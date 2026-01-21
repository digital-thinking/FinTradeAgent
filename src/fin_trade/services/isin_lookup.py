"""ISIN lookup service - placeholder for future real ISIN providers."""

from dataclasses import dataclass


@dataclass
class IsinLookupResult:
    """Result of an ISIN lookup."""

    isin: str
    name: str
    ticker: str | None = None
    exchange: str | None = None
    currency: str | None = None
