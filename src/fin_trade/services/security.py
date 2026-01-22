"""Security service for managing stock ticker/ISIN lookups and prices."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yfinance as yf

if TYPE_CHECKING:
    from fin_trade.services.stock_data import StockDataService


@dataclass
class Security:
    """Represents a known security with its identifiers."""

    isin: str
    ticker: str
    name: str


class SecurityService:
    """Service for managing security lookups and price fetching.

    ISINs are obtained from:
    1. yfinance (when available)
    2. User-provided via UI (stored in data files)
    3. Fallback to UNKNOWN-{ticker} when not available

    Prices are delegated to StockDataService which handles caching.
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

        # Initialize caches
        self._by_isin: dict[str, Security] = {}
        self._by_ticker: dict[str, Security] = {}
        self._full_info: dict[str, dict] = {}  # ticker -> full yfinance info

        # Load persisted security data from files
        self._load_persisted_securities()

    def _get_data_file_path(self, isin: str) -> Path:
        """Get the path to the data file for a security."""
        return self.data_dir / f"{isin}_data.json"

    def _load_persisted_securities(self) -> None:
        """Load all persisted security data from JSON files."""
        for data_file in self.data_dir.glob("*_data.json"):
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                isin = data.get("isin")
                ticker = data.get("ticker") or data.get("symbol")
                name = data.get("shortName") or data.get("longName") or data.get("name") or ticker

                if isin and ticker:
                    security = Security(isin=isin, ticker=ticker.upper(), name=name)
                    self._by_isin[isin] = security
                    self._by_ticker[ticker.upper()] = security
                    self._full_info[ticker.upper()] = data
            except Exception:
                # Skip files that can't be loaded
                continue

    def _save_security_data(self, isin: str, data: dict) -> None:
        """Save security data to a JSON file."""
        data_file = self._get_data_file_path(isin)

        # Add metadata
        data["_saved_at"] = datetime.now().isoformat()

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

    def get_by_isin(self, isin: str) -> Security | None:
        """Get a security by its ISIN."""
        return self._by_isin.get(isin)

    def get_by_ticker(self, ticker: str) -> Security | None:
        """Get a security by its ticker symbol."""
        return self._by_ticker.get(ticker.upper())

    def get_full_info(self, ticker: str) -> dict | None:
        """Get full yfinance info for a ticker if available."""
        return self._full_info.get(ticker.upper())

    def lookup_ticker(self, ticker: str) -> Security:
        """
        Lookup a security by ticker. If not known, fetch info from yfinance
        and register the security. Uses UNKNOWN-{ticker} if no ISIN available.
        User can provide ISIN manually via UI.
        """
        ticker = ticker.upper()

        # Check if already known in memory
        if ticker in self._by_ticker:
            return self._by_ticker[ticker]

        # Fetch from yfinance
        isin = None
        name = ticker
        info = {}

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            name = info.get("shortName") or info.get("longName") or ticker
            isin = info.get("isin")

            # Ensure ticker is in the info dict
            info["ticker"] = ticker

        except Exception:
            pass

        # Fallback to UNKNOWN if no ISIN from yfinance
        if not isin:
            isin = f"UNKNOWN-{ticker}"

        # Update info dict with ISIN
        info["isin"] = isin
        if "shortName" not in info:
            info["shortName"] = name

        # Save full info to file
        self._save_security_data(isin, info)

        # Cache full info
        self._full_info[ticker] = info

        security = Security(isin=isin, ticker=ticker, name=name)
        self._register(security)
        return security

    def _register(self, security: Security) -> None:
        """Register a security in the lookup caches."""
        self._by_isin[security.isin] = security
        self._by_ticker[security.ticker] = security

    def get_price(self, ticker: str) -> float:
        """Get the current price for a ticker symbol (cached, auto-updates if >24h old)."""
        return self._stock_data_service.get_price(ticker)

    def force_update_price(self, ticker: str) -> float:
        """Force refresh price data for a ticker and return current price."""
        self._stock_data_service.force_update(ticker)
        return self._stock_data_service.get_price(ticker)

    def get_stock_info(self, ticker: str) -> dict:
        """Get stock information including name, ISIN, etc."""
        ticker = ticker.upper()

        # Check if we have cached full info
        if ticker in self._full_info:
            info = self._full_info[ticker]
            return {
                "name": info.get("shortName") or info.get("longName") or ticker,
                "ticker": ticker,
                "isin": info.get("isin") or f"UNKNOWN-{ticker}",
                "currency": info.get("currency", "USD"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "website": info.get("website"),
                "marketCap": info.get("marketCap"),
            }

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            name = info.get("shortName") or info.get("longName") or ticker
            isin = info.get("isin") or f"UNKNOWN-{ticker}"

            info["ticker"] = ticker
            info["isin"] = isin

            # Save and cache the full info
            self._save_security_data(isin, info)
            self._full_info[ticker] = info

            return {
                "name": name,
                "ticker": ticker,
                "isin": isin,
                "currency": info.get("currency", "USD"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "website": info.get("website"),
                "marketCap": info.get("marketCap"),
            }
        except Exception:
            return {
                "name": ticker,
                "ticker": ticker,
                "isin": f"UNKNOWN-{ticker}",
                "currency": "USD",
            }

    def refresh_security_data(self, ticker: str) -> dict | None:
        """Force refresh security data from yfinance and save to file."""
        ticker = ticker.upper()
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            name = info.get("shortName") or info.get("longName") or ticker
            isin = info.get("isin") or f"UNKNOWN-{ticker}"

            info["ticker"] = ticker
            info["isin"] = isin

            # Save and update caches
            self._save_security_data(isin, info)
            self._full_info[ticker] = info

            security = Security(isin=isin, ticker=ticker, name=name)
            self._register(security)

            return info
        except Exception:
            return None

    def update_isin(self, ticker: str, isin: str) -> Security:
        """
        Update the ISIN for a security. Called when user provides ISIN manually.
        This will update caches and save to file.
        """
        ticker = ticker.upper()
        isin = isin.strip().upper()

        # Get existing security or create new one
        existing = self._by_ticker.get(ticker)
        if existing:
            name = existing.name
            # Get full info if available
            full_info = self._full_info.get(ticker, {}).copy()
        else:
            name = ticker
            full_info = {}

        # Update the info with the new ISIN
        full_info["isin"] = isin
        full_info["ticker"] = ticker
        if "shortName" not in full_info:
            full_info["shortName"] = name

        # Remove old file if it had UNKNOWN ISIN
        if existing and existing.isin.startswith("UNKNOWN-"):
            old_file = self._get_data_file_path(existing.isin)
            if old_file.exists():
                old_file.unlink()

        # Save with new ISIN
        self._save_security_data(isin, full_info)
        self._full_info[ticker] = full_info

        # Update caches
        security = Security(isin=isin, ticker=ticker, name=name)

        # Remove old entry from isin cache if it existed
        if existing:
            self._by_isin.pop(existing.isin, None)

        self._register(security)
        return security
