"""Security service for managing stock ticker lookups and prices."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import yfinance as yf
from backend.fin_trade.models import AssetClass

if TYPE_CHECKING:
    from backend.fin_trade.services.stock_data import StockDataService

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
            from backend.fin_trade.services.stock_data import StockDataService
            stock_data_service = StockDataService(data_dir=data_dir)
        self._stock_data_service = stock_data_service

        # Initialize caches
        self._by_ticker: dict[str, Security] = {}
        self._full_info: dict[str, dict] = {}  # ticker -> full yfinance info

        # Load persisted security data from files
        self._load_persisted_securities()

    def _get_data_file_path(self, ticker: str) -> Path:
        """Get the path to the data file for a security."""
        return self.data_dir / f"{ticker.upper()}_data.json"

    def _load_persisted_securities(self) -> None:
        """Load all persisted security data from JSON files."""
        for data_file in self.data_dir.glob("*_data.json"):
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

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

        # Add metadata
        data["_saved_at"] = datetime.now().isoformat()
        data["ticker"] = ticker

        # Convert any non-serializable values
        serializable_data = {}
        for key, value in data.items():
            try:
                json.dumps(value)
                serializable_data[key] = value
            except (TypeError, ValueError):
                # Convert non-serializable values to string
                serializable_data[key] = str(value)

        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, indent=2, default=str)

    def get_by_ticker(self, ticker: str) -> Security | None:
        """Get a security by its ticker symbol."""
        return self._by_ticker.get(ticker.upper())

    def get_full_info(self, ticker: str) -> dict | None:
        """Get full yfinance info for a ticker if available."""
        return self._full_info.get(ticker.upper())

    def lookup_ticker(self, ticker: str) -> Security:
        """
        Lookup a security by ticker. If not known, fetch info from yfinance
        and register the security.
        """
        ticker = ticker.upper()

        # Check if already known in memory
        if ticker in self._by_ticker:
            return self._by_ticker[ticker]

        # Fetch from yfinance
        stock = yf.Ticker(ticker)
        info = stock.info

        name = info.get("shortName") or info.get("longName") or ticker

        # Ensure ticker is in the info dict
        info["ticker"] = ticker

        if "shortName" not in info:
            info["shortName"] = name

        # Save full info to file (ticker-based)
        self._save_security_data(ticker, info)

        # Cache full info
        self._full_info[ticker] = info

        security = Security(ticker=ticker, name=name)
        self._register(security)
        return security

    def _register(self, security: Security) -> None:
        """Register a security in the lookup caches."""
        self._by_ticker[security.ticker] = security

    def get_price(self, ticker: str) -> float:
        """Get the current price for a ticker symbol (cached, auto-updates if >24h old)."""
        return self._stock_data_service.get_price(ticker)

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

    def get_stock_info(self, ticker: str) -> dict:
        """Get stock information including name, sector, etc."""
        ticker = ticker.upper()

        # Check if we have cached full info
        if ticker in self._full_info:
            info = self._full_info[ticker]
            return {
                "name": info.get("shortName") or info.get("longName") or ticker,
                "ticker": ticker,
                "currency": info.get("currency", "USD"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "website": info.get("website"),
                "marketCap": info.get("marketCap"),
            }

        stock = yf.Ticker(ticker)
        info = stock.info

        name = info.get("shortName") or info.get("longName") or ticker

        info["ticker"] = ticker

        # Save and cache the full info
        self._save_security_data(ticker, info)
        self._full_info[ticker] = info

        return {
            "name": name,
            "ticker": ticker,
            "currency": info.get("currency", "USD"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "website": info.get("website"),
            "marketCap": info.get("marketCap"),
        }

    def refresh_security_data(self, ticker: str) -> dict:
        """Force refresh security data from yfinance and save to file."""
        ticker = ticker.upper()
        stock = yf.Ticker(ticker)
        info = stock.info

        name = info.get("shortName") or info.get("longName") or ticker

        info["ticker"] = ticker

        # Save and update caches
        self._save_security_data(ticker, info)
        self._full_info[ticker] = info

        security = Security(ticker=ticker, name=name)
        self._register(security)

        return info

    def is_data_stale(self, ticker: str, max_age_hours: int = 24) -> bool:
        """Check if stored data for a ticker is stale (older than max_age_hours)."""
        info = self._full_info.get(ticker.upper())
        if not info:
            return True
        saved_at = info.get("_saved_at")
        if not saved_at:
            return True
        saved_time = datetime.fromisoformat(saved_at)
        return datetime.now() - saved_time > timedelta(hours=max_age_hours)

    # ==================== Rich Data Methods ====================
    # These methods expose already-stored yfinance data without new API calls

    def get_short_interest(self, ticker: str) -> dict | None:
        """Get short interest data from stored JSON.

        Returns:
            Dict with shares_short, short_ratio (days to cover), short_percent_float
            or None if not available
        """
        info = self._full_info.get(ticker.upper())
        if not info:
            return None

        shares_short = info.get("sharesShort")
        if shares_short is None:
            return None

        return {
            "shares_short": shares_short,
            "short_ratio": info.get("shortRatio"),  # Days to cover
            "short_percent_float": info.get("shortPercentOfFloat"),
        }

    def get_52w_range(self, ticker: str) -> dict | None:
        """Get 52-week range from stored JSON.

        Returns:
            Dict with high_52w, low_52w or None if not available
        """
        info = self._full_info.get(ticker.upper())
        if not info:
            return None

        high = info.get("fiftyTwoWeekHigh")
        low = info.get("fiftyTwoWeekLow")
        if high is None or low is None:
            return None

        return {
            "high_52w": high,
            "low_52w": low,
        }

    def get_moving_averages(self, ticker: str) -> dict | None:
        """Get moving averages from stored JSON.

        Returns:
            Dict with ma_50, ma_200 or None if not available
        """
        info = self._full_info.get(ticker.upper())
        if not info:
            return None

        ma_50 = info.get("fiftyDayAverage")
        ma_200 = info.get("twoHundredDayAverage")
        if ma_50 is None and ma_200 is None:
            return None

        return {
            "ma_50": ma_50,
            "ma_200": ma_200,
        }

    def get_analyst_data(self, ticker: str) -> dict | None:
        """Get analyst ratings from stored JSON.

        Returns:
            Dict with target_price, recommendation or None if not available
        """
        info = self._full_info.get(ticker.upper())
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
        }

    def get_volume_data(self, ticker: str) -> dict | None:
        """Get volume metrics from stored JSON.

        Returns:
            Dict with avg_volume, avg_volume_10d or None if not available
        """
        info = self._full_info.get(ticker.upper())
        if not info:
            return None

        avg_vol = info.get("averageVolume")
        if avg_vol is None:
            return None

        return {
            "avg_volume": avg_vol,
            "avg_volume_10d": info.get("averageVolume10days"),
        }

    def get_earnings_timestamp(self, ticker: str) -> datetime | None:
        """Get earnings date from stored JSON.

        Returns:
            Datetime of next earnings or None if not available
        """
        info = self._full_info.get(ticker.upper())
        if not info:
            return None

        ts = info.get("earningsTimestamp")
        if ts is None:
            return None

        try:
            return datetime.fromtimestamp(ts)
        except (TypeError, ValueError, OSError):
            return None

    def get_valuation_metrics(self, ticker: str) -> dict | None:
        """Get valuation metrics from stored JSON.

        Returns:
            Dict with beta, pe_trailing, pe_forward, etc.
        """
        info = self._full_info.get(ticker.upper())
        if not info:
            return None

        return {
            "beta": info.get("beta"),
            "pe_trailing": info.get("trailingPE"),
            "pe_forward": info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "market_cap": info.get("marketCap"),
        }
