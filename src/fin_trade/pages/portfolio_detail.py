"""Portfolio detail page."""

from collections.abc import Callable

import streamlit as st
import plotly.graph_objects as go

from fin_trade.models import PortfolioConfig, PortfolioState, TradeRecommendation
from fin_trade.services import PortfolioService, AgentService, SecurityService
from fin_trade.agents.service import (
    DebateAgentService,
    LangGraphAgentService,
    StepProgress,
    ExecutionMetrics,
)
from fin_trade.components.trade_display import (
    render_trade_recommendations,
    render_trade_history,
)


def render_portfolio_detail_page(
    portfolio_name: str,
    portfolio_service: PortfolioService,
    agent_service: AgentService,
    security_service: SecurityService,
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
        if st.button("← Back to Overview", type="secondary"):
            if on_back:
                on_back()

    with col2:
        st.title(config.name)

    _render_summary(config, state, portfolio_service, security_service)

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["Holdings", "Performance", "Execute Agent", "Trade History"])

    with tab1:
        _render_holdings(state, security_service)

    with tab2:
        _render_performance_chart(config, state, security_service)

    with tab3:
        _render_agent_execution(
            config, state, portfolio_service, agent_service, security_service, portfolio_name
        )

    with tab4:
        render_trade_history(state.trades, security_service)


