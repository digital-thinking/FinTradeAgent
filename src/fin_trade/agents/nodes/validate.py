"""Validate node - checks trade recommendations against constraints."""

import time

from fin_trade.agents.tools.price_lookup import get_stock_price
from fin_trade.services.security import SecurityService


def validate_node(state) -> dict:
    """Validate node: checks trade recommendations against portfolio constraints.

    Works with both SimpleAgentState and DebateAgentState.

    Validates:
    - SELL orders have sufficient shares owned
    - BUY orders have sufficient cash (estimates if price not in state)
    - Trade quantities are positive integers
    - Actions are valid (BUY/SELL)

    Updates state with:
    - error: Validation error message if invalid, None if valid
    - retry_count: Incremented if validation fails
    - _metrics_validate: Metrics for this step
    """
    start_time = time.time()

    recommendations = state.get("recommendations")
    if recommendations is None:
        # No recommendations to validate (parsing failed)
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "error": state.get("error", "No recommendations generated"),
            "retry_count": state.get("retry_count", 0) + 1,
            "_metrics_validate": {"duration_ms": duration_ms, "input_tokens": 0, "output_tokens": 0},
        }

    portfolio_state = state["portfolio_state"]
    price_data = state.get("price_data", {})

    # Build holdings lookup
    holdings_by_ticker = {h.ticker.upper(): h for h in portfolio_state.holdings}

    errors = []
    estimated_cash_needed = 0.0
    security_service = SecurityService()

    for trade in recommendations.trades:
        ticker = trade.ticker.upper()

        # Validate action
        if trade.action not in ("BUY", "SELL"):
            errors.append(f"{ticker}: Invalid action '{trade.action}', must be BUY or SELL")
            continue

        # Validate quantity
        if trade.quantity <= 0:
            errors.append(f"{ticker}: Quantity must be positive, got {trade.quantity}")
            continue

        if trade.action == "SELL":
            # Check if we own the stock
            if ticker not in holdings_by_ticker:
                errors.append(f"{ticker}: Cannot SELL - not in holdings")
            elif holdings_by_ticker[ticker].quantity < trade.quantity:
                errors.append(
                    f"{ticker}: Cannot SELL {trade.quantity} shares - only own "
                    f"{holdings_by_ticker[ticker].quantity}"
                )

        elif trade.action == "BUY":
            # Estimate cost - use cached price or fetch
            price = price_data.get(ticker)
            if price is None:
                try:
                    price = get_stock_price(ticker, security_service)
                except Exception:
                    # Can't validate without price, allow it through
                    continue
            estimated_cash_needed += price * trade.quantity

    # Check total cash requirement
    if estimated_cash_needed > portfolio_state.cash:
        errors.append(
            f"Insufficient cash: trades require ~${estimated_cash_needed:.2f}, "
            f"but only ${portfolio_state.cash:.2f} available"
        )

    duration_ms = int((time.time() - start_time) * 1000)
    metrics = {"duration_ms": duration_ms, "input_tokens": 0, "output_tokens": 0}

    if errors:
        return {
            "error": "; ".join(errors),
            "retry_count": state.get("retry_count", 0) + 1,
            "_metrics_validate": metrics,
        }

    # Validation passed
    return {
        "error": None,
        "retry_count": state.get("retry_count", 0),
        "_metrics_validate": metrics,
    }
