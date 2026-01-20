"""Portfolio detail page."""

from collections.abc import Callable

import streamlit as st
import plotly.graph_objects as go

from fin_trade.models import PortfolioConfig, PortfolioState, TradeRecommendation
from fin_trade.services import PortfolioService, AgentService, StockDataService
from fin_trade.components.trade_display import (
    render_trade_recommendations,
    render_trade_history,
)


def render_portfolio_detail_page(
    portfolio_name: str,
    portfolio_service: PortfolioService,
    agent_service: AgentService,
    stock_service: StockDataService,
    on_back: Callable | None = None,
) -> None:
    """Render the portfolio detail page."""
    try:
        config, state = portfolio_service.load_portfolio(portfolio_name)
    except Exception as e:
        st.error(f"Failed to load portfolio: {e}")
        if on_back and st.button("Back to Overview"):
            on_back()
        return

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("< Back"):
            if on_back:
                on_back()
            return

    with col2:
        st.title(config.name)

    _render_summary(config, state, portfolio_service)

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["Holdings", "Performance", "Execute Agent", "Trade History"])

    with tab1:
        _render_holdings(state, stock_service)

    with tab2:
        _render_performance_chart(config, state, stock_service)

    with tab3:
        _render_agent_execution(
            config, state, portfolio_service, agent_service, stock_service, portfolio_name
        )

    with tab4:
        render_trade_history(state.trades, stock_service)


def _render_summary(
    config: PortfolioConfig,
    state: PortfolioState,
    portfolio_service: PortfolioService,
) -> None:
    """Render the portfolio summary metrics."""
    value = portfolio_service.calculate_value(state)
    abs_gain, pct_gain = portfolio_service.calculate_gain(config, state)
    is_overdue = portfolio_service.is_execution_overdue(config, state)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Portfolio Value", f"${value:,.2f}")

    with col2:
        st.metric(
            "Gain/Loss",
            f"${abs_gain:,.2f}",
            delta=f"{pct_gain:+.1f}%",
        )

    with col3:
        st.metric("Cash Available", f"${state.cash:,.2f}")

    with col4:
        if is_overdue:
            st.metric("Status", "OVERDUE", delta="-Needs execution")
        else:
            st.metric("Status", "Current")

    with st.expander("Portfolio Configuration"):
        st.write(f"**Strategy:** {config.strategy_prompt[:200]}...")
        st.write(f"**Initial Amount:** ${config.initial_amount:,.2f}")
        st.write(f"**Run Frequency:** {config.run_frequency}")
        st.write(f"**Trades per Run:** {config.trades_per_run}")
        st.write(f"**LLM:** {config.llm_provider} / {config.llm_model}")


def _render_holdings(state: PortfolioState, stock_service: StockDataService) -> None:
    """Render the holdings table."""
    st.subheader("Current Holdings")

    if not state.holdings:
        st.info("No holdings. Execute the agent to start trading.")
        return

    for holding in state.holdings:
        ticker = stock_service.get_ticker(holding.isin)
        try:
            current_price = stock_service.get_price(holding.isin)
            current_value = current_price * holding.quantity
            cost_basis = holding.avg_price * holding.quantity
            gain = current_value - cost_basis
            gain_pct = (gain / cost_basis) * 100 if cost_basis > 0 else 0
        except Exception:
            current_price = holding.avg_price
            current_value = holding.avg_price * holding.quantity
            gain = 0
            gain_pct = 0

        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

        with col1:
            st.write(f"**{ticker}**")
            st.caption(holding.isin)

        with col2:
            st.write(f"{holding.quantity} shares")

        with col3:
            st.write(f"Avg: ${holding.avg_price:.2f}")

        with col4:
            st.write(f"Now: ${current_price:.2f}")

        with col5:
            gain_color = "green" if gain >= 0 else "red"
            st.markdown(f"**:{gain_color}[${gain:,.2f}]**")
            st.caption(f"{gain_pct:+.1f}%")

        st.divider()


def _render_performance_chart(
    config: PortfolioConfig,
    state: PortfolioState,
    stock_service: StockDataService,
) -> None:
    """Render the portfolio performance chart."""
    st.subheader("Performance")

    if not state.trades:
        st.info("No trade history to display.")
        return

    timestamps = []
    values = []
    running_value = config.initial_amount

    for trade in state.trades:
        timestamps.append(trade.timestamp)
        if trade.action == "BUY":
            running_value -= trade.price * trade.quantity
        else:
            running_value += trade.price * trade.quantity
        values.append(running_value)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=values,
            mode="lines+markers",
            name="Portfolio Value",
            line=dict(color="#00d4ff", width=2),
            marker=dict(size=6),
        )
    )

    fig.add_hline(
        y=config.initial_amount,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Initial: ${config.initial_amount:,.0f}",
    )

    fig.update_layout(
        title="Portfolio Value Over Time",
        xaxis_title="Date",
        yaxis_title="Value ($)",
        height=400,
        template="plotly_dark",
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_agent_execution(
    config: PortfolioConfig,
    state: PortfolioState,
    portfolio_service: PortfolioService,
    agent_service: AgentService,
    stock_service: StockDataService,
    portfolio_name: str,
) -> None:
    """Render the agent execution section."""
    st.subheader("Execute Trading Agent")

    is_overdue = portfolio_service.is_execution_overdue(config, state)

    if is_overdue:
        st.warning("This portfolio is overdue for execution!")

    if state.last_execution:
        st.caption(f"Last executed: {state.last_execution.strftime('%Y-%m-%d %H:%M')}")

    if "recommendation" not in st.session_state:
        st.session_state.recommendation = None

    execute_button_type = "primary" if is_overdue else "secondary"

    if st.button("Run Agent", type=execute_button_type, key="run_agent"):
        with st.spinner("Agent is analyzing portfolio..."):
            try:
                recommendation = agent_service.execute(config, state)
                st.session_state.recommendation = recommendation
                st.rerun()
            except Exception as e:
                st.error(f"Agent execution failed: {e}")

    if st.session_state.recommendation:
        def on_accept(trades: list[TradeRecommendation]) -> None:
            nonlocal state
            try:
                for trade in trades:
                    state = portfolio_service.execute_trade(
                        state,
                        trade.isin,
                        trade.action,
                        trade.quantity,
                        trade.reasoning,
                    )
                portfolio_service.save_state(portfolio_name, state)
                st.session_state.recommendation = None
                st.success(f"Successfully executed {len(trades)} trades!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to execute trades: {e}")

        def on_retry() -> None:
            st.session_state.recommendation = None
            st.rerun()

        render_trade_recommendations(
            st.session_state.recommendation,
            stock_service,
            on_accept=on_accept,
            on_retry=on_retry,
        )
