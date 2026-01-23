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
from fin_trade.components import render_large_status_badge, render_skeleton_table
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
        if on_back and st.button("Back to Overview", type="secondary"):
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
        render_large_status_badge(is_overdue)

    with st.expander("Portfolio Configuration"):
        st.write(f"**Strategy:** {config.strategy_prompt[:200]}...")
        st.write(f"**Initial Amount:** ${config.initial_amount:,.2f}")
        st.write(f"**Run Frequency:** {config.run_frequency}")
        st.write(f"**Trades per Run:** {config.trades_per_run}")
        st.write(f"**LLM:** {config.llm_provider} / {config.llm_model}")
        st.write(f"**Agent Mode:** {getattr(config, 'agent_mode', 'simple')}")


def _render_holdings(state: PortfolioState, security_service: SecurityService) -> None:
    """Render the holdings table."""
    import pandas as pd

    st.subheader("Current Holdings")

    if not state.holdings:
        st.info("No holdings. Execute the agent to start trading.")
        return

    # Show skeleton while loading prices
    table_placeholder = st.empty()
    with table_placeholder.container():
        render_skeleton_table(rows=len(state.holdings), cols=8)

    # Build holdings data for DataFrame
    holdings_data = []
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

        holdings_data.append({
            "Ticker": holding.ticker,
            "Name": holding.name,
            "Shares": holding.quantity,
            "Avg Price": holding.avg_price,
            "Current Price": current_price,
            "Value": current_value,
            "Gain/Loss": gain,
            "Gain %": gain_pct,
        })

    df = pd.DataFrame(holdings_data)

    # Replace skeleton with actual table
    with table_placeholder.container():
        st.dataframe(
            df,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Name": st.column_config.TextColumn("Name", width="medium"),
                "Shares": st.column_config.NumberColumn("Shares", format="%d"),
                "Avg Price": st.column_config.NumberColumn("Avg Price", format="$%.2f"),
                "Current Price": st.column_config.NumberColumn("Current", format="$%.2f"),
                "Value": st.column_config.NumberColumn("Value", format="$%.2f"),
                "Gain/Loss": st.column_config.NumberColumn("Gain/Loss", format="$%.2f"),
                "Gain %": st.column_config.NumberColumn("Gain %", format="%.1f%%"),
            },
            hide_index=True,
            use_container_width=True,
        )


def _render_performance_chart(
    config: PortfolioConfig,
    state: PortfolioState,
    security_service: SecurityService,
) -> None:
    """Render the portfolio performance chart with interactive features."""
    from datetime import datetime, timedelta

    st.subheader("Performance")

    if not state.trades:
        st.info("No trade history to display.")
        return

    # Build performance data with trade details
    performance_data = _calculate_performance_data(config, state, security_service)
    timestamps = performance_data["timestamps"]
    values = performance_data["values"]
    trade_points = performance_data["trade_points"]

    if not timestamps or not values:
        st.info("Insufficient data for chart.")
        return

    # Calculate key metrics
    metrics = _calculate_performance_metrics(config, values, timestamps)

    # Time period selector
    col1, col2 = st.columns([3, 1])
    with col2:
        time_range = st.selectbox(
            "Time Range",
            options=["1W", "1M", "3M", "YTD", "All"],
            index=4,
            key="perf_time_range",
        )

    # Filter data by time range
    filtered_timestamps, filtered_values, filtered_trades = _filter_by_time_range(
        timestamps, values, trade_points, time_range
    )

    # Display metrics row
    _render_performance_metrics(metrics, config.initial_amount)

    # Build the interactive chart
    fig = _build_performance_figure(
        filtered_timestamps,
        filtered_values,
        filtered_trades,
        config.initial_amount,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})


def _calculate_performance_data(
    config: PortfolioConfig,
    state: PortfolioState,
    security_service: SecurityService,
) -> dict:
    """Calculate portfolio value over time with trade markers."""
    from datetime import datetime

    timestamps = []
    values = []
    trade_points = []  # (timestamp, value, action, ticker, quantity)

    cash = config.initial_amount
    holdings: dict[str, dict] = {}

    for trade in state.trades:
        trade_cost = trade.price * trade.quantity

        if trade.action == "BUY":
            cash -= trade_cost
            if trade.ticker in holdings:
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

        # Calculate portfolio value at this point
        holdings_value = sum(h["quantity"] * h["avg_price"] for h in holdings.values())
        total_value = cash + holdings_value

        timestamps.append(trade.timestamp)
        values.append(total_value)
        trade_points.append({
            "timestamp": trade.timestamp,
            "value": total_value,
            "action": trade.action,
            "ticker": trade.ticker,
            "quantity": trade.quantity,
            "price": trade.price,
        })

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
        now = datetime.now()
        timestamps.append(now)
        values.append(current_total)
    except Exception:
        pass

    return {
        "timestamps": timestamps,
        "values": values,
        "trade_points": trade_points,
    }


