"""Pending Trades page for reviewing and applying agent recommendations."""

import json

import streamlit as st
import pandas as pd

from fin_trade.services.execution_log import ExecutionLogService
from fin_trade.services import PortfolioService
from fin_trade.services.security import SecurityService


def render_pending_trades_page() -> None:
    """Render the pending trades page."""
    st.title("📋 Pending Trades")
    st.caption("Review and apply trade recommendations from agent executions.")

    log_service = ExecutionLogService()

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

            pending_count = len([i for i in range(len(recommendations)) if i not in executed])
            if pending_count > 0:
                logs_with_pending.append((log, recommendations, executed, pending_count))
        except json.JSONDecodeError:
            continue

    if not logs_with_pending:
        st.info("🎉 No pending trades! All recommendations have been applied or there are no recent executions.")
        st.caption("Run agents from the Portfolios page to generate new recommendations.")
        return

    # Summary metrics
    total_pending = sum(count for _, _, _, count in logs_with_pending)
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
        for _, recs, executed, _ in logs_with_pending:
            for i, rec in enumerate(recs):
                if i not in executed:
                    if rec.get("action") == "BUY":
                        total_buys += 1
                    else:
                        total_sells += 1
        st.metric("BUY / SELL", f"{total_buys} / {total_sells}")

    st.divider()

    # Render each execution's pending trades
    for log, recommendations, executed, pending_count in logs_with_pending:
        with st.expander(
            f"**{log.portfolio_name}** — {log.timestamp.strftime('%Y-%m-%d %H:%M')} — {pending_count} pending",
            expanded=True,
        ):
            _render_pending_trades_for_log(log, recommendations, executed, log_service)


def _render_pending_trades_for_log(
    log,
    recommendations: list[dict],
    executed: set,
    log_service: ExecutionLogService,
) -> None:
    """Render pending trades for a single execution log."""
    pending_indices = [i for i in range(len(recommendations)) if i not in executed]

    # Build selection UI
    selected_indices = []

    # Select all checkbox
    select_all_key = f"select_all_{log.id}"
    select_all = st.checkbox("Select all", key=select_all_key)

    for i in pending_indices:
        rec = recommendations[i]
        col1, col2, col3, col4, col5 = st.columns([0.5, 1, 1.5, 1, 4])

        with col1:
            checkbox_key = f"pending_{log.id}_{i}"
            # If select all is checked, this should be checked too
            if select_all:
                st.session_state[checkbox_key] = True
            is_selected = st.checkbox("Select trade", key=checkbox_key, label_visibility="collapsed")
            if is_selected:
                selected_indices.append(i)

        with col2:
            action = rec.get("action", "")
            action_color = "#00ff41" if action == "BUY" else "#ff0000"
            st.markdown(f"<span style='color:{action_color};font-weight:bold'>{action}</span>", unsafe_allow_html=True)

        with col3:
            st.markdown(f"**{rec.get('ticker', '')}**")

        with col4:
            st.write(f"{rec.get('quantity', 0)} shares")

        with col5:
            reasoning = rec.get("reasoning", "")
            st.caption(reasoning[:80] + "..." if len(reasoning) > 80 else reasoning)

    st.markdown("---")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button(
            f"✓ Apply {len(selected_indices)} Trade(s)",
            key=f"apply_pending_{log.id}",
            type="primary",
            disabled=len(selected_indices) == 0,
        ):
            _apply_pending_trades(log, recommendations, selected_indices, log_service)

    with col2:
        if len(selected_indices) == 0:
            st.caption("Select trades to apply")
        else:
            # Show summary
            buys = sum(1 for i in selected_indices if recommendations[i].get("action") == "BUY")
            sells = len(selected_indices) - buys
            st.caption(f"Selected: {buys} BUY, {sells} SELL")


def _apply_pending_trades(
    log,
    recommendations: list[dict],
    selected_indices: list[int],
    log_service: ExecutionLogService,
) -> None:
    """Apply selected pending trades to the portfolio."""
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

    errors = []
    applied_indices = []

    # Sort trades: SELL first, then BUY (so cash from sells is available for buys)
    sorted_indices = sorted(
        selected_indices,
        key=lambda i: 0 if recommendations[i].get("action") == "SELL" else 1
    )

    for i in sorted_indices:
        rec = recommendations[i]
        ticker = rec.get("ticker", "")
        action = rec.get("action", "")
        quantity = rec.get("quantity", 0)
        reasoning = rec.get("reasoning", "")

        try:
            state = portfolio_service.execute_trade(
                state,
                ticker,
                action,
                quantity,
                reasoning,
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

    if applied_indices:
        st.success(f"Successfully applied {len(applied_indices)} trade(s)!")

    if errors:
        for error in errors:
            st.error(error)

    st.rerun()
