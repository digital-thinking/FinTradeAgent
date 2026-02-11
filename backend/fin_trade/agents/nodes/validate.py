"""Validate node - checks trade recommendations against constraints."""

import time

from backend.fin_trade.agents.tools.price_lookup import get_stock_price
from backend.fin_trade.models import AssetClass
from backend.fin_trade.services.security import SecurityService


def validate_node(state) -> dict:
    """Validate node: checks trade recommendations against portfolio constraints.

    Works with both SimpleAgentState and DebateAgentState.

    Validates:
    - SELL orders have sufficient shares owned
    - BUY orders have sufficient cash (estimates if price not in state)
    - Trade quantities are positive
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
    portfolio_config = state.get("portfolio_config")
    price_data = state.get("price_data", {})
    asset_class = getattr(portfolio_config, "asset_class", AssetClass.STOCKS)
    unit_label = "units" if asset_class == AssetClass.CRYPTO else "shares"

    # Build holdings lookup
    holdings_by_ticker = {h.ticker.upper(): h for h in portfolio_state.holdings}

    errors = []
    estimated_cash_needed = 0.0
    estimated_cash_from_sells = 0.0
    security_service = SecurityService()

    # First pass: validate all trades and calculate cash flows
    for trade in recommendations.trades:
        ticker = trade.ticker.upper()

        try:
            security_service.validate_ticker_for_asset_class(ticker, asset_class)
        except ValueError as e:
            errors.append(str(e))
            continue

        # Validate action
        if trade.action not in ("BUY", "SELL"):
            errors.append(f"{ticker}: Invalid action '{trade.action}', must be BUY or SELL")
            continue

        # Validate quantity
        if trade.quantity <= 0:
            errors.append(f"{ticker}: Quantity must be positive, got {trade.quantity}")
            continue
        if asset_class == AssetClass.STOCKS and not float(trade.quantity).is_integer():
            errors.append(f"{ticker}: Stock quantity must be a whole number, got {trade.quantity}")
            continue

        if trade.action == "SELL":
            # Check if we own the stock
            if ticker not in holdings_by_ticker:
                errors.append(f"{ticker}: Cannot SELL - not in holdings")
            elif holdings_by_ticker[ticker].quantity < trade.quantity:
                errors.append(
                    f"{ticker}: Cannot SELL {trade.quantity} {unit_label} - only own "
                    f"{holdings_by_ticker[ticker].quantity}"
                )
            else:
                # Valid SELL - estimate cash gained
                price = price_data.get(ticker)
                if price is None:
                    try:
                        price = get_stock_price(ticker, security_service)
                    except Exception:
                        # Use avg_price as fallback for estimation
                        price = holdings_by_ticker[ticker].avg_price
                estimated_cash_from_sells += price * trade.quantity

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

    # Check total cash requirement (current cash + proceeds from sells)
    available_cash = portfolio_state.cash + estimated_cash_from_sells
    if estimated_cash_needed > available_cash:
        errors.append(
            f"Insufficient cash: trades require ~${estimated_cash_needed:.2f}, "
            f"but only ~${available_cash:.2f} available (${portfolio_state.cash:.2f} cash + ~${estimated_cash_from_sells:.2f} from sells)"
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
