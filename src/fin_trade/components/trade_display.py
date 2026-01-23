"""Trade recommendation display component."""

from collections.abc import Callable
from dataclasses import replace

import streamlit as st

from fin_trade.models import AgentRecommendation, TradeRecommendation, Holding
from fin_trade.services.security import SecurityService
from fin_trade.components.skeleton import render_skeleton_table


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

    # Fix formatting issues in agent output
    # 1. Limit height of reasoning text
    # 2. Prevent broken links by rendering as plain text or handling them
    
    with st.container(border=True):
        st.markdown("### Analysis")
        # Use a scrollable container for long text
        with st.container(height=300):
            st.markdown(recommendation.overall_reasoning)

    if not recommendation.trades:
        st.caption(f"Available cash: **${available_cash:,.2f}**")
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

    # Calculate potential cash from valid SELL orders for display
    potential_sell_cash = 0.0
    for info in trade_info:
        trade = info["trade"]
        if trade.action == "SELL" and info["price"] and info["price"] > 0:
            held_qty = holdings_by_ticker.get(info["corrected_ticker"], 0)
            if held_qty >= trade.quantity:
                potential_sell_cash += info["cost"]

    # Show available cash (including potential proceeds from sells)
    if potential_sell_cash > 0:
        total_available = available_cash + potential_sell_cash
        st.caption(
            f"Available cash: **${available_cash:,.2f}** + "
            f"~${potential_sell_cash:,.2f} from sells = **${total_available:,.2f}**"
        )
    else:
        st.caption(f"Available cash: **${available_cash:,.2f}**")

    # Calculate which trades are executable
    # Process SELL orders first to determine available cash from sells,
    # then check BUY orders against total available cash (current + from sells)
    simulated_holdings = holdings_by_ticker.copy()

    # First pass: determine executability of SELL orders and calculate cash from sells
    cash_from_sells = 0.0
    for info in trade_info:
        trade = info["trade"]
        if trade.action != "SELL":
            continue

        corrected_ticker = info["corrected_ticker"]
        price = info["price"]
        cost = info["cost"]
        price_error = info["price_error"]

        can_execute = True
        cannot_execute_reason = None

        if price_error or price == 0:
            can_execute = False
            cannot_execute_reason = "Price unavailable"
        else:
            held_qty = simulated_holdings.get(corrected_ticker, 0)
            if held_qty < trade.quantity:
                can_execute = False
                cannot_execute_reason = f"Insufficient holdings (need {trade.quantity}, have {held_qty})"
            else:
                # Valid SELL - add to available cash
                cash_from_sells += cost
                simulated_holdings[corrected_ticker] = held_qty - trade.quantity

        info["can_execute"] = can_execute
        info["cannot_execute_reason"] = cannot_execute_reason

    # Second pass: determine executability of BUY orders using cash + proceeds from sells
    remaining_cash = available_cash + cash_from_sells
    for info in trade_info:
        trade = info["trade"]
        if trade.action != "BUY":
            continue

        corrected_ticker = info["corrected_ticker"]
        price = info["price"]
        cost = info["cost"]
        price_error = info["price_error"]

        can_execute = True
        cannot_execute_reason = None

        if price_error or price == 0:
            can_execute = False
            cannot_execute_reason = "Price unavailable"
        elif cost > remaining_cash:
            can_execute = False
            cannot_execute_reason = f"Insufficient cash (need ${cost:,.2f}, have ${remaining_cash:,.2f})"
        else:
            # Valid BUY - deduct from remaining cash
            remaining_cash -= cost
            simulated_holdings[corrected_ticker] = simulated_holdings.get(corrected_ticker, 0) + trade.quantity

        info["can_execute"] = can_execute
        info["cannot_execute_reason"] = cannot_execute_reason

    # Reset simulated state for UI rendering (will be updated based on user selections)
    simulated_holdings = holdings_by_ticker.copy()
    remaining_cash = available_cash

    selected_trades = []
    for info in trade_info:
        i = info["index"]
        trade = info["trade"]
        corrected_ticker = info["corrected_ticker"]
        price = info["price"]
        cost = info["cost"]
        price_error = info["price_error"]
        security_info = info["security_info"]
        can_execute = info["can_execute"]
        cannot_execute_reason = info["cannot_execute_reason"]

        # Matrix colors
        action_color = "#00ff41" if trade.action == "BUY" else "#ff0000"

        # Auto-enable checkbox when a corrected ticker becomes valid
        # This handles the case where user fixes an invalid ticker
        checkbox_key = f"trade_{i}"
        was_corrected = corrected_ticker != trade.ticker
        if was_corrected and can_execute:
            # Force checkbox to be checked when correction makes trade valid
            st.session_state[checkbox_key] = True

        with st.container(border=True):
            # Header row with action and stock info
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.markdown(f"### <span style='color:{action_color}'>{trade.action}</span>", unsafe_allow_html=True)
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
                    key=checkbox_key,
                    disabled=not can_execute,
                )

            # Show warning if trade cannot be executed
            if not can_execute and cannot_execute_reason:
                st.warning(f"⚠️ {cannot_execute_reason}")

            # Show success message if ticker was corrected and is now valid
            if was_corrected and can_execute:
                st.success(f"✓ Ticker corrected to {corrected_ticker} - trade is now ready!")

            # Show error and correction UI if price fetch failed
            if price_error:
                st.error(f"Could not find price for '{corrected_ticker}'.")
                
                # Inline correction UI
                with st.container():
                    col_label, col_input, col_btn = st.columns([2, 3, 1])
                    with col_label:
                        st.markdown("**Did you mean?**")
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
    import pandas as pd

    if not trades:
        st.info("No trades executed yet.")
        return

    st.subheader("Trade History")

    # Show skeleton placeholder while building table
    table_placeholder = st.empty()
    with table_placeholder.container():
        render_skeleton_table(rows=min(len(trades), 10), cols=8)

    # Build trade data for DataFrame
    trade_data = []
    for trade in trades:
        total = trade.price * trade.quantity
        trade_data.append({
            "Date": trade.timestamp,
            "Action": trade.action,
            "Ticker": trade.ticker,
            "Name": trade.name,
            "Shares": trade.quantity,
            "Price": trade.price,
            "Total": total,
            "Reasoning": trade.reasoning,
        })

    df = pd.DataFrame(trade_data)
    # Sort by date descending
    df = df.sort_values("Date", ascending=False)

    # Replace skeleton with actual table
    with table_placeholder.container():
        st.dataframe(
            df,
            column_config={
                "Date": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD HH:mm"),
                "Action": st.column_config.TextColumn("Action", width="small"),
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Name": st.column_config.TextColumn("Name", width="medium"),
                "Shares": st.column_config.NumberColumn("Shares", format="%d"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Total": st.column_config.NumberColumn("Total", format="$%.2f"),
                "Reasoning": st.column_config.TextColumn("Reasoning", width="large"),
            },
            hide_index=True,
            use_container_width=True,
        )
