"""Trade recommendation display component."""

from collections.abc import Callable
from dataclasses import replace

import streamlit as st

from fin_trade.models import AgentRecommendation, TradeRecommendation, Holding
from fin_trade.services.security import SecurityService


def render_trade_recommendations(
    recommendation: AgentRecommendation,
    security_service: SecurityService,
    available_cash: float,
    holdings: list[Holding],
    on_accept: Callable | None = None,
    on_retry: Callable | None = None,
) -> list[TradeRecommendation] | None:
    """Render trade recommendations and return accepted trades.

    Args:
        recommendation: The agent's recommendations
        security_service: Service for price lookups
        available_cash: Current cash balance for affordability checks
        holdings: Current holdings for sell validation
        on_accept: Callback when trades are accepted
        on_retry: Callback to retry agent
    """
    st.subheader("Agent Recommendations")

    st.info(recommendation.overall_reasoning)

    # Show available cash
    st.caption(f"Available cash: **${available_cash:,.2f}**")

    if not recommendation.trades:
        st.warning("The agent recommends no trades at this time.")
        if on_retry:
            if st.button("Retry", key="retry_no_trades", type="secondary"):
                on_retry()
        return None

    # Initialize session state for ticker corrections
    if "ticker_corrections" not in st.session_state:
        st.session_state.ticker_corrections = {}
    if "isin_inputs" not in st.session_state:
        st.session_state.isin_inputs = {}

    # Build holdings lookup
    holdings_by_ticker = {h.ticker: h.quantity for h in holdings}

    # First pass: collect all trade info with prices
    trade_info = []
    for i, trade in enumerate(recommendation.trades):
        corrected_ticker = st.session_state.ticker_corrections.get(i, trade.ticker)

        price = None
        price_error = None
        security_info = None
        cost = 0

        try:
            price = security_service.get_price(corrected_ticker)
            cost = price * trade.quantity
            security = security_service.lookup_ticker(corrected_ticker)
            security_info = security
        except Exception as e:
            price_error = str(e)
            price = 0
            cost = 0

        trade_info.append({
            "index": i,
            "trade": trade,
            "corrected_ticker": corrected_ticker,
            "price": price,
            "cost": cost,
            "price_error": price_error,
            "security_info": security_info,
        })

    # Calculate which trades are executable
    remaining_cash = available_cash
    simulated_holdings = holdings_by_ticker.copy()

    selected_trades = []
    for info in trade_info:
        i = info["index"]
        trade = info["trade"]
        corrected_ticker = info["corrected_ticker"]
        price = info["price"]
        cost = info["cost"]
        price_error = info["price_error"]
        security_info = info["security_info"]

        action_color = "green" if trade.action == "BUY" else "red"

        # Determine if trade is executable
        can_execute = True
        cannot_execute_reason = None

        if price_error or price == 0:
            can_execute = False
            cannot_execute_reason = "Price unavailable"
        elif trade.action == "BUY":
            if cost > remaining_cash:
                can_execute = False
                cannot_execute_reason = f"Insufficient cash (need ${cost:,.2f}, have ${remaining_cash:,.2f})"
        elif trade.action == "SELL":
            held_qty = simulated_holdings.get(corrected_ticker, 0)
            if held_qty < trade.quantity:
                can_execute = False
                cannot_execute_reason = f"Insufficient holdings (need {trade.quantity}, have {held_qty})"

        with st.container(border=True):
            # Header row with action and stock info
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.markdown(f"### :{action_color}[{trade.action}]")
                st.markdown(f"**{corrected_ticker}**")
                st.caption(trade.name)

            with col2:
                if price and price > 0:
                    st.metric("Price", f"${price:.2f}", label_visibility="collapsed")
                    st.write(f"{trade.quantity} shares × ${price:.2f} = **${cost:,.2f}**")
                else:
                    st.write(f"{trade.quantity} shares")
                    if price_error:
                        st.caption("Price unavailable")

            with col3:
                include = st.checkbox(
                    "Include",
                    value=can_execute,
                    key=f"trade_{i}",
                    disabled=not can_execute,
                )

            # Show warning if trade cannot be executed
            if not can_execute and cannot_execute_reason:
                st.warning(f"⚠️ {cannot_execute_reason}")

            # Show error and correction UI if price fetch failed
            if price_error:
                with st.expander("🔧 Correct Ticker Symbol", expanded=True):
                    st.caption("The ticker symbol might be incorrect. Enter the correct symbol:")
                    col_input, col_btn = st.columns([3, 1])
                    with col_input:
                        new_ticker = st.text_input(
                            "Correct ticker",
                            value=corrected_ticker,
                            key=f"ticker_input_{i}",
                            label_visibility="collapsed",
                            placeholder="e.g., AAPL, MSFT",
                        )
                    with col_btn:
                        if st.button("Verify", key=f"verify_ticker_{i}", type="secondary"):
                            st.session_state.ticker_corrections[i] = new_ticker.upper()
                            st.rerun()

            # Check if ISIN is missing/unknown
            if security_info and security_info.isin.startswith("UNKNOWN-"):
                with st.expander("📝 ISIN Missing - Please Provide", expanded=False):
                    st.caption(
                        f"yfinance couldn't find the ISIN for {corrected_ticker}. "
                        "Please enter it manually for better tracking:"
                    )
                    isin_input = st.text_input(
                        "ISIN",
                        value=st.session_state.isin_inputs.get(i, ""),
                        key=f"isin_input_{i}",
                        placeholder="e.g., US0378331005",
                    )
                    if isin_input:
                        st.session_state.isin_inputs[i] = isin_input

            st.caption(f"💭 {trade.reasoning}")

            # Track selected trades and update simulated state
            if include and can_execute:
                modified_trade = trade
                if corrected_ticker != trade.ticker:
                    modified_trade = replace(trade, ticker=corrected_ticker)
                selected_trades.append(modified_trade)

                # Update simulated cash/holdings for subsequent trades
                if trade.action == "BUY":
                    remaining_cash -= cost
                    simulated_holdings[corrected_ticker] = simulated_holdings.get(corrected_ticker, 0) + trade.quantity
                elif trade.action == "SELL":
                    remaining_cash += cost
                    simulated_holdings[corrected_ticker] = simulated_holdings.get(corrected_ticker, 0) - trade.quantity

    st.divider()

    # Show summary of selected trades
    if selected_trades:
        total_buy = sum(
            info["cost"] for info in trade_info
            if info["trade"].action == "BUY" and any(
                t.ticker == info["corrected_ticker"] for t in selected_trades
            )
        )
        total_sell = sum(
            info["cost"] for info in trade_info
            if info["trade"].action == "SELL" and any(
                t.ticker == info["corrected_ticker"] for t in selected_trades
            )
        )
        st.caption(f"Selected: {len(selected_trades)} trades | Buy: ${total_buy:,.2f} | Sell: ${total_sell:,.2f} | Net: ${total_sell - total_buy:,.2f}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✓ Accept Selected", type="primary", key="accept_trades",
                     disabled=len(selected_trades) == 0):
            if selected_trades and on_accept:
                # Apply any user-provided ISINs before accepting
                for i, isin in st.session_state.isin_inputs.items():
                    if isin and i < len(recommendation.trades):
                        ticker = st.session_state.ticker_corrections.get(
                            i, recommendation.trades[i].ticker
                        )
                        try:
                            security_service.update_isin(ticker, isin)
                        except Exception:
                            pass  # Ignore errors, the trade will still work

                # Clear corrections from session state
                st.session_state.ticker_corrections = {}
                st.session_state.isin_inputs = {}
                on_accept(selected_trades)
                return selected_trades

    with col2:
        if st.button("↻ Retry", key="retry_trades", type="secondary"):
            # Clear corrections
            st.session_state.ticker_corrections = {}
            st.session_state.isin_inputs = {}
            if on_retry:
                on_retry()

    if len(selected_trades) == 0:
        st.warning("No trades selected. Fix ticker symbols above or retry with the agent.")

    return None


def render_trade_history(trades: list, security_service: SecurityService) -> None:
    """Render the trade history table."""
    if not trades:
        st.info("No trades executed yet.")
        return

    st.subheader("Trade History")

    for trade in reversed(trades[-20:]):
        action_color = "green" if trade.action == "BUY" else "red"
        total = trade.price * trade.quantity

        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([1, 2, 2, 1])

            with col1:
                st.write(trade.timestamp.strftime("%Y-%m-%d"))

            with col2:
                st.markdown(f"**:{action_color}[{trade.action}]** {trade.ticker}")
                st.caption(trade.name)

            with col3:
                st.write(f"{trade.quantity} × ${trade.price:.2f}")

            with col4:
                st.write(f"**${total:,.2f}**")

            st.caption(f"💭 {trade.reasoning}")
