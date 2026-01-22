"""Stock data fetching and caching service."""

from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


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