def _render_summary(
    config: PortfolioConfig,
    state: PortfolioState,
    portfolio_service: PortfolioService,
    security_service: SecurityService,
) -> None:
    """Render the portfolio summary metrics."""
    total_value = portfolio_service.calculate_value(state)
    abs_gain, pct_gain = portfolio_service.calculate_gain(config, state)
    is_overdue = portfolio_service.is_execution_overdue(config, state)

    # Calculate stock holdings value
    stock_value = 0.0
    for holding in state.holdings:
        try:
            price = security_service.get_price(holding.ticker)
            stock_value += price * holding.quantity
        except Exception:
            stock_value += holding.avg_price * holding.quantity

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Value", f"${total_value:,.2f}")

    with col2:
        gain_delta = f"{pct_gain:+.1f}%"
        st.metric("Gain/Loss", f"${abs_gain:,.2f}", delta=gain_delta)

    with col3:
        st.metric("Stock Holdings", f"${stock_value:,.2f}")

    with col4:
        st.metric("Cash Available", f"${state.cash:,.2f}")

    with col5:
        if is_overdue:
            st.markdown(
                """<div style="background: linear-gradient(135deg, #ff6b6b, #ee5a5a);
                padding: 12px; border-radius: 8px; text-align: center;">
                <span style="font-size: 0.8em; color: rgba(255,255,255,0.8);">Status</span><br>
                <span style="font-size: 1.2em; font-weight: bold; color: white;">⚠️ OVERDUE</span>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """<div style="background: linear-gradient(135deg, #51cf66, #40c057);
                padding: 12px; border-radius: 8px; text-align: center;">
                <span style="font-size: 0.8em; color: rgba(255,255,255,0.8);">Status</span><br>
                <span style="font-size: 1.2em; font-weight: bold; color: white;">✓ Current</span>
                </div>""",
                unsafe_allow_html=True,
            )

    with st.expander("Portfolio Configuration"):
        st.write(f"**Strategy:** {config.strategy_prompt[:200]}...")
        st.write(f"**Initial Amount:** ${config.initial_amount:,.2f}")
        st.write(f"**Run Frequency:** {config.run_frequency}")
        st.write(f"**Trades per Run:** {config.trades_per_run}")
        st.write(f"**LLM:** {config.llm_provider} / {config.llm_model}")
        st.write(f"**Agent Mode:** {getattr(config, 'agent_mode', 'simple')}")


def _render_holdings(state: PortfolioState, security_service: SecurityService) -> None:
    """Render the holdings table."""
    st.subheader("Current Holdings")

    if not state.holdings:
        st.info("No holdings. Execute the agent to start trading.")
        return

    for holding in state.holdings:
        try:
            current_price = security_service.get_price(holding.ticker)
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
            st.write(f"**{holding.ticker}**")
            st.caption(holding.name)

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
    security_service: SecurityService,
) -> None:
    """Render the portfolio performance chart."""
    st.subheader("Performance")

    if not state.trades:
        st.info("No trade history to display.")
        return

    # Calculate portfolio value at each trade point
    # Track cash and holdings separately
    timestamps = [None]  # Starting point
    values = [config.initial_amount]  # Initial value

    cash = config.initial_amount
    holdings: dict[str, dict] = {}  # ticker -> {quantity, avg_price}

    for trade in state.trades:
        trade_cost = trade.price * trade.quantity

        if trade.action == "BUY":
            cash -= trade_cost
            if trade.ticker in holdings:
                # Update average price
                existing = holdings[trade.ticker]
                total_qty = existing["quantity"] + trade.quantity
                avg_price = (
                    existing["avg_price"] * existing["quantity"] + trade_cost
                ) / total_qty
                holdings[trade.ticker] = {"quantity": total_qty, "avg_price": avg_price}
            else:
                holdings[trade.ticker] = {"quantity": trade.quantity, "avg_price": trade.price}
        else:  # SELL
            cash += trade_cost
            if trade.ticker in holdings:
                holdings[trade.ticker]["quantity"] -= trade.quantity
                if holdings[trade.ticker]["quantity"] <= 0:
                    del holdings[trade.ticker]

        # Calculate total portfolio value at this point
        # Use purchase prices for holdings (we don't have historical market prices)
        holdings_value = sum(
            h["quantity"] * h["avg_price"] for h in holdings.values()
        )
        total_value = cash + holdings_value

        timestamps.append(trade.timestamp)
        values.append(total_value)

    # Add current value as final point
    try:
        current_holdings_value = 0.0
        for ticker, h in holdings.items():
            try:
                current_price = security_service.get_price(ticker)
                current_holdings_value += h["quantity"] * current_price
            except Exception:
                current_holdings_value += h["quantity"] * h["avg_price"]

        current_total = cash + current_holdings_value
        if current_total != values[-1]:
            from datetime import datetime
            timestamps.append(datetime.now())
            values.append(current_total)
    except Exception:
        pass

    # Remove the None placeholder if we have trades
    if timestamps[0] is None and len(timestamps) > 1:
        timestamps[0] = timestamps[1]

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

    # Color the area based on gain/loss
    final_value = values[-1] if values else config.initial_amount
    fill_color = "rgba(0, 212, 255, 0.1)" if final_value >= config.initial_amount else "rgba(255, 75, 75, 0.1)"

    fig.update_traces(fill="tozeroy", fillcolor=fill_color)

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
    security_service: SecurityService,
    portfolio_name: str,
) -> None:
    """Render the agent execution section."""
    st.subheader("Execute Trading Agent")

    is_overdue = portfolio_service.is_execution_overdue(config, state)

    if is_overdue:
        st.warning("This portfolio is overdue for execution!")

    if state.last_execution:
        st.caption(f"Last executed: {state.last_execution.strftime('%Y-%m-%d %H:%M')}")

    # Show agent mode badge
    agent_mode = getattr(config, "agent_mode", "simple")
    mode_colors = {"langgraph": "blue", "debate": "green", "simple": "gray"}
    mode_color = mode_colors.get(agent_mode, "gray")
    st.caption(f"Agent Mode: :{mode_color}[{agent_mode}]")

    if "recommendation" not in st.session_state:
        st.session_state.recommendation = None
    if "last_metrics" not in st.session_state:
        st.session_state.last_metrics = None
    if "debate_transcript" not in st.session_state:
        st.session_state.debate_transcript = None

    execute_button_type = "primary" if is_overdue else "secondary"

    if st.button("Run Agent", type=execute_button_type, key="run_agent"):
        try:
            # Choose agent based on config.agent_mode
            if agent_mode == "debate":
                debate_agent = DebateAgentService(security_service=security_service)

                # Create status container for progress
                with st.status("Running Debate Agent...", expanded=True) as status:
                    steps_completed = []

                    def on_progress(progress: StepProgress) -> None:
                        steps_completed.append(progress)
                        metrics_str = ""
                        if progress.metrics:
                            metrics_str = f" ({progress.metrics.duration_ms}ms, {progress.metrics.total_tokens} tokens)"
                        st.write(f"{progress.icon} **{progress.label}**{metrics_str}")
                        if progress.result_preview:
                            st.caption(progress.result_preview)

                    recommendation, metrics = debate_agent.execute(config, state, on_progress=on_progress)

                    # Store metrics and transcript in session state
                    st.session_state.last_metrics = metrics
                    st.session_state.debate_transcript = debate_agent.last_transcript

                    # Update final status
                    if recommendation and recommendation.trades:
                        status.update(
                            label=f"Debate completed - {len(recommendation.trades)} trade(s) | {metrics.total_duration_ms}ms | {metrics.total_tokens} tokens",
                            state="complete",
                            expanded=False,
                        )
                    else:
                        status.update(
                            label=f"Debate completed - No trades | {metrics.total_duration_ms}ms | {metrics.total_tokens} tokens",
                            state="complete",
                            expanded=False,
                        )

            elif agent_mode == "langgraph":
                langgraph_agent = LangGraphAgentService(security_service=security_service)

                # Create status container for progress
                with st.status("Running LangGraph Agent...", expanded=True) as status:
                    steps_completed = []

                    def on_progress(progress: StepProgress) -> None:
                        steps_completed.append(progress)
                        # Update status display with metrics
                        metrics_str = ""
                        if progress.metrics:
                            metrics_str = f" ({progress.metrics.duration_ms}ms, {progress.metrics.total_tokens} tokens)"
                        st.write(f"{progress.icon} **{progress.label}**{metrics_str}")
                        if progress.result_preview:
                            st.caption(progress.result_preview)

                    recommendation, metrics = langgraph_agent.execute(config, state, on_progress=on_progress)

                    # Store metrics in session state
                    st.session_state.last_metrics = metrics
                    st.session_state.debate_transcript = None

                    # Update final status with metrics summary
                    if recommendation and recommendation.trades:
                        status.update(
                            label=f"Agent completed - {len(recommendation.trades)} trade(s) | {metrics.total_duration_ms}ms | {metrics.total_tokens} tokens",
                            state="complete",
                            expanded=False,
                        )
                    else:
                        status.update(
                            label=f"Agent completed - No trades | {metrics.total_duration_ms}ms | {metrics.total_tokens} tokens",
                            state="complete",
                            expanded=False,
                        )
            else:
                with st.spinner("Agent is analyzing portfolio..."):
                    recommendation = agent_service.execute(config, state)
                st.session_state.last_metrics = None
                st.session_state.debate_transcript = None

            st.session_state.recommendation = recommendation
            st.rerun()
        except Exception as e:
            st.error(f"Agent execution failed: {e}")

    # Show last execution metrics if available
    if st.session_state.last_metrics:
        metrics = st.session_state.last_metrics
        with st.expander("Last Execution Metrics", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Duration", f"{metrics.total_duration_ms}ms")
            with col2:
                st.metric("Input Tokens", f"{metrics.total_input_tokens:,}")
            with col3:
                st.metric("Output Tokens", f"{metrics.total_output_tokens:,}")

            st.caption("Per-step breakdown:")
            for step_name, step_metrics in metrics.steps.items():
                st.text(f"  {step_name}: {step_metrics.duration_ms}ms, {step_metrics.input_tokens} in / {step_metrics.output_tokens} out")

    # Show debate transcript if available
    if st.session_state.debate_transcript:
        transcript = st.session_state.debate_transcript
        with st.expander("Debate Transcript", expanded=True):
            # Bull Case
            st.markdown("### Bull Case")
            st.markdown(transcript.bull_pitch)

            st.divider()

            # Bear Case
            st.markdown("### Bear Case")
            st.markdown(transcript.bear_pitch)

            st.divider()

            # Neutral Analysis
            st.markdown("### Neutral Analysis")
            st.markdown(transcript.neutral_pitch)

            # Debate Rounds
            if transcript.debate_history:
                st.divider()
                st.markdown("### Debate Rounds")
                for msg in transcript.debate_history:
                    agent_icon = {"bull": "🐂", "bear": "🐻", "neutral": "⚖️"}.get(msg["agent"], "💬")
                    st.markdown(f"**{agent_icon} {msg['agent'].upper()} (Round {msg['round']})**")
                    st.markdown(msg["message"])
                    st.write("")

            st.divider()

            # Moderator Verdict
            st.markdown("### Moderator Verdict")
            st.markdown(transcript.moderator_analysis)

    if st.session_state.recommendation:
        def on_accept(trades: list[TradeRecommendation]) -> None:
            nonlocal state
            try:
                for trade in trades:
                    state = portfolio_service.execute_trade(
                        state,
                        trade.ticker,
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
            security_service,
            available_cash=state.cash,
            holdings=state.holdings,
            on_accept=on_accept,
            on_retry=on_retry,
        )