def _calculate_performance_metrics(
    config: PortfolioConfig,
    values: list[float],
    timestamps: list,
) -> dict:
    """Calculate key performance metrics."""
    if not values:
        return {}

    initial = config.initial_amount
    current = values[-1]
    abs_gain = current - initial
    pct_gain = (abs_gain / initial) * 100 if initial > 0 else 0

    # Calculate max drawdown
    peak = initial
    max_drawdown = 0
    max_drawdown_pct = 0
    for v in values:
        if v > peak:
            peak = v
        drawdown = peak - v
        drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0
        if drawdown_pct > max_drawdown_pct:
            max_drawdown = drawdown
            max_drawdown_pct = drawdown_pct

    # Calculate high/low
    high = max(values) if values else initial
    low = min(values) if values else initial

    # Days active
    if len(timestamps) >= 2 and timestamps[0] and timestamps[-1]:
        days_active = (timestamps[-1] - timestamps[0]).days
    else:
        days_active = 0

    return {
        "current_value": current,
        "abs_gain": abs_gain,
        "pct_gain": pct_gain,
        "max_drawdown": max_drawdown,
        "max_drawdown_pct": max_drawdown_pct,
        "high": high,
        "low": low,
        "days_active": days_active,
    }


def _filter_by_time_range(
    timestamps: list,
    values: list[float],
    trade_points: list[dict],
    time_range: str,
) -> tuple[list, list[float], list[dict]]:
    """Filter data by selected time range."""
    from datetime import datetime, timedelta

    if time_range == "All" or not timestamps:
        return timestamps, values, trade_points

    now = datetime.now()
    if time_range == "1W":
        cutoff = now - timedelta(weeks=1)
    elif time_range == "1M":
        cutoff = now - timedelta(days=30)
    elif time_range == "3M":
        cutoff = now - timedelta(days=90)
    elif time_range == "YTD":
        cutoff = datetime(now.year, 1, 1)
    else:
        return timestamps, values, trade_points

    filtered_ts = []
    filtered_vals = []
    filtered_trades = []

    for i, ts in enumerate(timestamps):
        if ts and ts >= cutoff:
            filtered_ts.append(ts)
            filtered_vals.append(values[i])

    for tp in trade_points:
        if tp["timestamp"] and tp["timestamp"] >= cutoff:
            filtered_trades.append(tp)

    # If no data in range, return original
    if not filtered_ts:
        return timestamps, values, trade_points

    return filtered_ts, filtered_vals, filtered_trades


def _render_performance_metrics(metrics: dict, initial_amount: float) -> None:
    """Render performance metrics row."""
    if not metrics:
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        gain_delta = f"{metrics['pct_gain']:+.1f}%"
        st.metric(
            "Total Return",
            f"${metrics['abs_gain']:+,.2f}",
            delta=gain_delta,
        )

    with col2:
        st.metric(
            "Max Drawdown",
            f"-${metrics['max_drawdown']:,.2f}",
            delta=f"-{metrics['max_drawdown_pct']:.1f}%",
            delta_color="inverse",
        )

    with col3:
        st.metric("Period High", f"${metrics['high']:,.2f}")

    with col4:
        st.metric("Period Low", f"${metrics['low']:,.2f}")


