"""Security service for managing stock ticker lookups and prices."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import yfinance as yf
from fin_trade.models import AssetClass

if TYPE_CHECKING:
    from fin_trade.services.stock_data import StockDataService

CRYPTO_SUFFIXES = ("-USD", "-EUR", "-GBP")


@dataclass
class Security:
    """Represents a known security with its identifiers."""

    ticker: str
    name: str


class SecurityService:
    """Service for managing security lookups and price fetching.

    Security data is stored in {TICKER}_data.json files containing
    full yfinance info. Prices are delegated to StockDataService.

    Fundamentals lookups (sector, analyst targets, earnings, 52w range, MAs,
    insider/short data) accept an optional ``fundamentals_ticker`` argument.
    When provided, that symbol is used as the source for business-level
    fields while prices continue to come from the traded listing.
    """

    def __init__(
        self,
        data_dir: Path | None = None,
        stock_data_service: StockDataService | None = None,
    ):
        if data_dir is None:
            data_dir = Path("data/stock_data")
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Lazy import to avoid circular dependency
        if stock_data_service is None:
            from fin_trade.services.stock_data import StockDataService
            stock_data_service = StockDataService(data_dir=data_dir)
        self._stock_data_service = stock_data_service

        self._by_ticker: dict[str, Security] = {}
        self._full_info: dict[str, dict] = {}  # ticker -> full yfinance info

        self._load_persisted_securities()

    @staticmethod
    def _resolve(ticker: str, fundamentals_ticker: str | None) -> str:
        """Return the ticker used for fundamentals lookups."""
        if fundamentals_ticker:
            return fundamentals_ticker.upper()
        return ticker.upper()

    def _get_data_file_path(self, ticker: str) -> Path:
        """Get the path to the data file for a security."""
        return self.data_dir / f"{ticker.upper()}_data.json"

    def _load_persisted_securities(self) -> None:
        """Load all persisted security data from JSON files."""
        for data_file in self.data_dir.glob("*_data.json"):
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Legacy files written by the old fallback code cached the
            # fundamentals ticker's info under the listing ticker (tagged
            # with ``_fundamentals_ticker``). Skip those — we now cache each
            # ticker under its own key and the listing needs a fresh local
            # fetch to get its real currency.
            if data.get("_fundamentals_ticker"):
                continue

            ticker = data.get("ticker") or data.get("symbol")
            name = data.get("shortName") or data.get("longName") or data.get("name") or ticker

            if ticker:
                ticker = ticker.upper()
                security = Security(ticker=ticker, name=name)
                self._by_ticker[ticker] = security
                self._full_info[ticker] = data

    def _save_security_data(self, ticker: str, data: dict) -> None:
        """Save security data to a JSON file."""
        ticker = ticker.upper()
        data_file = self._get_data_file_path(ticker)

        data["_saved_at"] = datetime.now(timezone.utc).isoformat()
        data["ticker"] = ticker

        serializable_data = {}
        for key, value in data.items():
            try:
                json.dumps(value)
                serializable_data[key] = value
            except (TypeError, ValueError):
                serializable_data[key] = str(value)

        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, indent=2, default=str)

    def _fetch_and_cache_info(self, ticker: str) -> dict:
        """Fetch yfinance info for one ticker and cache it under that ticker."""
        ticker = ticker.upper()
        stock = yf.Ticker(ticker)
        info = dict(stock.info)

        name = info.get("shortName") or info.get("longName") or ticker
        info["ticker"] = ticker
        if "shortName" not in info:
            info["shortName"] = name

        self._save_security_data(ticker, info)
        self._full_info[ticker] = info
        self._register(Security(ticker=ticker, name=name))
        return info

    def _ensure_info(self, ticker: str) -> dict:
        """Return cached info for ticker, fetching if missing."""
        ticker = ticker.upper()
        info = self._full_info.get(ticker)
        if info is None:
            info = self._fetch_and_cache_info(ticker)
        return info

    def get_by_ticker(self, ticker: str) -> Security | None:
        """Get a security by its ticker symbol."""
        return self._by_ticker.get(ticker.upper())

    def get_full_info(
        self,
        ticker: str,
        fundamentals_ticker: str | None = None,
    ) -> dict | None:
        """Get cached yfinance info. Returns fundamentals_ticker's info when set."""
        source = self._resolve(ticker, fundamentals_ticker)
        return self._full_info.get(source)

    def lookup_ticker(
        self,
        ticker: str,
        fundamentals_ticker: str | None = None,
    ) -> Security:
        """Look up a security by ticker, fetching and caching info if unknown.

        When ``fundamentals_ticker`` is given, that symbol's info is also
        pre-fetched so subsequent fundamentals calls can hit the cache.
        """
        ticker = ticker.upper()
        if fundamentals_ticker:
            fundamentals_ticker = fundamentals_ticker.upper()

        info = self._full_info.get(ticker)
        if info is None:
            info = self._fetch_and_cache_info(ticker)

        if fundamentals_ticker and fundamentals_ticker != ticker:
            if fundamentals_ticker not in self._full_info:
                self._fetch_and_cache_info(fundamentals_ticker)

        if ticker in self._by_ticker:
            return self._by_ticker[ticker]

        name = info.get("shortName") or info.get("longName") or ticker
        security = Security(ticker=ticker, name=name)
        self._register(security)
        return security

    def _register(self, security: Security) -> None:
        """Register a security in the lookup caches."""
        self._by_ticker[security.ticker] = security

    def get_price(self, ticker: str) -> float:
        """Get the current price for a ticker symbol (cached, auto-updates if >24h old)."""
        return self._stock_data_service.get_price(ticker)

    def get_closes(self, tickers: list[str], start: datetime, end: datetime):
        """Get aligned daily closes for ticker symbols."""
        return self._stock_data_service.get_closes(tickers, start, end)

    def is_crypto_ticker(self, ticker: str) -> bool:
        """Check whether a ticker is a crypto symbol with fiat quote suffix."""
        normalized = ticker.upper()
        return any(normalized.endswith(suffix) for suffix in CRYPTO_SUFFIXES)

    def validate_ticker_for_asset_class(self, ticker: str, asset_class: AssetClass) -> bool:
        """Validate that ticker matches portfolio asset class."""
        normalized = ticker.upper()
        is_crypto = self.is_crypto_ticker(normalized)
        if asset_class == AssetClass.CRYPTO and not is_crypto:
            raise ValueError(
                f"Ticker {normalized} is not a crypto ticker. Use format like BTC-USD."
            )
        if asset_class == AssetClass.STOCKS and is_crypto:
            raise ValueError(
                f"Ticker {normalized} is a crypto ticker. This portfolio only allows stocks."
            )
        return True

    def force_update_price(self, ticker: str) -> float:
        """Force refresh price data for a ticker and return current price."""
        self._stock_data_service.force_update(ticker)
        return self._stock_data_service.get_price(ticker)

    def get_currency(
        self,
        ticker: str,
    ) -> str:
        """Return the native currency of a ticker's traded listing."""
        info = self._ensure_info(ticker)
        return info.get("currency") or "USD"

    def get_stock_info(
        self,
        ticker: str,
        fundamentals_ticker: str | None = None,
    ) -> dict:
        """Get stock information including name, sector, currency.

        ``currency`` always comes from the traded listing (``ticker``) so
        price-denominated comparisons remain honest. Business-level fields
        (sector, industry, country, website) prefer the ``fundamentals_ticker``
        data when provided — the primary/ADR listing usually has richer info.
        """
        ticker = ticker.upper()
        local_info = self._ensure_info(ticker)

        fundamentals_info = local_info
        if fundamentals_ticker:
            fundamentals_info = self._ensure_info(fundamentals_ticker)

        name = (
            local_info.get("shortName")
            or local_info.get("longName")
            or ticker
        )

        return {
            "name": name,
            "ticker": ticker,
            "fundamentals_ticker": fundamentals_ticker.upper() if fundamentals_ticker else ticker,
            "currency": local_info.get("currency") or "USD",
            "sector": fundamentals_info.get("sector") or local_info.get("sector"),
            "industry": fundamentals_info.get("industry") or local_info.get("industry"),
            "country": fundamentals_info.get("country") or local_info.get("country"),
            "website": fundamentals_info.get("website") or local_info.get("website"),
            "marketCap": fundamentals_info.get("marketCap"),
        }

    def delete_security(self, ticker: str) -> None:
        """Delete cached security data (info JSON + price CSV) for a ticker."""
        ticker = ticker.upper()

        data_file = self._get_data_file_path(ticker)
        if data_file.exists():
            data_file.unlink()

        price_file = self.data_dir / f"{ticker}_prices.csv"
        if price_file.exists():
            price_file.unlink()

        self._by_ticker.pop(ticker, None)
        self._full_info.pop(ticker, None)
        self._stock_data_service._cache.pop(ticker, None)

    def refresh_security_data(
        self,
        ticker: str,
        fundamentals_ticker: str | None = None,
    ) -> dict:
        """Force refresh security data from yfinance and save to file."""
        ticker = ticker.upper()
        info = self._fetch_and_cache_info(ticker)
        if fundamentals_ticker and fundamentals_ticker.upper() != ticker:
            self._fetch_and_cache_info(fundamentals_ticker.upper())
        return info

    def is_data_stale(
        self,
        ticker: str,
        max_age_hours: int = 24,
        fundamentals_ticker: str | None = None,
    ) -> bool:
        """Check if stored data for a ticker is stale (older than max_age_hours)."""
        source = self._resolve(ticker, fundamentals_ticker)
        info = self._full_info.get(source)
        if not info:
            return True
        saved_at = info.get("_saved_at")
        if not saved_at:
            return True
        saved_time = datetime.fromisoformat(saved_at)
        if saved_time.tzinfo is None:
            saved_time = saved_time.replace(tzinfo=timezone.utc)

        return datetime.now(timezone.utc) - saved_time > timedelta(hours=max_age_hours)

    # ==================== Rich Data Methods ====================
    # These methods expose already-stored yfinance data without new API calls.
    # Each returns a ``currency`` field so callers can convert to a display
    # currency via FxService — price-denominated values (52w, MAs, analyst
    # targets) are in the fundamentals ticker's native currency.

    def get_short_interest(
        self,
        ticker: str,
        fundamentals_ticker: str | None = None,
    ) -> dict | None:
        """Short interest data (shares_short, short_ratio, short_percent_float)."""
        info = self.get_full_info(ticker, fundamentals_ticker)
        if not info:
            return None

        shares_short = info.get("sharesShort")
        if shares_short is None:
            return None

        return {
            "shares_short": shares_short,
            "short_ratio": info.get("shortRatio"),
            "short_percent_float": info.get("shortPercentOfFloat"),
        }

    def get_52w_range(
        self,
        ticker: str,
        fundamentals_ticker: str | None = None,
    ) -> dict | None:
        """52-week range with the source currency attached."""
        info = self.get_full_info(ticker, fundamentals_ticker)
        if not info:
            return None

        high = info.get("fiftyTwoWeekHigh")
        low = info.get("fiftyTwoWeekLow")
        if high is None or low is None:
            return None

        return {
            "high_52w": high,
            "low_52w": low,
            "currency": info.get("currency") or "USD",
        }

    def get_moving_averages(
        self,
        ticker: str,
        fundamentals_ticker: str | None = None,
    ) -> dict | None:
        """Moving averages with the source currency attached."""
        info = self.get_full_info(ticker, fundamentals_ticker)
        if not info:
            return None

        ma_50 = info.get("fiftyDayAverage")
        ma_200 = info.get("twoHundredDayAverage")
        if ma_50 is None and ma_200 is None:
            return None

        return {
            "ma_50": ma_50,
            "ma_200": ma_200,
            "currency": info.get("currency") or "USD",
        }

    def get_analyst_data(
        self,
        ticker: str,
        fundamentals_ticker: str | None = None,
    ) -> dict | None:
        """Analyst ratings and targets with source currency attached."""
        info = self.get_full_info(ticker, fundamentals_ticker)
        if not info:
            return None

        target = info.get("targetMeanPrice")
        rec = info.get("recommendationKey")
        if target is None and rec is None:
            return None

        return {
            "target_price": target,
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            "recommendation": rec,
            "num_analysts": info.get("numberOfAnalystOpinions"),
            "currency": info.get("currency") or "USD",
        }

    def get_volume_data(
        self,
        ticker: str,
        fundamentals_ticker: str | None = None,
    ) -> dict | None:
        """Volume metrics (avg_volume, avg_volume_10d)."""
        info = self.get_full_info(ticker, fundamentals_ticker)
        if not info:
            return None

        avg_vol = info.get("averageVolume")
        if avg_vol is None:
            return None

        return {
            "avg_volume": avg_vol,
            "avg_volume_10d": info.get("averageVolume10days"),
        }

    def get_earnings_timestamp(
        self,
        ticker: str,
        fundamentals_ticker: str | None = None,
    ) -> datetime | None:
        """Next earnings date if available."""
        info = self.get_full_info(ticker, fundamentals_ticker)
        if not info:
            return None

        ts = info.get("earningsTimestamp")
        if ts is None:
            return None

        try:
            return datetime.fromtimestamp(ts)
        except (TypeError, ValueError, OSError):
            return None

    def get_valuation_metrics(
        self,
        ticker: str,
        fundamentals_ticker: str | None = None,
    ) -> dict | None:
        """Valuation metrics (beta, PE, P/B, market cap).

        PE ratios and price/book are dimensionless and comparable across
        listings. ``market_cap`` is attached with its source currency so
        callers can convert if needed.
        """
        info = self.get_full_info(ticker, fundamentals_ticker)
        if not info:
            return None

        return {
            "beta": info.get("beta"),
            "pe_trailing": info.get("trailingPE"),
            "pe_forward": info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "market_cap": info.get("marketCap"),
            "currency": info.get("currency") or "USD",
        }
