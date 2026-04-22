"""FX rate fetching and caching service.

Caches historical FX rates to data/fx_cache/{FROM}{TO}=X_prices.csv so
portfolio values can be converted between native and display currencies
using the rate at each relevant timestamp.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf


class FxService:
    """Service for fetching and caching FX rates via yfinance pairs."""

    def __init__(self, cache_dir: Path | None = None):
        if cache_dir is None:
            cache_dir = Path("data/fx_cache")
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, pd.DataFrame] = {}

    @staticmethod
    def _normalize_ccy(ccy: str) -> str:
        return ccy.strip().upper()

    @staticmethod
    def _pair_symbol(from_ccy: str, to_ccy: str) -> str:
        """yfinance FX pair symbol. USD pairs use the short form {CCY}=X."""
        if from_ccy == "USD":
            return f"{to_ccy}=X"
        return f"{from_ccy}{to_ccy}=X"

    def _cache_path(self, pair: str) -> Path:
        safe = pair.replace("=", "_")
        return self.cache_dir / f"{safe}_prices.csv"

    def _is_cache_valid(self, path: Path, max_age_hours: int = 24) -> bool:
        if not path.exists():
            return False
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return datetime.now(timezone.utc) - mtime < timedelta(hours=max_age_hours)

    def _load_history(self, pair: str) -> pd.DataFrame:
        """Load FX history for a pair, refreshing the CSV if stale."""
        if pair in self._cache:
            return self._cache[pair]

        path = self._cache_path(pair)
        if self._is_cache_valid(path):
            df = pd.read_csv(path, index_col=0, parse_dates=True)
        else:
            ticker = yf.Ticker(pair)
            df = ticker.history(period="10y", auto_adjust=False)
            if df.empty:
                raise ValueError(f"No FX data available for {pair}")
            df = df.dropna(subset=["Close"])
            if df.empty:
                raise ValueError(f"No valid FX close data for {pair}")
            df.to_csv(path)

        if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        self._cache[pair] = df
        return df

    def get_rate(
        self,
        from_ccy: str,
        to_ccy: str = "USD",
        at: datetime | None = None,
    ) -> float:
        """Return the rate to convert 1 unit of from_ccy into to_ccy.

        If ``at`` is given, looks up the rate on that trading day (or the
        nearest prior trading day). Otherwise returns the latest cached rate.
        """
        from_ccy = self._normalize_ccy(from_ccy)
        to_ccy = self._normalize_ccy(to_ccy)
        if from_ccy == to_ccy:
            return 1.0

        # Most FX pairs on yfinance are quoted against USD. Route non-USD
        # cross rates through USD so we only need {CCY}=X series.
        if from_ccy != "USD" and to_ccy != "USD":
            return self.get_rate(from_ccy, "USD", at) * self.get_rate("USD", to_ccy, at)

        pair = self._pair_symbol(from_ccy, to_ccy)
        df = self._load_history(pair)
        closes = df["Close"].dropna()
        if closes.empty:
            raise ValueError(f"No close prices in FX history for {pair}")

        if at is None:
            return float(closes.iloc[-1])

        ts = pd.Timestamp(at)
        if ts.tz is not None:
            ts = ts.tz_convert("UTC").tz_localize(None)

        # Nearest prior trading day; if the lookup date predates our history,
        # fall back to the earliest available close rather than raising.
        prior = closes[closes.index <= ts]
        if prior.empty:
            return float(closes.iloc[0])
        return float(prior.iloc[-1])

    def convert(
        self,
        amount: float,
        from_ccy: str,
        to_ccy: str = "USD",
        at: datetime | None = None,
    ) -> float:
        """Convert ``amount`` from ``from_ccy`` to ``to_ccy``."""
        if amount == 0:
            return 0.0
        return amount * self.get_rate(from_ccy, to_ccy, at)