def _build_performance_figure(
    timestamps: list,
    values: list[float],
    trade_points: list[dict],
    initial_amount: float,
) -> go.Figure:
    """Build the interactive Plotly figure."""
    fig = go.Figure()

    # Create hover text with detailed info
    hover_texts = []
    for i, (ts, val) in enumerate(zip(timestamps, values)):
        gain = val - initial_amount
        gain_pct = (gain / initial_amount) * 100 if initial_amount > 0 else 0
        date_str = ts.strftime("%Y-%m-%d %H:%M") if ts else "Start"
        hover_texts.append(
            f"<b>{date_str}</b><br>"
            f"Value: ${val:,.2f}<br>"
            f"Gain: ${gain:+,.2f} ({gain_pct:+.1f}%)"
        )

    # Main value line
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=values,
            mode="lines",
            name="Portfolio Value",
            line=dict(color="#008F11", width=2),
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_texts,
        )
    )

    # Determine fill color based on final value
    final_value = values[-1] if values else initial_amount
    fill_color = "rgba(0, 143, 17, 0.15)" if final_value >= initial_amount else "rgba(255, 0, 0, 0.15)"

    fig.update_traces(fill="tozeroy", fillcolor=fill_color, selector=dict(name="Portfolio Value"))

    # Add trade markers
    if trade_points:
        buy_trades = [tp for tp in trade_points if tp["action"] == "BUY"]
        sell_trades = [tp for tp in trade_points if tp["action"] == "SELL"]

        if buy_trades:
            buy_hover = [
                f"<b>BUY {tp['ticker']}</b><br>"
                f"{tp['quantity']} shares @ ${tp['price']:.2f}<br>"
                f"Portfolio: ${tp['value']:,.2f}"
                for tp in buy_trades
            ]
            fig.add_trace(
                go.Scatter(
                    x=[tp["timestamp"] for tp in buy_trades],
                    y=[tp["value"] for tp in buy_trades],
                    mode="markers",
                    name="Buy",
                    marker=dict(
                        symbol="triangle-up",
                        size=12,
                        color="#008F11",
                        line=dict(color="#004d00", width=1),
                    ),
                    hovertemplate="%{customdata}<extra></extra>",
                    customdata=buy_hover,
                )
            )

        if sell_trades:
            sell_hover = [
                f"<b>SELL {tp['ticker']}</b><br>"
                f"{tp['quantity']} shares @ ${tp['price']:.2f}<br>"
                f"Portfolio: ${tp['value']:,.2f}"
                for tp in sell_trades
            ]
            fig.add_trace(
                go.Scatter(
                    x=[tp["timestamp"] for tp in sell_trades],
                    y=[tp["value"] for tp in sell_trades],
                    mode="markers",
                    name="Sell",
                    marker=dict(
                        symbol="triangle-down",
                        size=12,
                        color="#ff0000",
                        line=dict(color="#990000", width=1),
                    ),
                    hovertemplate="%{customdata}<extra></extra>",
                    customdata=sell_hover,
                )
            )

    # Initial investment line
    fig.add_hline(
        y=initial_amount,
        line_dash="dash",
        line_color="#666666",
        annotation_text=f"Initial: ${initial_amount:,.0f}",
        annotation_font_color="#000000",
        annotation_position="bottom right",
    )

    # Layout
    fig.update_layout(
        xaxis=dict(
            title="Date",
            title_font=dict(color="#000000", family="Segoe UI, Roboto, sans-serif"),
            tickfont=dict(color="#000000", family="Segoe UI, Roboto, sans-serif"),
            gridcolor="rgba(0, 143, 17, 0.2)",
            showgrid=True,
            rangeslider=dict(visible=True, thickness=0.05),
            rangeselector=dict(
                buttons=[
                    dict(count=7, label="1W", step="day", stepmode="backward"),
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(step="all", label="All"),
                ],
                bgcolor="rgba(0, 143, 17, 0.1)",
                activecolor="rgba(0, 143, 17, 0.3)",
                font=dict(color="#000000"),
            ),
        ),
        yaxis=dict(
            title="Value ($)",
            title_font=dict(color="#000000", family="Segoe UI, Roboto, sans-serif"),
            tickfont=dict(color="#000000", family="Segoe UI, Roboto, sans-serif"),
            gridcolor="rgba(0, 143, 17, 0.2)",
            tickformat="$,.0f",
        ),
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, Roboto, sans-serif", color="#000000"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#000000"),
        ),
        hovermode="x unified",
        margin=dict(t=50, b=80),
    )

    return fig


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
    if "user_context" not in st.session_state:
        st.session_state.user_context = ""

    # User feedback input
    with st.expander("Provide Guidance (Optional)", expanded=False):
        st.caption("Give the agent specific instructions or context to consider during analysis.")
        user_context = st.text_area(
            "Your guidance:",
            value=st.session_state.user_context,
            placeholder="e.g., 'Focus on tech stocks with strong earnings', 'Avoid energy sector', 'Consider selling positions with >20% gains'...",
            height=100,
            key="user_context_input",
        )
        st.session_state.user_context = user_context

    # Use primary button for execution, regardless of overdue status
    execute_button_type = "primary"

    # Get user context (empty string becomes None)
    user_context_value = st.session_state.user_context.strip() or None

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

                    recommendation, metrics = debate_agent.execute(config, state, on_progress=on_progress, user_context=user_context_value)

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

                    recommendation, metrics = langgraph_agent.execute(config, state, on_progress=on_progress, user_context=user_context_value)

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
