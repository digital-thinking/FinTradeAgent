"""Price lookup tools for LangGraph agents."""

import re

from fin_trade.services.security import SecurityService


def extract_tickers_from_text(text: str) -> list[str]:
    """Extract stock ticker symbols prefixed with $ from text.

    Matches tickers written as $AAPL, $BTC-USD, $SAP.DE, etc.
    The LLM prompts instruct the model to always use $TICKER notation.

    Args:
        text: Text containing $TICKER references

    Returns:
        List of unique ticker symbols found (without the $ prefix)
    """
    # Match $TICKER patterns: $AAPL, $BTC-USD, $SAP.DE, etc.
    pattern = r"\$([A-Z]{1,5}(?:-[A-Z]{2,4}|\.[A-Z]{1,2})?)\b"
    matches = re.findall(pattern, text)

    # Deduplicate while preserving order
    seen = set()
    tickers = []
    for match in matches:
        ticker = match.upper()
        if ticker not in seen:
            seen.add(ticker)
            tickers.append(ticker)

    return tickers


def fetch_buy_candidate_data(
    tickers: list[str],
    security_service: SecurityService | None = None,
) -> dict[str, dict]:
    """Fetch and cache data for potential BUY candidates.

    Looks up each ticker via SecurityService, which caches the full
    yfinance info to {TICKER}_data.json for reuse.

    Args:
        tickers: List of ticker symbols to look up
        security_service: Optional SecurityService instance

    Returns:
        Dict mapping ticker -> info dict with price, bid, ask, name
    """
    if security_service is None:
        security_service = SecurityService()

    results = {}
    for ticker in tickers:
        try:
            # lookup_ticker() saves full info to {TICKER}_data.json
            security = security_service.lookup_ticker(ticker)

            # Get current price
            try:
                price = security_service.get_price(ticker)
            except Exception:
                price = None

            # Get bid/ask from stored data
            info = security_service.get_full_info(ticker) or {}
            bid = info.get("bid")
            ask = info.get("ask")

            results[ticker] = {
                "name": security.name,
                "price": price,
                "bid": bid,
                "ask": ask,
            }
        except Exception:
            # Skip tickers that fail
            continue

    return results


def format_buy_candidates_for_prompt(candidates: dict[str, dict]) -> str:
    """Format BUY candidate data for inclusion in prompts.

    Args:
        candidates: Dict from fetch_buy_candidate_data()

    Returns:
        Formatted string for prompt inclusion
    """
    if not candidates:
        return ""

    lines = ["BUY CANDIDATE PRICES (for quantity calculations):"]
    for ticker, info in candidates.items():
        if info.get("price"):
            price_str = f"${info['price']:.2f}"
            bid_ask = ""
            if info.get("bid") and info.get("ask"):
                spread = info["ask"] - info["bid"]
                spread_pct = (spread / info["bid"]) * 100 if info["bid"] > 0 else 0
                bid_ask = f" (bid ${info['bid']:.2f} / ask ${info['ask']:.2f}, spread {spread_pct:.2f}%)"
            lines.append(f"  {ticker} ({info.get('name', ticker)}): {price_str}{bid_ask}")

    return "\n".join(lines) if len(lines) > 1 else ""


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
