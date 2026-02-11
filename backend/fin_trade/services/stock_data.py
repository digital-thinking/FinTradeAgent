"""Stock data fetching and caching service."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd
import yfinance as yf
from fin_trade.models import AssetClass

if TYPE_CHECKING:
    from fin_trade.services.security import SecurityService


@dataclass
class PriceContext:
    """Price history context for a single ticker."""

    ticker: str
    current_price: float
    change_5d_pct: float | None
    change_30d_pct: float | None
    high_52w: float | None
    low_52w: float | None
    pct_from_52w_high: float | None
    pct_from_52w_low: float | None
    rsi_14: float | None
    volume_avg_20d: float | None
    volume_ratio: float | None  # Current vs 20-day avg
    ma_20: float | None
    ma_50: float | None
    trend_summary: str  # e.g., "↗ +15% (5d), above 20-day MA"

    # Short interest data (from stored SecurityService data)
    shares_short: int | None = None
    short_ratio: float | None = None  # Days to cover
    short_percent_float: float | None = None

    def to_context_string(self) -> str:
        """Format as compact string for agent consumption."""
        parts = [f"${self.current_price:.2f}"]

        # 5-day and 30-day changes
        if self.change_5d_pct is not None:
            arrow = "↗" if self.change_5d_pct > 0 else "↘" if self.change_5d_pct < 0 else "→"
            parts.append(f"{arrow}{self.change_5d_pct:+.1f}% (5d)")
        if self.change_30d_pct is not None:
            parts.append(f"{self.change_30d_pct:+.1f}% (30d)")

        # 52-week range position
        if self.pct_from_52w_high is not None and self.pct_from_52w_low is not None:
            range_pct = 100 - abs(self.pct_from_52w_high) if self.pct_from_52w_high else 0
            parts.append(f"52w range: {range_pct:.0f}%")

        # RSI
        if self.rsi_14 is not None:
            rsi_label = "overbought" if self.rsi_14 > 70 else "oversold" if self.rsi_14 < 30 else ""
            if rsi_label:
                parts.append(f"RSI {self.rsi_14:.0f} ({rsi_label})")
            else:
                parts.append(f"RSI {self.rsi_14:.0f}")

        # Volume
        if self.volume_ratio is not None and self.volume_ratio > 1.5:
            parts.append(f"vol {self.volume_ratio:.1f}x avg")

        # MA context
        if self.ma_20 is not None and self.current_price:
            if self.current_price > self.ma_20:
                parts.append("above 20-MA")
            else:
                parts.append("below 20-MA")

        # Short interest (only show if significant - > 10%)
        if self.short_percent_float is not None and self.short_percent_float > 0.10:
            si_pct = self.short_percent_float * 100
            dtc = f" ({self.short_ratio:.1f} DTC)" if self.short_ratio else ""
            parts.append(f"SI: {si_pct:.1f}%{dtc}")

        return " | ".join(parts)


class StockDataService:
    """Service for fetching and caching stock price data in CSV files.

    Price data is cached for 24 hours and automatically refreshed when stale.
    Use force_update() to refresh immediately (e.g., when executing trades).
    """

    def __init__(self, data_dir: Path | None = None):
        if data_dir is None:
            data_dir = Path("data/stock_data")
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, pd.DataFrame] = {}  # In-memory cache

    def _get_cache_path(self, ticker: str) -> Path:
        """Get the cache file path for a ticker."""
        return self.data_dir / f"{ticker.upper()}_prices.csv"

    def _is_cache_valid(self, cache_path: Path, max_age_hours: int = 24) -> bool:
        """Check if the cache file is still valid (default: 24 hours)."""
        if not cache_path.exists():
            return False
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        return datetime.now() - mtime < timedelta(hours=max_age_hours)

    def update_data(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """Fetch and cache latest price data for a ticker."""
        ticker = ticker.upper()
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            if df.empty:
                raise ValueError(f"No data found for {ticker}")

            cache_path = self._get_cache_path(ticker)
            df.to_csv(cache_path)
            self._cache[ticker] = df
            return df
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data for {ticker}: {e}") from e

    def force_update(self, ticker: str) -> pd.DataFrame:
        """Force refresh price data for a ticker (use when executing trades)."""
        return self.update_data(ticker)

    def get_history(self, ticker: str, days: int = 365) -> pd.DataFrame:
        """Get price history for a ticker."""
        ticker = ticker.upper()
        if ticker in self._cache:
            df = self._cache[ticker]
            # Check if in-memory cache is stale (file might be newer)
            cache_path = self._get_cache_path(ticker)
            if cache_path.exists():
                file_mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
                if hasattr(df, '_cache_time') and file_mtime > df._cache_time:
                    # File is newer, reload
                    df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                    if not isinstance(df.index, pd.DatetimeIndex):
                        df.index = pd.to_datetime(df.index, utc=True)
                    self._cache[ticker] = df
        else:
            cache_path = self._get_cache_path(ticker)
            if self._is_cache_valid(cache_path):
                df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                # Ensure index is DatetimeIndex
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index, utc=True)
                self._cache[ticker] = df
            else:
                df = self.update_data(ticker)

        # Convert timezone-aware index to naive for consistent comparisons
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        if days > 0:
            cutoff = datetime.now() - timedelta(days=days)
            df = df[df.index >= cutoff]
        return df

    def get_price(self, ticker: str) -> float:
        """Get the current price for a ticker (cached, auto-updates if stale)."""
        ticker = ticker.upper()
        df = self.get_history(ticker, days=5)
        if df.empty:
            raise ValueError(f"No price data available for {ticker}")
        return float(df["Close"].iloc[-1])

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float | None:
        """Calculate RSI (Relative Strength Index)."""
        if len(prices) < period + 1:
            return None

        delta = prices.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        if avg_loss.iloc[-1] == 0:
            return 100.0

        rs = avg_gain.iloc[-1] / avg_loss.iloc[-1]
        return float(100 - (100 / (1 + rs)))

    def _calculate_change_pct(
        self, df: pd.DataFrame, days: int
    ) -> float | None:
        """Calculate percentage change over N days."""
        if len(df) < 2:
            return None

        cutoff = datetime.now() - timedelta(days=days)
        recent = df[df.index >= cutoff]

        if len(recent) < 2:
            return None

        start_price = recent["Close"].iloc[0]
        end_price = recent["Close"].iloc[-1]

        if start_price == 0:
            return None

        return float(((end_price - start_price) / start_price) * 100)

    def get_price_context(
        self,
        ticker: str,
        security_service: SecurityService | None = None,
    ) -> PriceContext:
        """Get rich price context for a ticker including history and indicators.

        If security_service is provided, uses stored 52w range and MA data
        to reduce API calls (only fetches 30 days of history for RSI/changes).

        Args:
            ticker: Stock ticker symbol
            security_service: Optional SecurityService for stored data reuse

        Returns:
            PriceContext with price history and technical indicators
        """
        ticker = ticker.upper()

        # Try to get 52w range and MAs from stored data
        high_52w = None
        low_52w = None
        ma_50_stored = None
        shares_short = None
        short_ratio = None
        short_percent_float = None

        if security_service:
            # Get stored 52w range (avoid fetching 365 days of history)
            range_data = security_service.get_52w_range(ticker)
            if range_data:
                high_52w = range_data["high_52w"]
                low_52w = range_data["low_52w"]

            # Get stored MA data
            ma_data = security_service.get_moving_averages(ticker)
            if ma_data:
                ma_50_stored = ma_data["ma_50"]

            # Get short interest data
            si_data = security_service.get_short_interest(ticker)
            if si_data:
                shares_short = si_data["shares_short"]
                short_ratio = si_data["short_ratio"]
                short_percent_float = si_data["short_percent_float"]

        # Determine how much history we need
        # If we have stored 52w data, only need 30 days for RSI and changes
        # Otherwise, need 365 days to calculate 52w range
        days_needed = 30 if (high_52w is not None and low_52w is not None) else 365

        df = self.get_history(ticker, days=days_needed)

        if df.empty:
            raise ValueError(f"No price data available for {ticker}")

        current_price = float(df["Close"].iloc[-1])

        # Calculate changes
        change_5d = self._calculate_change_pct(df, 5)
        change_30d = self._calculate_change_pct(df, 30)

        # Calculate 52-week high/low from history if not from stored data
        if high_52w is None or low_52w is None:
            high_52w = float(df["High"].max()) if "High" in df.columns else None
            low_52w = float(df["Low"].min()) if "Low" in df.columns else None

        pct_from_high = None
        pct_from_low = None
        if high_52w and high_52w > 0:
            pct_from_high = ((current_price - high_52w) / high_52w) * 100
        if low_52w and low_52w > 0:
            pct_from_low = ((current_price - low_52w) / low_52w) * 100

        # RSI
        rsi = self._calculate_rsi(df["Close"])

        # Volume metrics
        volume_avg_20d = None
        volume_ratio = None
        if "Volume" in df.columns and len(df) >= 20:
            volume_avg_20d = float(df["Volume"].tail(20).mean())
            if volume_avg_20d > 0:
                current_volume = float(df["Volume"].iloc[-1])
                volume_ratio = current_volume / volume_avg_20d

        # Moving averages - use stored MA-50 if available, calculate from history otherwise
        ma_20 = float(df["Close"].tail(20).mean()) if len(df) >= 20 else None
        ma_50 = ma_50_stored if ma_50_stored else (float(df["Close"].tail(50).mean()) if len(df) >= 50 else None)

        # Build trend summary
        trend_parts = []
        if change_5d is not None:
            arrow = "↗" if change_5d > 0 else "↘" if change_5d < 0 else "→"
            trend_parts.append(f"{arrow}{change_5d:+.1f}% (5d)")
        if ma_20 and current_price > ma_20:
            trend_parts.append("above 20-MA")
        elif ma_20:
            trend_parts.append("below 20-MA")

        trend_summary = ", ".join(trend_parts) if trend_parts else "neutral"

        return PriceContext(
            ticker=ticker,
            current_price=current_price,
            change_5d_pct=change_5d,
            change_30d_pct=change_30d,
            high_52w=high_52w,
            low_52w=low_52w,
            pct_from_52w_high=pct_from_high,
            pct_from_52w_low=pct_from_low,
            rsi_14=rsi,
            volume_avg_20d=volume_avg_20d,
            volume_ratio=volume_ratio,
            ma_20=ma_20,
            ma_50=ma_50,
            trend_summary=trend_summary,
            shares_short=shares_short,
            short_ratio=short_ratio,
            short_percent_float=short_percent_float,
        )

    def get_holdings_context(
        self,
        tickers: list[str],
        security_service: SecurityService | None = None,
    ) -> dict[str, PriceContext]:
        """Get price context for multiple tickers.

        Args:
            tickers: List of ticker symbols
            security_service: Optional SecurityService for stored data reuse

        Returns:
            Dict mapping ticker to PriceContext
        """
        result = {}
        for ticker in tickers:
            result[ticker] = self.get_price_context(ticker, security_service)
        return result

    def format_holdings_for_prompt(
        self,
        holdings: list,
        price_contexts: dict[str, PriceContext] | None = None,
        security_service: SecurityService | None = None,
        asset_class: AssetClass = AssetClass.STOCKS,
    ) -> str:
        """Format holdings with rich context for agent prompts.

        Args:
            holdings: List of Holding objects with ticker, name, quantity, avg_price
            price_contexts: Pre-fetched price contexts (will fetch if not provided)
            security_service: Optional SecurityService for stored data reuse

        Returns:
            Formatted string for agent prompt
        """
        if not holdings:
            return "  None (empty portfolio)"

        if price_contexts is None:
            tickers = [h.ticker for h in holdings]
            price_contexts = self.get_holdings_context(tickers, security_service)

        unit_label = "units" if asset_class == AssetClass.CRYPTO else "shares"

        lines = []
        for h in holdings:
            ctx = price_contexts.get(h.ticker)
            quantity = (
                f"{h.quantity:.8f}".rstrip("0").rstrip(".")
                if asset_class == AssetClass.CRYPTO
                else f"{int(h.quantity)}"
            )

            if ctx:
                gain = ((ctx.current_price - h.avg_price) / h.avg_price * 100) if h.avg_price > 0 else 0
                line = (
                    f"  - {h.ticker} - {h.name}: {quantity} {unit_label} @ avg ${h.avg_price:.2f}\n"
                    f"    Current: {ctx.to_context_string()}\n"
                    f"    P/L: {gain:+.1f}%"
                )
            else:
                # Fallback without context
                line = (
                    f"  - {h.ticker} - {h.name}: {quantity} {unit_label} "
                    f"@ avg ${h.avg_price:.2f}"
                )

            lines.append(line)

        return "\n".join(lines)

    def get_benchmark_performance(
        self,
        symbol: str = "SPY",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pd.DataFrame:
        """Get benchmark total return series for comparison.

        Args:
            symbol: Benchmark ticker symbol (default: SPY for S&P 500)
            start_date: Start date for the series (default: 1 year ago)
            end_date: End date for the series (default: today)

        Returns:
            DataFrame with columns: date, price, cumulative_return
            cumulative_return is normalized to 0% at start_date
        """
        # Default to 1 year of data
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        # Get historical data - calculate days needed from date range
        days_needed = (end_date - start_date).days + 10
        df = self.get_history(symbol, days=days_needed)

        if df.empty:
            raise ValueError(f"No benchmark data available for {symbol}")

        # Filter by date range
        df = df[(df.index >= start_date) & (df.index <= end_date)]

        if df.empty:
            raise ValueError(f"No benchmark data in date range for {symbol}")

        # Calculate cumulative return from start
        start_price = df["Close"].iloc[0]
        df = df.copy()
        df["cumulative_return"] = ((df["Close"] / start_price) - 1) * 100

        # Create clean output DataFrame
        result = pd.DataFrame({
            "date": df.index,
            "price": df["Close"].values,
            "cumulative_return": df["cumulative_return"].values,
        })
        result = result.reset_index(drop=True)

        return result

