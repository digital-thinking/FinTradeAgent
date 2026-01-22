"""Price lookup tools for LangGraph agents."""

from fin_trade.services.security import SecurityService


def get_stock_price(ticker: str, security_service: SecurityService | None = None) -> float:
    """Get the current price for a stock ticker.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT")
        security_service: Optional SecurityService instance, creates one if not provided

    Returns:
        Current stock price as float

    Raises:
        RuntimeError: If price cannot be fetched
    """
    if security_service is None:
        security_service = SecurityService()
    return security_service.get_price(ticker)


def get_stock_prices(
    tickers: list[str], security_service: SecurityService | None = None
) -> dict[str, float]:
    """Get current prices for multiple stock tickers.

    Args:
        tickers: List of stock ticker symbols
        security_service: Optional SecurityService instance

    Returns:
        Dictionary mapping ticker -> price. Failed lookups are omitted.
    """
    if security_service is None:
        security_service = SecurityService()

    prices = {}
    for ticker in tickers:
        try:
            prices[ticker.upper()] = security_service.get_price(ticker)
        except Exception:
            # Skip tickers that fail to fetch
            continue
    return prices
