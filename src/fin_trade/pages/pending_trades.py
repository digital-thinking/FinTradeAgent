"""Pending Trades page for reviewing and applying agent recommendations."""

import json

import streamlit as st
import pandas as pd

from fin_trade.models import AssetClass
from fin_trade.services.execution_log import ExecutionLogService
from fin_trade.services import PortfolioService
from fin_trade.services.security import SecurityService
from fin_trade.components.ticker_correction import (
    render_ticker_correction,
    clear_ticker_corrections,
)


def _display_persistent_messages() -> None:
    """Display and clear persistent messages from session state."""
    messages = st.session_state.pop("pending_trades_messages", None)
    if not messages:
        return

    for msg in messages:
        if msg["type"] == "success":
            st.success(msg["text"])
        elif msg["type"] == "error":
            st.error(msg["text"])
        elif msg["type"] == "warning":
            st.warning(msg["text"])
        elif msg["type"] == "info":
            st.info(msg["text"])


def render_pending_trades_page() -> None:
    """Render the pending trades page."""
    st.title("📋 Pending Trades")
    st.caption("Review and apply trade recommendations from agent executions.")

    # Display persistent messages from previous actions
    _display_persistent_messages()

    log_service = ExecutionLogService()
    security_service = SecurityService()
    portfolio_service = PortfolioService(security_service=security_service)

    _render_add_manual_trade(portfolio_service, security_service, log_service)

    # Get recent logs with recommendations
    logs = log_service.get_logs(limit=50)

    # Filter to logs with pending trades
    logs_with_pending = []
    for log in logs:
        if not log.recommendations_json:
            continue

        try:
            recommendations = json.loads(log.recommendations_json)
            executed = set()
            if log.executed_trades_json:
                executed = set(json.loads(log.executed_trades_json))
            
            rejected = set()
            if log.rejected_trades_json:
                rejected = set(json.loads(log.rejected_trades_json))

            # Pending = not executed AND not rejected
            pending_indices = [
                i for i in range(len(recommendations)) 
                if i not in executed and i not in rejected
            ]
            
            if pending_indices:
                logs_with_pending.append((log, recommendations, executed, rejected, pending_indices))
        except json.JSONDecodeError:
            continue

    if not logs_with_pending:
        st.info("🎉 No pending trades! All recommendations have been applied or rejected.")
        st.caption("Run agents from the Portfolios page to generate new recommendations.")
        return

    # Summary metrics
    total_pending = sum(len(indices) for _, _, _, _, indices in logs_with_pending)
    total_executions = len(logs_with_pending)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pending Trades", total_pending)
    with col2:
        st.metric("From Executions", total_executions)
    with col3:
        # Count by action type
        total_buys = 0
        total_sells = 0
        for _, recs, _, _, indices in logs_with_pending:
            for i in indices:
                rec = recs[i]
                if rec.get("action") == "BUY":
                    total_buys += 1
                else:
                    total_sells += 1
        st.metric("BUY / SELL", f"{total_buys} / {total_sells}")

    st.divider()

    # Render each execution's pending trades
    for log, recommendations, executed, rejected, pending_indices in logs_with_pending:
        with st.expander(
            f"**{log.portfolio_name}** — {log.timestamp.strftime('%Y-%m-%d %H:%M')} — {len(pending_indices)} pending",
            expanded=True,
        ):
            _render_pending_trades_for_log(
                log, recommendations, pending_indices, log_service, security_service
            )


