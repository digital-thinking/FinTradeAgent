"""Stock data fetching and caching service."""

from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


# Known ISIN to Yahoo Finance ticker mappings (for reference/backwards compatibility)
KNOWN_ISINS = {
    "US0378331005": "AAPL",  # Apple
    "US5949181045": "MSFT",  # Microsoft
    "US02079K3059": "GOOGL",  # Alphabet
    "US0231351067": "AMZN",  # Amazon
    "US88160R1014": "TSLA",  # Tesla
    "US67066G1040": "NVDA",  # NVIDIA
    "US30303M1027": "META",  # Meta
    "US4781601046": "JNJ",  # Johnson & Johnson
    "US91324P1021": "UNH",  # UnitedHealth
    "US7427181091": "PG",  # Procter & Gamble
    "US4592001014": "IBM",  # IBM
    "US1912161007": "KO",  # Coca-Cola
    "US7170811035": "PFE",  # Pfizer
    "US2546871060": "DIS",  # Disney
    "US0970231058": "BA",  # Boeing
    "US46625H1005": "JPM",  # JPMorgan Chase
    "US0605051046": "BAC",  # Bank of America
    "US92826C8394": "V",  # Visa
    "US5801351017": "MCD",  # McDonald's
    "US2855121099": "LLY",  # Eli Lilly
}


class StockDataService:
    """Service for fetching and caching stock price data."""

    def __init__(self, data_dir: Path | None = None):
        if data_dir is None:
            data_dir = Path("data/stock_data")
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, pd.DataFrame] = {}
        self._ticker_cache: dict[str, str] = {}  # Maps identifiers to validated tickers

    def get_ticker(self, identifier: str) -> str:
        """
        Resolve any identifier (ISIN, ticker symbol) to a Yahoo Finance ticker.
        The identifier is stored as-is in the portfolio but resolved here for data fetching.
        """
        # Check cache first
        if identifier in self._ticker_cache:
            return self._ticker_cache[identifier]

        # Check known ISIN mappings
        if identifier in KNOWN_ISINS:
            ticker = KNOWN_ISINS[identifier]
            self._ticker_cache[identifier] = ticker
            return ticker

        # Assume it's already a ticker symbol - validate it works
        ticker = identifier.upper()
        self._ticker_cache[identifier] = ticker
        return ticker

    def _get_ticker(self, identifier: str) -> str:
        """Internal method - use get_ticker() instead."""
        return self.get_ticker(identifier)

    def _get_cache_path(self, isin: str) -> Path:
        """Get the cache file path for an ISIN."""
        return self.data_dir / f"{isin}.csv"

    def _is_cache_valid(self, cache_path: Path, max_age_hours: int = 1) -> bool:
        """Check if the cache file is still valid."""
        if not cache_path.exists():
            return False
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        return datetime.now() - mtime < timedelta(hours=max_age_hours)

    def update_data(self, isin: str, period: str = "1y") -> pd.DataFrame:
        """Fetch and cache latest data for an ISIN."""
        ticker = self._get_ticker(isin)
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            if df.empty:
                raise ValueError(f"No data found for {ticker}")

            cache_path = self._get_cache_path(isin)
            df.to_csv(cache_path)
            self._cache[isin] = df
            return df
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data for {ticker}: {e}") from e

    def get_history(self, isin: str, days: int = 365) -> pd.DataFrame:
        """Get price history for an ISIN."""
        if isin in self._cache:
            df = self._cache[isin]
        else:
            cache_path = self._get_cache_path(isin)
            if self._is_cache_valid(cache_path):
                df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                # Ensure index is DatetimeIndex
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index, utc=True)
                self._cache[isin] = df
            else:
                df = self.update_data(isin)

        # Convert timezone-aware index to naive for consistent comparisons
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        if days > 0:
            cutoff = datetime.now() - timedelta(days=days)
            df = df[df.index >= cutoff]
        return df

    def get_price(self, isin: str) -> float:
        """Get the current price for an ISIN."""
        df = self.get_history(isin, days=5)
        if df.empty:
            raise ValueError(f"No price data available for {isin}")
        return float(df["Close"].iloc[-1])

    def get_stock_info(self, isin: str) -> dict:
        """Get stock information including name."""
        ticker = self._get_ticker(isin)
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                "name": info.get("shortName", ticker),
                "symbol": ticker,
                "isin": isin,
                "currency": info.get("currency", "USD"),
            }
        except Exception:
            return {
                "name": ticker,
                "symbol": ticker,
                "isin": isin,
                "currency": "USD",
            }

    @staticmethod
    def get_known_isins() -> dict[str, str]:
        """Get a mapping of known ISINs to their tickers (for reference only)."""
        return KNOWN_ISINS.copy()

    @staticmethod
    def get_available_isins() -> dict[str, str]:
        """Deprecated: Use get_known_isins(). Returns known ISIN mappings."""
        return KNOWN_ISINS.copy()
