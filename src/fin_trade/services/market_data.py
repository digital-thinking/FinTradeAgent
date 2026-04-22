"""Market data service for fetching earnings, filings, insider trades, and macro data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import yfinance as yf
from fin_trade.models import AssetClass

if TYPE_CHECKING:
    from fin_trade.services.security import SecurityService


@dataclass
class EarningsInfo:
    """Earnings calendar information for a stock."""

    ticker: str
    earnings_date: datetime | None
    eps_estimate: float | None
    revenue_estimate: float | None
    hours_until_earnings: float | None

    def to_context_string(self) -> str:
        """Format earnings info for agent context."""
        if self.earnings_date is None:
            return f"{self.ticker}: No upcoming earnings date available"

        parts = [f"{self.ticker}: Earnings on {self.earnings_date.strftime('%Y-%m-%d')}"]
        if self.hours_until_earnings is not None:
            if self.hours_until_earnings < 24:
                parts.append("(today)")
            else:
                days = int(self.hours_until_earnings / 24)
                parts.append(f"({days} days away)")
        if self.eps_estimate is not None:
            parts.append(f"EPS est: ${self.eps_estimate:.2f}")
        if self.revenue_estimate is not None:
            parts.append(f"Rev est: ${self.revenue_estimate / 1e9:.2f}B")
        return " | ".join(parts)


@dataclass
class InsiderTrade:
    """Insider trading transaction."""

    ticker: str
    insider_name: str
    position: str
    transaction_type: str  # "Buy" or "Sell"
    shares: int
    value: float | None
    date: datetime | None

    def to_context_string(self) -> str:
        """Format insider trade for agent context."""
        date_str = self.date.strftime("%Y-%m-%d") if self.date else "Unknown date"
        value_str = f"${self.value:,.0f}" if self.value else "N/A"
        return (
            f"{self.ticker}: {self.insider_name} ({self.position}) "
            f"{self.transaction_type} {self.shares:,} shares ({value_str}) on {date_str}"
        )


@dataclass
class SECFiling:
    """SEC filing information."""

    ticker: str
    filing_type: str  # 8-K, 10-Q, 10-K, etc.
    date: datetime | None
    title: str
    url: str

    def to_context_string(self) -> str:
        """Format SEC filing for agent context."""
        date_str = self.date.strftime("%Y-%m-%d") if self.date else "Unknown date"
        return f"{self.ticker}: {self.filing_type} filed {date_str} - {self.title}"


@dataclass
class MacroData:
    """Macro-economic market data."""

    sp500_price: float | None
    sp500_change_pct: float | None
    nasdaq_price: float | None
    nasdaq_change_pct: float | None
    dow_price: float | None
    dow_change_pct: float | None
    treasury_10y: float | None
    treasury_3m: float | None
    vix: float | None
    timestamp: datetime

    def to_context_string(self) -> str:
        """Format macro data for agent context."""
        lines = ["MARKET OVERVIEW:"]

        if self.sp500_price:
            change = f"{self.sp500_change_pct:+.2f}%" if self.sp500_change_pct else ""
            lines.append(f"  S&P 500: {self.sp500_price:,.2f} {change}")

        if self.nasdaq_price:
            change = f"{self.nasdaq_change_pct:+.2f}%" if self.nasdaq_change_pct else ""
            lines.append(f"  NASDAQ: {self.nasdaq_price:,.2f} {change}")

        if self.dow_price:
            change = f"{self.dow_change_pct:+.2f}%" if self.dow_change_pct else ""
            lines.append(f"  DOW: {self.dow_price:,.2f} {change}")

        if self.vix:
            lines.append(f"  VIX (Volatility): {self.vix:.2f}")

        if self.treasury_10y or self.treasury_3m:
            lines.append("INTEREST RATES:")
            if self.treasury_10y:
                lines.append(f"  10-Year Treasury: {self.treasury_10y:.2f}%")
            if self.treasury_3m:
                lines.append(f"  3-Month Treasury: {self.treasury_3m:.2f}%")
            if self.treasury_10y and self.treasury_3m:
                # Yahoo's ^IRX is the 3M bill, so this inversion signal is 10Y-3M, not 10Y-2Y.
                spread = self.treasury_10y - self.treasury_3m
                inversion = " (INVERTED - recession signal)" if spread < 0 else ""
                lines.append(f"  Yield Spread (10Y-3M): {spread:.2f}%{inversion}")

        return "\n".join(lines)


class MarketDataService:
    """Service for fetching market data: earnings, filings, insider trades, macro data."""

    def __init__(self, cache_dir: Path | None = None):
        if cache_dir is None:
            cache_dir = Path("data/market_data")
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, tuple[datetime, object]] = {}
        self._cache_duration = timedelta(hours=24)

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self._cache:
            return False
        cached_time, _ = self._cache[key]
        return datetime.now(timezone.utc) - cached_time < self._cache_duration

    def _get_cached(self, key: str) -> object | None:
        """Get cached data if valid."""
        if self._is_cache_valid(key):
            return self._cache[key][1]
        return None

    def _set_cached(self, key: str, data: object) -> None:
        """Store data in cache."""
        self._cache[key] = (datetime.now(timezone.utc), data)

    @staticmethod
    def _resolve_source(ticker: str, fundamentals_ticker: str | None) -> str:
        """Return the ticker to use as the fundamentals/events data source."""
        if fundamentals_ticker:
            return fundamentals_ticker.upper()
        return ticker.upper()

    def get_earnings_info(
        self,
        ticker: str,
        security_service: SecurityService | None = None,
        fundamentals_ticker: str | None = None,
    ) -> EarningsInfo:
        """Fetch earnings calendar information for a ticker.

        When ``fundamentals_ticker`` is given, corporate events are pulled
        from that symbol (typically the US/primary listing) instead of the
        traded ticker.
        """
        ticker = ticker.upper()
        source = self._resolve_source(ticker, fundamentals_ticker)
        cache_key = f"earnings_{ticker}_{source}"

        cached = self._get_cached(cache_key)
        if cached:
            return cached  # type: ignore

        if security_service:
            stored_earnings = security_service.get_earnings_timestamp(
                ticker, fundamentals_ticker
            )
            if stored_earnings:
                # Ensure stored_earnings is UTC-aware
                if stored_earnings.tzinfo is None:
                    stored_earnings = stored_earnings.replace(tzinfo=timezone.utc)
                
                # Check if stored date is in the future
                hours_until = (stored_earnings - datetime.now(timezone.utc)).total_seconds() / 3600
                if hours_until >= -1:
                    result = EarningsInfo(
                        ticker=ticker,
                        earnings_date=stored_earnings,
                        eps_estimate=None,  # Not available from stored data
                        revenue_estimate=None,
                        hours_until_earnings=hours_until,
                    )
                    self._set_cached(cache_key, result)
                    return result

        stock = yf.Ticker(source)
        calendar = stock.calendar

        earnings_date = None
        eps_estimate = None
        revenue_estimate = None
        hours_until = None

        # calendar can be a DataFrame or dict depending on yfinance version
        if calendar is not None:
            if isinstance(calendar, pd.DataFrame) and not calendar.empty:
                if "Earnings Date" in calendar.index:
                    date_val = calendar.loc["Earnings Date"].iloc[0]
                    if pd.notna(date_val):
                        earnings_date = pd.to_datetime(date_val).to_pydatetime()
                if "EPS Estimate" in calendar.index:
                    eps_val = calendar.loc["EPS Estimate"].iloc[0]
                    if pd.notna(eps_val):
                        eps_estimate = float(eps_val)
                if "Revenue Estimate" in calendar.index:
                    rev_val = calendar.loc["Revenue Estimate"].iloc[0]
                    if pd.notna(rev_val):
                        revenue_estimate = float(rev_val)
            elif isinstance(calendar, dict) and calendar:
                if "Earnings Date" in calendar:
                    dates = calendar["Earnings Date"]
                    if dates:
                        earnings_date = pd.to_datetime(dates[0]).to_pydatetime()
                if "EPS Estimate" in calendar:
                    eps_estimate = calendar.get("EPS Estimate")
                if "Revenue Estimate" in calendar:
                    revenue_estimate = calendar.get("Revenue Estimate")

        if earnings_date:
            # Ensure earnings_date is UTC-aware (yfinance typically returns UTC or naive)
            if earnings_date.tzinfo is None:
                earnings_date = earnings_date.replace(tzinfo=timezone.utc)
            else:
                earnings_date = earnings_date.astimezone(timezone.utc)
                
            hours_until = (earnings_date - datetime.now(timezone.utc)).total_seconds() / 3600

        result = EarningsInfo(
            ticker=ticker,
            earnings_date=earnings_date,
            eps_estimate=eps_estimate,
            revenue_estimate=revenue_estimate,
            hours_until_earnings=hours_until,
        )
        self._set_cached(cache_key, result)
        return result

    def get_insider_trades(
        self,
        ticker: str,
        limit: int = 5,
        security_service: SecurityService | None = None,
        fundamentals_ticker: str | None = None,
    ) -> list[InsiderTrade]:
        """Fetch recent insider trading transactions for a ticker."""
        ticker = ticker.upper()
        source = self._resolve_source(ticker, fundamentals_ticker)
        cache_key = f"insider_{ticker}_{source}"

        cached = self._get_cached(cache_key)
        if cached:
            return cached[:limit]  # type: ignore

        stock = yf.Ticker(source)
        insider_df = stock.insider_transactions

        if insider_df is None or insider_df.empty:
            return []

        trades = []
        for _, row in insider_df.head(limit * 2).iterrows():
            # Parse transaction type
            trans_text = str(row.get("Text", row.get("Transaction", "")))
            if "Sale" in trans_text or "Sell" in trans_text:
                trans_type = "Sell"
            elif "Purchase" in trans_text or "Buy" in trans_text:
                trans_type = "Buy"
            else:
                continue  # Skip other transaction types

            # Parse shares
            shares = row.get("Shares", 0)
            if pd.isna(shares):
                shares = 0
            shares = int(abs(shares))

            # Parse value
            value = row.get("Value", None)
            if pd.notna(value):
                value = float(abs(value))
            else:
                value = None

            # Parse date
            date = None
            date_col = row.get("Start Date", row.get("Date", None))
            if pd.notna(date_col):
                date = pd.to_datetime(date_col).to_pydatetime()

            trades.append(
                InsiderTrade(
                    ticker=ticker,
                    insider_name=str(row.get("Insider", "Unknown")),
                    position=str(row.get("Position", "Unknown")),
                    transaction_type=trans_type,
                    shares=shares,
                    value=value,
                    date=date,
                )
            )

        self._set_cached(cache_key, trades)
        return trades[:limit]

    def get_sec_filings(
        self,
        ticker: str,
        filing_types: list[str] | None = None,
        limit: int = 5,
        security_service: SecurityService | None = None,
        fundamentals_ticker: str | None = None,
    ) -> list[SECFiling]:
        """Fetch recent SEC filings for a ticker."""
        ticker = ticker.upper()
        source = self._resolve_source(ticker, fundamentals_ticker)
        cache_key = f"sec_{ticker}_{source}"

        if filing_types is None:
            filing_types = ["8-K", "10-Q", "10-K"]

        cached = self._get_cached(cache_key)
        if cached:
            filings = [f for f in cached if f.filing_type in filing_types]  # type: ignore
            return filings[:limit]

        stock = yf.Ticker(source)
        sec_filings = stock.sec_filings

        if sec_filings is None or (
            isinstance(sec_filings, pd.DataFrame) and sec_filings.empty
        ):
            return []

        filings = []

        # Handle both DataFrame and list formats
        if isinstance(sec_filings, pd.DataFrame):
            for _, row in sec_filings.iterrows():
                filing_type = str(row.get("type", row.get("Type", "")))
                if not any(ft in filing_type for ft in filing_types):
                    continue

                date = None
                date_col = row.get("date", row.get("Date", None))
                if pd.notna(date_col):
                    date = pd.to_datetime(date_col).to_pydatetime()

                filings.append(
                    SECFiling(
                        ticker=ticker,
                        filing_type=filing_type,
                        date=date,
                        title=str(row.get("title", row.get("Title", "N/A"))),
                        url=str(row.get("edgarUrl", row.get("link", ""))),
                    )
                )
        elif isinstance(sec_filings, list):
            for filing in sec_filings:
                filing_type = filing.get("type", "")
                if not any(ft in filing_type for ft in filing_types):
                    continue

                date = None
                if "date" in filing:
                    date = pd.to_datetime(filing["date"]).to_pydatetime()

                filings.append(
                    SECFiling(
                        ticker=ticker,
                        filing_type=filing_type,
                        date=date,
                        title=filing.get("title", "N/A"),
                        url=filing.get("edgarUrl", ""),
                    )
                )

        self._set_cached(cache_key, filings)
        return filings[:limit]

    def get_macro_data(self) -> MacroData:
        """Fetch macro-economic market data (indices, treasury yields, VIX)."""
        cache_key = "macro_data"

        cached = self._get_cached(cache_key)
        if cached:
            return cached  # type: ignore

        def get_latest_price_and_change(
            ticker_symbol: str,
        ) -> tuple[float | None, float | None]:
            """Get latest price and daily change percentage."""
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="5d")
            if hist.empty or len(hist) < 2:
                if not hist.empty:
                    return float(hist["Close"].iloc[-1]), None
                return None, None
            latest = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            change_pct = ((latest - prev) / prev) * 100
            return latest, change_pct

        def get_treasury_yield(ticker_symbol: str) -> float | None:
            """Get latest treasury yield."""
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="5d")
            if hist.empty:
                return None
            return float(hist["Close"].iloc[-1])

        # Fetch data for major indices and rates
        sp500_price, sp500_change = get_latest_price_and_change("^GSPC")
        nasdaq_price, nasdaq_change = get_latest_price_and_change("^IXIC")
        dow_price, dow_change = get_latest_price_and_change("^DJI")
        vix, _ = get_latest_price_and_change("^VIX")
        treasury_10y = get_treasury_yield("^TNX")
        treasury_3m = get_treasury_yield("^IRX")  # ^IRX is the 3-month T-bill yield.

        result = MacroData(
            sp500_price=sp500_price,
            sp500_change_pct=sp500_change,
            nasdaq_price=nasdaq_price,
            nasdaq_change_pct=nasdaq_change,
            dow_price=dow_price,
            dow_change_pct=dow_change,
            treasury_10y=treasury_10y,
            treasury_3m=treasury_3m,
            vix=vix,
            timestamp=datetime.now(timezone.utc),
        )
        self._set_cached(cache_key, result)
        return result

    def get_full_context_for_holdings(
        self,
        holdings: list,
        security_service: SecurityService | None = None,
    ) -> str:
        """Get full market data context for a list of holdings.

        ``holdings`` entries expose ``ticker`` and optional
        ``fundamentals_ticker`` — each holding's events are pulled from
        its fundamentals ticker when set.
        """
        lines = []

        macro = self.get_macro_data()
        lines.append(macro.to_context_string())
        lines.append("")

        earnings_upcoming = []
        for h in holdings:
            fundamentals = getattr(h, "fundamentals_ticker", None)
            info = self.get_earnings_info(
                h.ticker,
                security_service=security_service,
                fundamentals_ticker=fundamentals,
            )
            if (
                info.hours_until_earnings is not None
                and -1 <= info.hours_until_earnings <= 30 * 24
            ):
                earnings_upcoming.append(info)

        if earnings_upcoming:
            lines.append("UPCOMING EARNINGS (next 30 days):")
            for info in sorted(
                earnings_upcoming, key=lambda x: x.hours_until_earnings or 9999
            ):
                lines.append(f"  {info.to_context_string()}")
            lines.append("")

        all_filings = []
        for h in holdings:
            fundamentals = getattr(h, "fundamentals_ticker", None)
            filings = self.get_sec_filings(
                h.ticker,
                limit=3,
                security_service=security_service,
                fundamentals_ticker=fundamentals,
            )
            all_filings.extend(filings)

        all_filings.sort(key=lambda x: x.date or datetime.min, reverse=True)
        recent_filings = all_filings[:10]

        if recent_filings:
            lines.append("RECENT SEC FILINGS:")
            for filing in recent_filings:
                lines.append(f"  {filing.to_context_string()}")
            lines.append("")

        all_insider_trades = []
        for h in holdings:
            fundamentals = getattr(h, "fundamentals_ticker", None)
            trades = self.get_insider_trades(
                h.ticker,
                limit=3,
                security_service=security_service,
                fundamentals_ticker=fundamentals,
            )
            all_insider_trades.extend(trades)

        all_insider_trades.sort(key=lambda x: x.date or datetime.min, reverse=True)
        recent_trades = all_insider_trades[:10]

        if recent_trades:
            lines.append("RECENT INSIDER TRADING:")
            for trade in recent_trades:
                lines.append(f"  {trade.to_context_string()}")

        return "\n".join(lines) if lines else "No additional market data available."

    def get_holdings_context(
        self,
        holdings: list,
        asset_class: AssetClass = AssetClass.STOCKS,
        security_service: SecurityService | None = None,
    ) -> str:
        """Get holdings context aligned to asset class."""
        if asset_class == AssetClass.CRYPTO:
            macro = self.get_macro_data()
            return (
                f"{macro.to_context_string()}\n\n"
                "CRYPTO NOTE: Stock fundamentals (earnings, SEC filings, insider trades) "
                "are not applicable."
            )
        return self.get_full_context_for_holdings(
            holdings, security_service=security_service
        )