def _render_pending_trades_for_log(
    log,
    recommendations: list[dict],
    pending_indices: list[int],
    log_service: ExecutionLogService,
    security_service: SecurityService,
) -> None:
    """Render pending trades for a single execution log."""

    # Initialize quantity adjustments in session state
    if "pending_qty_adjustments" not in st.session_state:
        st.session_state.pending_qty_adjustments = {}

    # Load portfolio state for cash validation
    portfolio_service = PortfolioService(security_service=security_service)
    portfolios = portfolio_service.list_portfolios()
    portfolio_filename = None
    portfolio_state = None
    portfolio_config = None
    
    for filename in portfolios:
        config, state = portfolio_service.load_portfolio(filename)
        if config.name == log.portfolio_name:
            portfolio_filename = filename
            portfolio_state = state
            portfolio_config = config
            break

    available_cash = portfolio_state.cash if portfolio_state else 0.0
    asset_class = (
        portfolio_config.asset_class if portfolio_config else AssetClass.STOCKS
    )
    unit_label = "units" if asset_class == AssetClass.CRYPTO else "shares"
    is_empty_portfolio = (
        portfolio_state is not None
        and len(portfolio_state.holdings) == 0
        and len(portfolio_state.trades) == 0
    )

    # Build selection UI
    selected_indices = []
    trade_validity = {}  # Track which trades are valid (ticker found)
    key_prefixes = []  # Track key prefixes for ISIN application

    # First pass: check all tickers and collect validity info
    for i in pending_indices:
        rec = recommendations[i]
        ticker = rec.get("ticker", "")
        key_prefix = f"pending_{log.id}_{i}"
        key_prefixes.append(key_prefix)

        # Check if ticker has been corrected
        correction_key = f"{key_prefix}_ticker_correction"
        corrected_ticker = st.session_state.get(correction_key, ticker)

        # Try to get price
        try:
            price = security_service.get_price(corrected_ticker)
            is_valid = price is not None and price > 0
            trade_validity[i] = {
                "is_valid": is_valid,
                "corrected_ticker": corrected_ticker,
                "price": price,
                "error": None,
            }
        except Exception as e:
            trade_validity[i] = {
                "is_valid": False,
                "corrected_ticker": corrected_ticker,
                "price": None,
                "error": str(e),
            }

    # Select all checkbox with proper toggle behavior
    select_all_key = f"select_all_{log.id}"
    prev_select_all_key = f"prev_select_all_{log.id}"

    # Get previous state of select_all
    prev_select_all = st.session_state.get(prev_select_all_key, False)
    select_all = st.checkbox("Select all valid trades", key=select_all_key)

    # Detect if select_all was just toggled
    if select_all != prev_select_all:
        # Update all valid trade checkboxes based on new select_all state
        for i in pending_indices:
            if trade_validity[i]["is_valid"]:
                checkbox_key = f"pending_{log.id}_{i}"
                st.session_state[checkbox_key] = select_all
        st.session_state[prev_select_all_key] = select_all
        st.rerun()

    for i in pending_indices:
        rec = recommendations[i]
        ticker = rec.get("ticker", "")
        key_prefix = f"pending_{log.id}_{i}"
        validity = trade_validity[i]
        corrected_ticker = validity["corrected_ticker"]
        is_valid = validity["is_valid"]
        price = validity["price"]
        error = validity["error"]

        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([0.5, 1, 2, 1, 0.5])

            with col1:
                checkbox_key = f"pending_{log.id}_{i}"
                # Auto-enable if ticker was corrected and is now valid
                was_corrected = corrected_ticker != ticker
                if was_corrected and is_valid and checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = True

                is_selected = st.checkbox(
                    "Select trade",
                    key=checkbox_key,
                    label_visibility="collapsed",
                    disabled=not is_valid,
                )
                if is_selected and is_valid:
                    selected_indices.append(i)

            with col2:
                action = rec.get("action", "")
                action_color = "#00ff41" if action == "BUY" else "#ff0000"
                st.markdown(f"<span style='color:{action_color};font-weight:bold'>{action}</span>", unsafe_allow_html=True)

            with col3:
                st.markdown(f"**{corrected_ticker}**")
                if corrected_ticker != ticker:
                    st.caption(f"(was: {ticker})")

            with col4:
                original_quantity = rec.get("quantity", 0)
                qty_key = f"pending_qty_{log.id}_{i}"

                if price:
                    unit_singular = unit_label[:-1] if unit_label.endswith("s") else unit_label
                    st.caption(f"${price:.2f}/{unit_singular}")
                    if asset_class == AssetClass.CRYPTO:
                        adjusted_qty = st.number_input(
                            "Units",
                            min_value=0.0,
                            value=float(st.session_state.pending_qty_adjustments.get(qty_key, original_quantity)),
                            step=0.0001,
                            format="%.8f",
                            key=qty_key,
                            label_visibility="collapsed",
                            disabled=not is_valid,
                        )
                    else:
                        adjusted_qty = st.number_input(
                            "Shares",
                            min_value=0,
                            value=int(st.session_state.pending_qty_adjustments.get(qty_key, original_quantity)),
                            step=1,
                            key=qty_key,
                            label_visibility="collapsed",
                            disabled=not is_valid,
                        )
                    st.session_state.pending_qty_adjustments[qty_key] = adjusted_qty
                    cost = price * adjusted_qty
                    if adjusted_qty != original_quantity:
                        st.caption(f"~~{original_quantity}~~ -> **{adjusted_qty}** {unit_label} = ${cost:,.2f}")
                    else:
                        st.caption(f"{adjusted_qty} {unit_label} = ${cost:,.2f}")
                    # Show stop-loss and take-profit for BUY orders
                    action = rec.get("action", "")
                    stop_loss = rec.get("stop_loss_price")
                    take_profit = rec.get("take_profit_price")
                    if action == "BUY" and (stop_loss or take_profit):
                        sl_tp_parts = []
                        if stop_loss:
                            sl_pct = ((stop_loss - price) / price) * 100
                            sl_tp_parts.append(f"Stop-loss ${stop_loss:.2f} ({sl_pct:+.1f}%)")
                        if take_profit:
                            tp_pct = ((take_profit - price) / price) * 100
                            sl_tp_parts.append(f"Take-profit ${take_profit:.2f} ({tp_pct:+.1f}%)")
                        st.caption(" | ".join(sl_tp_parts))
                else:
                    st.write(f"{original_quantity} {unit_label}")

            with col5:
                # Delete button
                if st.button("🗑️", key=f"delete_{log.id}_{i}", help="Reject this trade"):
                    _reject_trade(log, i, log_service)

            # Show reasoning
            reasoning = rec.get("reasoning", "")
            st.caption(f"💭 {reasoning[:120]}..." if len(reasoning) > 120 else f"💭 {reasoning}")

            # Show ticker correction UI if invalid
            if not is_valid:
                result = render_ticker_correction(
                    original_ticker=ticker,
                    key_prefix=key_prefix,
                    security_service=security_service,
                )
                # If correction made it valid, show success
                if result.is_valid and result.corrected_ticker != ticker:
                    st.success(f"✓ Ticker corrected to {result.corrected_ticker} - trade is now ready!")

    st.markdown("---")

    # Calculate cash totals for selected trades (using adjusted quantities)
    total_buy_cost = 0.0
    total_sell_proceeds = 0.0
    for i in selected_indices:
        rec = recommendations[i]
        validity = trade_validity.get(i, {})
        price = validity.get("price", 0) or 0
        original_quantity = rec.get("quantity", 0)
        qty_key = f"pending_qty_{log.id}_{i}"
        quantity = st.session_state.pending_qty_adjustments.get(qty_key, original_quantity)
        action = rec.get("action", "")

        if quantity <= 0:
            continue  # Skip trades with 0 quantity

        if action == "BUY" and price > 0:
            total_buy_cost += price * quantity
        elif action == "SELL" and price > 0:
            total_sell_proceeds += price * quantity

    net_cash_change = total_sell_proceeds - total_buy_cost
    cash_after_trades = available_cash + net_cash_change
    has_sufficient_cash = cash_after_trades >= 0 or is_empty_portfolio
    needs_cash_override = not has_sufficient_cash and len(selected_indices) > 0
    allow_negative_cash = False

    # Show cash summary
    st.markdown(f"**Available Cash:** ${available_cash:,.2f}")
    if len(selected_indices) > 0:
        summary_parts = []
        if total_sell_proceeds > 0:
            summary_parts.append(f"+${total_sell_proceeds:,.2f} (sells)")
        if total_buy_cost > 0:
            summary_parts.append(f"-${total_buy_cost:,.2f} (buys)")

        if summary_parts:
            st.write(f"**After trades:** {' '.join(summary_parts)} = ${cash_after_trades:,.2f}")

        if not has_sufficient_cash:
            st.error(f"⚠️ Insufficient cash! Need ${-cash_after_trades:,.2f} more.")
            allow_negative_cash = st.checkbox(
                "Apply anyway (allow negative cash balance)",
                key=f"allow_negative_cash_{log.id}",
                help="Override cash validation and execute selected BUY trades.",
            )
        elif is_empty_portfolio and cash_after_trades < 0:
            st.info(f"ℹ️ Initial portfolio setup - cash will be increased by ${-cash_after_trades:,.2f}")

    col1, col2 = st.columns([1, 3])
    with col1:
        button_disabled = len(selected_indices) == 0 or (
            needs_cash_override and not allow_negative_cash
        )
        if st.button(
            f"✓ Apply {len(selected_indices)} Trade(s)",
            key=f"apply_pending_{log.id}",
            type="primary",
            disabled=button_disabled,
        ):
            # Build ticker corrections map
            ticker_corrections = {}
            for i in pending_indices:
                key_prefix = f"pending_{log.id}_{i}"
                correction_key = f"{key_prefix}_ticker_correction"
                if correction_key in st.session_state:
                    ticker_corrections[i] = st.session_state[correction_key]

            # Build quantity adjustments map
            quantity_adjustments = {}
            for i in selected_indices:
                qty_key = f"pending_qty_{log.id}_{i}"
                if qty_key in st.session_state.pending_qty_adjustments:
                    quantity_adjustments[i] = st.session_state.pending_qty_adjustments[qty_key]

            _apply_pending_trades(
                log, recommendations, selected_indices, log_service, ticker_corrections,
                quantity_adjustments=quantity_adjustments,
                increase_cash_if_needed=is_empty_portfolio,
                allow_negative_cash=allow_negative_cash,
            )

            # Clear ticker corrections and quantity adjustments after applying
            clear_ticker_corrections([f"pending_{log.id}_{i}" for i in pending_indices])
            for i in pending_indices:
                qty_key = f"pending_qty_{log.id}_{i}"
                st.session_state.pending_qty_adjustments.pop(qty_key, None)

    with col2:
        if len(selected_indices) == 0:
            st.caption("Select valid trades to apply")
        else:
            # Show summary
            buys = sum(1 for i in selected_indices if recommendations[i].get("action") == "BUY")
            sells = len(selected_indices) - buys
            st.caption(f"Selected: {buys} BUY, {sells} SELL")


