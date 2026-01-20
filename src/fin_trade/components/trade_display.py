"""Trade recommendation display component."""

from collections.abc import Callable

import streamlit as st

from fin_trade.models import AgentRecommendation, TradeRecommendation
from fin_trade.services.stock_data import StockDataService


def render_trade_recommendations(
    recommendation: AgentRecommendation,
    stock_service: StockDataService,
    on_accept: Callable | None = None,
    on_retry: Callable | None = None,
) -> list[TradeRecommendation] | None:
    """Render trade recommendations and return accepted trades."""
    st.subheader("Agent Recommendations")

    st.info(recommendation.overall_reasoning)

    if not recommendation.trades:
        st.warning("The agent recommends no trades at this time.")
        if on_retry:
            if st.button("Retry", key="retry_no_trades"):
                on_retry()
        return None

    selected_trades = []
    for i, trade in enumerate(recommendation.trades):
        ticker = stock_service.get_ticker(trade.isin)
        try:
            price = stock_service.get_price(trade.isin)
            cost = price * trade.quantity
        except Exception as e:
            st.warning(f"Could not fetch price for {ticker}: {e}")
            price = 0
            cost = 0

        action_color = "green" if trade.action == "BUY" else "red"

        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])

            with col1:
                st.markdown(f"**:{action_color}[{trade.action}]**")
                st.caption(f"{ticker}")

            with col2:
                st.write(f"{trade.quantity} shares @ ${price:.2f}")
                st.caption(f"Total: ${cost:.2f}")

            with col3:
                include = st.checkbox(
                    "Include",
                    value=True,
                    key=f"trade_{i}",
                )
                if include:
                    selected_trades.append(trade)

            with st.expander("Reasoning"):
                st.write(trade.reasoning)

            st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Accept Selected", type="primary", key="accept_trades"):
            if selected_trades and on_accept:
                on_accept(selected_trades)
                return selected_trades

    with col2:
        if st.button("Retry", key="retry_trades"):
            if on_retry:
                on_retry()

    return None


def render_trade_history(trades: list, stock_service: StockDataService) -> None:
    """Render the trade history table."""
    if not trades:
        st.info("No trades executed yet.")
        return

    st.subheader("Trade History")

    for trade in reversed(trades[-20:]):
        ticker = stock_service.get_ticker(trade.isin)
        action_color = "green" if trade.action == "BUY" else "red"
        total = trade.price * trade.quantity

        col1, col2, col3, col4 = st.columns([1, 1, 2, 1])

        with col1:
            st.write(trade.timestamp.strftime("%Y-%m-%d"))

        with col2:
            st.markdown(f"**:{action_color}[{trade.action}]** {ticker}")

        with col3:
            st.write(f"{trade.quantity} @ ${trade.price:.2f}")

        with col4:
            st.write(f"${total:.2f}")

        with st.expander("Reasoning", expanded=False):
            st.write(trade.reasoning)