def _reject_trade(log, trade_index: int, log_service: ExecutionLogService) -> None:
    """Reject a single trade."""
    # Get existing rejected trades
    rejected = set()
    if log.rejected_trades_json:
        try:
            rejected = set(json.loads(log.rejected_trades_json))
        except json.JSONDecodeError:
            pass
    
    rejected.add(trade_index)
    log_service.mark_trades_rejected(log.id, list(rejected))
    
    st.session_state["pending_trades_messages"] = [{
        "type": "info",
        "text": "Trade rejected.",
    }]
    st.rerun()


def _apply_pending_trades(
    log,
    recommendations: list[dict],
    selected_indices: list[int],
    log_service: ExecutionLogService,
    ticker_corrections: dict[int, str] | None = None,
    quantity_adjustments: dict[int, float] | None = None,
    increase_cash_if_needed: bool = False,
    allow_negative_cash: bool = False,
) -> None:
    """Apply selected pending trades to the portfolio.

    Args:
        log: The execution log entry
        recommendations: List of trade recommendations
        selected_indices: Indices of trades to apply
        log_service: Service for updating execution logs
        ticker_corrections: Optional dict mapping trade index to corrected ticker
        quantity_adjustments: Optional dict mapping trade index to adjusted quantity
        increase_cash_if_needed: If True, increase cash for initial portfolio setup
        allow_negative_cash: If True, allow BUY trades to reduce cash below zero
    """
    if ticker_corrections is None:
        ticker_corrections = {}
    if quantity_adjustments is None:
        quantity_adjustments = {}

    security_service = SecurityService()
    portfolio_service = PortfolioService(security_service=security_service)

    # Find the portfolio config file
    portfolios = portfolio_service.list_portfolios()
    portfolio_filename = None
    for filename in portfolios:
        config, _ = portfolio_service.load_portfolio(filename)
        if config.name == log.portfolio_name:
            portfolio_filename = filename
            break

    if not portfolio_filename:
        st.error(f"Could not find portfolio '{log.portfolio_name}'")
        return

    config, state = portfolio_service.load_portfolio(portfolio_filename)

    quoted_prices: dict[str, float] = {}
    try:
        for i in selected_indices:
            rec = recommendations[i]
            ticker = ticker_corrections.get(i, rec.get("ticker", ""))
            quantity = quantity_adjustments.get(i, rec.get("quantity", 0))
            if quantity <= 0 or not ticker:
                continue
            if ticker not in quoted_prices:
                quoted_prices[ticker] = security_service.get_price(ticker)
    except Exception as e:
        st.error(f"Failed to capture quoted prices: {e}")
        return

    # If this is an empty portfolio and we need more cash, increase it
    if increase_cash_if_needed:
        # Calculate total cost of BUY trades (using adjusted quantities)
        total_buy_cost = 0.0
        for i in selected_indices:
            rec = recommendations[i]
            if rec.get("action") == "BUY":
                ticker = ticker_corrections.get(i, rec.get("ticker", ""))
                quantity = quantity_adjustments.get(i, rec.get("quantity", 0))
                if quantity <= 0:
                    continue
                price = quoted_prices.get(ticker)
                if price is not None:
                    total_buy_cost += price * quantity

        # If we need more cash, increase it
        if total_buy_cost > state.cash:
            cash_needed = total_buy_cost - state.cash
            state.cash += cash_needed + 100  # Add a small buffer

        # Record actual initial investment (cash before first trades)
        state.initial_investment = state.cash

    errors = []
    applied_indices = []

    # Sort trades: SELL first, then BUY (so cash from sells is available for buys)
    sorted_indices = sorted(
        selected_indices,
        key=lambda i: 0 if recommendations[i].get("action") == "SELL" else 1
    )

    for i in sorted_indices:
        rec = recommendations[i]
        # Use corrected ticker if available, otherwise use original
        ticker = ticker_corrections.get(i, rec.get("ticker", ""))
        action = rec.get("action", "")
        # Use adjusted quantity if available, otherwise use original
        quantity = quantity_adjustments.get(i, rec.get("quantity", 0))
        reasoning = rec.get("reasoning", "")
        stop_loss_price = rec.get("stop_loss_price")
        take_profit_price = rec.get("take_profit_price")

        # Skip trades with 0 quantity
        if quantity <= 0:
            continue

        try:
            state = portfolio_service.execute_trade(
                state,
                ticker,
                action,
                quantity,
                reasoning,
                price=quoted_prices[ticker],
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                asset_class=config.asset_class,
                allow_negative_cash=allow_negative_cash,
            )
            applied_indices.append(i)
        except Exception as e:
            errors.append(f"{action} {quantity} {ticker}: {str(e)}")

    # Save state
    portfolio_service.save_state(portfolio_filename, state)

    # Update executed trades in log
    existing_executed = set()
    if log.executed_trades_json:
        try:
            existing_executed = set(json.loads(log.executed_trades_json))
        except json.JSONDecodeError:
            pass

    all_executed = list(existing_executed | set(applied_indices))
    log_service.mark_trades_executed(log.id, all_executed)

    # Store messages in session state for persistence across rerun
    messages = []
    if applied_indices:
        messages.append({
            "type": "success",
            "text": f"Successfully applied {len(applied_indices)} trade(s)!",
        })

    if errors:
        for error in errors:
            messages.append({
                "type": "error",
                "text": error,
            })

    if messages:
        st.session_state["pending_trades_messages"] = messages

    st.rerun()


def _render_add_manual_trade(
    portfolio_service: PortfolioService,
    security_service: SecurityService,
    log_service: ExecutionLogService,
) -> None:
    """Render a form to add a manual pending trade."""
    portfolio_filenames = portfolio_service.list_portfolios()
    if not portfolio_filenames:
        return

    portfolio_configs: dict[str, tuple[str, AssetClass]] = {}
    for filename in portfolio_filenames:
        config, _ = portfolio_service.load_portfolio(filename)
        portfolio_configs[config.name] = (filename, config.asset_class)

    cached_ticker_names: dict[str, str] = {
        t: sec.name for t, sec in security_service._by_ticker.items()
    }
    cached_tickers = sorted(cached_ticker_names.keys())

    def _format_ticker(t: str) -> str:
        name = cached_ticker_names.get(t)
        return f"{t} — {name}" if name and name != t else t

    with st.expander("➕ Add Manual Trade", expanded=False):
        with st.form("add_manual_trade_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                selected_portfolio_name = st.selectbox(
                    "Portfolio",
                    options=list(portfolio_configs.keys()),
                )

            with col2:
                action = st.selectbox("Action", options=["BUY", "SELL"])

            with col3:
                ticker_selection = st.selectbox(
                    "Ticker",
                    options=cached_tickers,
                    index=None,
                    placeholder="Search cached or type a new ticker",
                    accept_new_options=True,
                    format_func=_format_ticker,
                )
                ticker = (ticker_selection or "").strip().upper()

            asset_class = portfolio_configs[selected_portfolio_name][1]
            unit_label = "Units" if asset_class == AssetClass.CRYPTO else "Shares"

            col4, col5, col6 = st.columns(3)
            with col4:
                if asset_class == AssetClass.CRYPTO:
                    quantity = st.number_input(
                        unit_label, min_value=0.0, value=0.0, step=0.0001, format="%.8f"
                    )
                else:
                    quantity = st.number_input(
                        unit_label, min_value=0, value=0, step=1
                    )

            with col5:
                stop_loss_price = st.number_input(
                    "Stop-loss price (optional)",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                )

            with col6:
                take_profit_price = st.number_input(
                    "Take-profit price (optional)",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                )

            reasoning = st.text_area(
                "Reasoning (optional)",
                placeholder="Why are you placing this trade?",
            )

            submitted = st.form_submit_button("Add to Pending Trades", type="primary")

            if submitted:
                _submit_manual_trade(
                    portfolio_name=selected_portfolio_name,
                    ticker=ticker,
                    action=action,
                    quantity=quantity,
                    stop_loss_price=stop_loss_price if stop_loss_price > 0 else None,
                    take_profit_price=take_profit_price if take_profit_price > 0 else None,
                    reasoning=reasoning.strip(),
                    security_service=security_service,
                    log_service=log_service,
                )


def _submit_manual_trade(
    portfolio_name: str,
    ticker: str,
    action: str,
    quantity: float,
    stop_loss_price: float | None,
    take_profit_price: float | None,
    reasoning: str,
    security_service: SecurityService,
    log_service: ExecutionLogService,
) -> None:
    """Validate and persist a manual trade as a new pending execution log entry."""
    if not ticker:
        st.error("Ticker is required.")
        return
    if quantity <= 0:
        st.error("Quantity must be greater than zero.")
        return

    try:
        price = security_service.get_price(ticker)
    except Exception as e:
        st.error(f"Could not look up ticker '{ticker}': {e}")
        return

    if not price or price <= 0:
        st.error(f"Ticker '{ticker}' not found or has no price.")
        return

    recommendation = {
        "ticker": ticker,
        "name": ticker,
        "action": action,
        "quantity": quantity,
        "reasoning": reasoning or "Manually added trade.",
    }
    if stop_loss_price is not None:
        recommendation["stop_loss_price"] = stop_loss_price
    if take_profit_price is not None:
        recommendation["take_profit_price"] = take_profit_price

    log_service.log_execution(
        portfolio_name=portfolio_name,
        agent_mode="manual",
        model="manual",
        duration_ms=0,
        input_tokens=0,
        output_tokens=0,
        num_trades=1,
        success=True,
        recommendations=[recommendation],
    )

    st.session_state["pending_trades_messages"] = [{
        "type": "success",
        "text": f"Added manual {action} {quantity} {ticker} to pending trades.",
    }]
    st.rerun()
