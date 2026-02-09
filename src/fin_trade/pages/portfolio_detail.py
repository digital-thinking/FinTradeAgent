"""Portfolio detail page."""

from collections.abc import Callable
from datetime import datetime

import streamlit as st
import plotly.graph_objects as go

from fin_trade.models import AssetClass, PortfolioConfig, PortfolioState, TradeRecommendation
from fin_trade.services import PortfolioService, AgentService, SecurityService
from fin_trade.services.execution_log import ExecutionLogService
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


def get_unit_label(asset_class: AssetClass) -> str:
    """Get the quantity unit label for a portfolio asset class."""
    return "units" if asset_class == AssetClass.CRYPTO else "shares"


def format_quantity(quantity: float, asset_class: AssetClass) -> str:
    """Format quantities for UI display."""
    if asset_class == AssetClass.CRYPTO:
        return f"{quantity:.8f}".rstrip("0").rstrip(".")
    return str(int(quantity))


def render_portfolio_detail_page(
    portfolio_name: str,
    portfolio_service: PortfolioService,
    agent_service: AgentService,
    security_service: SecurityService,
    on_back: Callable | None = None,
    on_navigate_to_portfolio: Callable[[str], None] | None = None,
) -> None:
    """Render the portfolio detail page."""
    try:
        config, state = portfolio_service.load_portfolio(portfolio_name)
    except Exception as e:
        st.error(f"Failed to load portfolio: {e}")
        if on_back and st.button("Back to Overview", type="secondary"):
            on_back()
        return

    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("← Back to Overview", type="secondary"):
            if on_back:
                on_back()

    with col2:
        st.title(config.name)

    with col3:
        _render_portfolio_actions(
            portfolio_name, config, state, portfolio_service, on_back, on_navigate_to_portfolio
        )

    _render_summary(config, state, portfolio_service, security_service)

    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Holdings", "Performance", "Execute Agent", "Trade Log", "Execution History"]
    )

    with tab1:
        _render_holdings(config, state, security_service)

    with tab2:
        _render_performance_chart(config, state, security_service)

    with tab3:
        _render_agent_execution(
            config, state, portfolio_service, agent_service, security_service, portfolio_name
        )

    with tab4:
        render_trade_history(state.trades, security_service, config.asset_class)

    with tab5:
        _render_execution_history(
            portfolio_name,
        )

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

    # Calculate holdings value
    holdings_value = 0.0
    for holding in state.holdings:
        try:
            price = security_service.get_price(holding.ticker)
            holdings_value += price * holding.quantity
        except Exception:
            holdings_value += holding.avg_price * holding.quantity

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Value", f"${total_value:,.2f}")

    with col2:
        gain_delta = f"{pct_gain:+.1f}%"
        st.metric("Gain/Loss", f"${abs_gain:,.2f}", delta=gain_delta)

    with col3:
        holdings_label = "Crypto Holdings" if config.asset_class == AssetClass.CRYPTO else "Stock Holdings"
        st.metric(holdings_label, f"${holdings_value:,.2f}")

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


def _render_portfolio_actions(
    portfolio_name: str,
    config: PortfolioConfig,
    state: PortfolioState,
    portfolio_service: PortfolioService,
    on_back: Callable | None,
    on_navigate_to_portfolio: Callable[[str], None] | None,
) -> None:
    """Render Clone and Reset action buttons."""
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Clone", key="clone_btn", help="Create a copy of this portfolio"):
            st.session_state.show_clone_dialog = True

    with col2:
        if st.button("Reset", key="reset_btn", type="secondary", help="Reset to initial state"):
            st.session_state.show_reset_dialog = True

    # Clone Dialog
    if st.session_state.get("show_clone_dialog", False):
        _render_clone_dialog(portfolio_name, portfolio_service, on_navigate_to_portfolio)

    # Reset Dialog
    if st.session_state.get("show_reset_dialog", False):
        _render_reset_dialog(portfolio_name, config, state, portfolio_service)


@st.dialog("Clone Portfolio")
def _render_clone_dialog(
    portfolio_name: str,
    portfolio_service: PortfolioService,
    on_navigate_to_portfolio: Callable[[str], None] | None,
) -> None:
    """Render the clone portfolio dialog."""
    new_name = st.text_input(
        "New Portfolio Name",
        value=f"{portfolio_name}_copy",
        help="Enter a unique name for the cloned portfolio",
    )

    include_state = st.checkbox(
        "Include current state (holdings & trades)",
        value=False,
        help="If checked, the clone will have the same holdings and trade history",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clone", type="primary", key="confirm_clone"):
            try:
                portfolio_service.clone_portfolio(
                    portfolio_name, new_name.strip(), include_state=include_state
                )
                st.success(f"Portfolio '{new_name}' created successfully!")
                st.session_state.show_clone_dialog = False

                # Navigate to new portfolio
                if on_navigate_to_portfolio:
                    on_navigate_to_portfolio(new_name.strip())
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except FileNotFoundError as e:
                st.error(str(e))

    with col2:
        if st.button("Cancel", key="cancel_clone"):
            st.session_state.show_clone_dialog = False
            st.rerun()


@st.dialog("Reset Portfolio")
def _render_reset_dialog(
    portfolio_name: str,
    config: PortfolioConfig,
    state: PortfolioState,
    portfolio_service: PortfolioService,
) -> None:
    """Render the reset portfolio dialog with confirmation."""
    st.warning("This action will reset your portfolio to its initial state.")

    # Show what will be lost
    st.markdown("**What will be lost:**")
    current_value = portfolio_service.calculate_value(state)
    st.markdown(f"- **{len(state.trades)}** trades")
    st.markdown(f"- **{len(state.holdings)}** holdings")
    st.markdown(f"- **${current_value:,.2f}** current value")

    st.divider()

    archive = st.checkbox(
        "Archive current state before reset",
        value=True,
        help="Save a backup of the current state in data/state/archive/",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reset Portfolio", type="primary", key="confirm_reset"):
            try:
                portfolio_service.reset_portfolio(portfolio_name, archive=archive)
                st.success("Portfolio reset successfully!")
                st.session_state.show_reset_dialog = False
                st.rerun()
            except FileNotFoundError as e:
                st.error(str(e))

    with col2:
        if st.button("Cancel", key="cancel_reset"):
            st.session_state.show_reset_dialog = False
            st.rerun()


def _render_holdings(
    config: PortfolioConfig,
    state: PortfolioState,
    security_service: SecurityService,
) -> None:
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
            "Quantity": format_quantity(holding.quantity, config.asset_class),
            "Avg Price": holding.avg_price,
            "Current Price": current_price,
            "Value": current_value,
            "Gain/Loss": gain,
            "Gain %": gain_pct,
            "Stop Loss": holding.stop_loss_price,
            "Take Profit": holding.take_profit_price,
        })

    unit_label = get_unit_label(config.asset_class).capitalize()

    df = pd.DataFrame(holdings_data)

    # Replace skeleton with actual table
    with table_placeholder.container():
        st.dataframe(
            df,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Name": st.column_config.TextColumn("Name", width="medium"),
                "Quantity": st.column_config.TextColumn(unit_label, width="small"),
                "Avg Price": st.column_config.NumberColumn("Avg Price", format="$%.2f"),
                "Current Price": st.column_config.NumberColumn("Current", format="$%.2f"),
                "Value": st.column_config.NumberColumn("Value", format="$%.2f"),
                "Gain/Loss": st.column_config.NumberColumn("Gain/Loss", format="$%.2f"),
                "Gain %": st.column_config.NumberColumn("Gain %", format="%.1f%%"),
                "Stop Loss": st.column_config.NumberColumn("Stop Loss", format="$%.2f"),
                "Take Profit": st.column_config.NumberColumn("Take Profit", format="$%.2f"),
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
    from fin_trade.services import StockDataService

    st.subheader("Performance")

    if not state.trades:
        st.info("No trade history to display.")
        return

    # Build performance data with trade details
    performance_data = _calculate_performance_data(config, state, security_service)
    timestamps = performance_data["timestamps"]
    values = performance_data["values"]
    cash_values = performance_data["cash_values"]
    holdings_values = performance_data["holdings_values"]
    trade_points = performance_data["trade_points"]

    if not timestamps or not values:
        st.info("Insufficient data for chart.")
        return

    # Calculate key metrics
    metrics = _calculate_performance_metrics(config, state, values, timestamps)

    # Time period selector and benchmark toggle
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        time_range = st.selectbox(
            "Time Range",
            options=["1W", "1M", "3M", "YTD", "All"],
            index=4,
            key="perf_time_range",
        )
    with col3:
        benchmark_symbol = "BTC-USD" if config.asset_class == AssetClass.CRYPTO else "SPY"
        benchmark_label = "BTC" if config.asset_class == AssetClass.CRYPTO else "S&P 500"
        show_benchmark = st.checkbox(f"Show {benchmark_label}", value=False, key="show_benchmark")

    # Filter data by time range
    filtered_timestamps, filtered_values, filtered_cash, filtered_holdings, filtered_trades = _filter_by_time_range(
        timestamps, values, cash_values, holdings_values, trade_points, time_range
    )

    # Use actual initial investment if recorded, otherwise fall back to config
    initial_investment = state.initial_investment or config.initial_amount

    # Display metrics row
    _render_performance_metrics(metrics, initial_investment)

    # Get benchmark data if requested
    benchmark_data = None
    if show_benchmark and filtered_timestamps:
        try:
            stock_data_service = StockDataService()
            start_date = filtered_timestamps[0]
            end_date = filtered_timestamps[-1] if len(filtered_timestamps) > 1 else datetime.now()
            benchmark_df = stock_data_service.get_benchmark_performance(
                symbol=benchmark_symbol,
                start_date=start_date,
                end_date=end_date,
            )
            if not benchmark_df.empty:
                # Normalize benchmark to start at same value as portfolio
                start_portfolio_value = filtered_values[0]
                benchmark_data = {
                    "dates": benchmark_df["date"].tolist(),
                    "values": (benchmark_df["cumulative_return"] / 100 + 1) * start_portfolio_value,
                    "label": benchmark_label,
                }
        except Exception:
            pass  # Silently skip benchmark if unavailable

    # Load notes for chart annotations
    log_service = ExecutionLogService()
    notes = log_service.get_notes(config.name)

    # Build the interactive chart
    fig = _build_performance_figure(
        filtered_timestamps,
        filtered_values,
        filtered_cash,
        filtered_holdings,
        filtered_trades,
        initial_investment,
        asset_class=config.asset_class,
        benchmark_data=benchmark_data,
        notes=_map_notes_to_points(notes, filtered_timestamps, filtered_values),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})


def _calculate_performance_data(
    config: PortfolioConfig,
    state: PortfolioState,
    security_service: SecurityService,
) -> dict:
    """Calculate portfolio value over time with trade markers and stacked data."""
    from datetime import datetime

    timestamps = []
    values = []
    cash_values = []  # Track cash over time
    holdings_values = []  # Track holdings value over time
    trade_points = []  # (timestamp, value, action, ticker, quantity)

    # Use actual initial investment if recorded, otherwise fall back to config
    cash = state.initial_investment or config.initial_amount
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
        cash_values.append(cash)
        holdings_values.append(holdings_value)
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
        cash_values.append(cash)
        holdings_values.append(current_holdings_value)
    except Exception:
        pass

    return {
        "timestamps": timestamps,
        "values": values,
        "cash_values": cash_values,
        "holdings_values": holdings_values,
        "trade_points": trade_points,
    }


def _calculate_performance_metrics(
    config: PortfolioConfig,
    state: PortfolioState,
    values: list[float],
    timestamps: list,
) -> dict:
    """Calculate key performance metrics."""
    if not values:
        return {}

    # Use actual initial investment if recorded, otherwise fall back to config
    initial = state.initial_investment or config.initial_amount
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
    cash_values: list[float],
    holdings_values: list[float],
    trade_points: list[dict],
    time_range: str,
) -> tuple[list, list[float], list[float], list[float], list[dict]]:
    """Filter data by selected time range."""
    from datetime import datetime, timedelta

    if time_range == "All" or not timestamps:
        return timestamps, values, cash_values, holdings_values, trade_points

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
        return timestamps, values, cash_values, holdings_values, trade_points

    filtered_ts = []
    filtered_vals = []
    filtered_cash = []
    filtered_holdings = []
    filtered_trades = []

    for i, ts in enumerate(timestamps):
        if ts and ts >= cutoff:
            filtered_ts.append(ts)
            filtered_vals.append(values[i])
            filtered_cash.append(cash_values[i])
            filtered_holdings.append(holdings_values[i])

    for tp in trade_points:
        if tp["timestamp"] and tp["timestamp"] >= cutoff:
            filtered_trades.append(tp)

    # If no data in range, return original
    if not filtered_ts:
        return timestamps, values, cash_values, holdings_values, trade_points

    return filtered_ts, filtered_vals, filtered_cash, filtered_holdings, filtered_trades


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
    cash_values: list[float],
    holdings_values: list[float],
    trade_points: list[dict],
    initial_amount: float,
    asset_class: AssetClass = AssetClass.STOCKS,
    benchmark_data: dict | None = None,
    notes: list[dict] | None = None,
) -> go.Figure:
    """Build the interactive stacked area Plotly figure."""
    fig = go.Figure()
    unit_label = get_unit_label(asset_class)

    # Create hover text for cash
    cash_hover = [
        f"<b>Cash</b><br>${c:,.2f}"
        for c in cash_values
    ]

    # Create hover text for holdings
    holdings_hover = [
        f"<b>Holdings</b><br>${h:,.2f}"
        for h in holdings_values
    ]

    # Stacked area chart - Cash (bottom layer)
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=cash_values,
            mode="lines",
            name="Cash",
            line=dict(color="#4CAF50", width=0),
            fill="tozeroy",
            fillcolor="rgba(76, 175, 80, 0.6)",
            hovertemplate="%{customdata}<extra></extra>",
            customdata=cash_hover,
            stackgroup="portfolio",
        )
    )

    # Stacked area chart - Holdings (top layer)
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=holdings_values,
            mode="lines",
            name="Holdings",
            line=dict(color="#2196F3", width=0),
            fill="tonexty",
            fillcolor="rgba(33, 150, 243, 0.6)",
            hovertemplate="%{customdata}<extra></extra>",
            customdata=holdings_hover,
            stackgroup="portfolio",
        )
    )

    # Add trade markers on top of the stacked chart
    if trade_points:
        buy_trades = [tp for tp in trade_points if tp["action"] == "BUY"]
        sell_trades = [tp for tp in trade_points if tp["action"] == "SELL"]

        if buy_trades:
            buy_hover = [
                f"<b>BUY {tp['ticker']}</b><br>"
                f"{format_quantity(tp['quantity'], asset_class)} {unit_label} @ ${tp['price']:.2f}<br>"
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
                        color="#00ff41",
                        line=dict(color="#004d00", width=1),
                    ),
                    hovertemplate="%{customdata}<extra></extra>",
                    customdata=buy_hover,
                )
            )

        if sell_trades:
            sell_hover = [
                f"<b>SELL {tp['ticker']}</b><br>"
                f"{format_quantity(tp['quantity'], asset_class)} {unit_label} @ ${tp['price']:.2f}<br>"
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

    # Benchmark overlay (S&P 500)
    if benchmark_data:
        benchmark_label = benchmark_data.get("label", "Benchmark")
        benchmark_hover = [
            f"<b>{benchmark_label}</b><br>${v:,.2f}"
            for v in benchmark_data["values"]
        ]
        fig.add_trace(
            go.Scatter(
                x=benchmark_data["dates"],
                y=benchmark_data["values"],
                mode="lines",
                name=benchmark_label,
                line=dict(color="#FF9800", width=2, dash="dot"),
                hovertemplate="%{customdata}<extra></extra>",
                customdata=benchmark_hover,
            )
        )

    # Note markers
    if notes:
        note_hover = []
        for note in notes:
            tags = ", ".join(note.get("tags", [])) if note.get("tags") else "No tags"
            preview = note.get("note_text", "")
            if len(preview) > 140:
                preview = preview[:140] + "..."
            note_hover.append(
                f"<b>Note</b><br>{preview}<br><i>{tags}</i>"
            )
        fig.add_trace(
            go.Scatter(
                x=[note["timestamp"] for note in notes],
                y=[note["value"] for note in notes],
                mode="markers",
                name="Notes",
                marker=dict(
                    symbol="circle",
                    size=10,
                    color="#9C27B0",
                    line=dict(color="#4A148C", width=1),
                ),
                hovertemplate="%{customdata}<extra></extra>",
                customdata=note_hover,
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


def _map_notes_to_points(
    notes: list[dict],
    timestamps: list,
    values: list[float],
) -> list[dict]:
    """Map notes to chart points based on closest prior timestamp."""
    if not notes or not timestamps:
        return []

    note_points = []
    ts_list = list(timestamps)

    for note in notes:
        note_date = note.get("note_date")
        if not note_date:
            continue

        idx = None
        for i in range(len(ts_list) - 1, -1, -1):
            if ts_list[i].date() <= note_date:
                idx = i
                break

        if idx is None:
            continue

        note_points.append({
            "timestamp": ts_list[idx],
            "value": values[idx],
            "note_text": note.get("note_text", ""),
            "tags": note.get("tags", []),
            "id": note.get("id"),
        })

    return note_points


def _render_execution_history(
    portfolio_name: str,
) -> None:
    """Render execution history with full context and notes."""
    import json
    import pandas as pd

    st.subheader("Execution History")

    log_service = ExecutionLogService()
    logs = log_service.get_logs(portfolio_name=portfolio_name, limit=50)

    if not logs:
        st.info("No execution logs yet. Run the agent to generate logs.")
        return

    for log in logs:
        recommendations = []
        if log.recommendations_json:
            recommendations = json.loads(log.recommendations_json)

        executed = set()
        if log.executed_trades_json:
            executed = set(json.loads(log.executed_trades_json))

        rejected = set()
        if log.rejected_trades_json:
            rejected = set(json.loads(log.rejected_trades_json))

        applied_count = len(executed)
        rejected_count = len(rejected)
        pending_count = len(recommendations) - applied_count - rejected_count

        outcomes = log_service.get_recommendation_outcomes(log.id)
        outcome_score = None
        if outcomes:
            outcome_values = [o["hypothetical_pl"] for o in outcomes if o["hypothetical_pl"] is not None]
            if outcome_values:
                outcome_score = sum(outcome_values)

        outcome_label = "Outcome: N/A"
        if outcome_score is not None:
            outcome_label = f"Outcome: {'+' if outcome_score >= 0 else ''}{outcome_score:,.2f}"

        expander_title = (
            f"{log.timestamp.strftime('%Y-%m-%d %H:%M')} — {log.model} — "
            f"{len(recommendations)} recs | {applied_count} applied / {rejected_count} rejected / "
            f"{pending_count} pending — {outcome_label}"
        )

        with st.expander(expander_title, expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Duration", f"{log.duration_ms}ms")
            with col2:
                st.metric("Total Tokens", f"{log.total_tokens:,}")
            with col3:
                st.metric("Agent Mode", log.agent_mode)

            if log.error_message:
                st.error(log.error_message)

            # Recommendations with outcomes
            st.markdown("### Recommendations & Outcomes")
            if not outcomes:
                st.caption("No recommendations available.")
            else:
                rows = []
                for outcome in outcomes:
                    rows.append({
                        "Status": outcome["status"].capitalize(),
                        "Ticker": outcome["ticker"],
                        "Action": outcome["action"],
                        "Qty": outcome["recommended_quantity"],
                        "Rec Price": outcome["recommended_price"],
                        "Current/Exit": outcome["exit_price"] or outcome["current_price"],
                        "Hypo P/L": outcome["hypothetical_pl"],
                        "Actual P/L": outcome["actual_pl"],
                    })

                df = pd.DataFrame(rows)
                st.dataframe(
                    df,
                    column_config={
                        "Rec Price": st.column_config.NumberColumn("Rec Price", format="$%.2f"),
                        "Current/Exit": st.column_config.NumberColumn("Current/Exit", format="$%.2f"),
                        "Hypo P/L": st.column_config.NumberColumn("Hypo P/L", format="$%.2f"),
                        "Actual P/L": st.column_config.NumberColumn("Actual P/L", format="$%.2f"),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

            # Full context from markdown logs
            context = log_service.get_execution_with_context(log.id).get("log_context", {})

            if context.get("analysis"):
                st.markdown("### Full Agent Reasoning")
                st.markdown(context["analysis"])
            elif context.get("overall_reasoning"):
                st.markdown("### Full Agent Reasoning")
                st.markdown(context["overall_reasoning"])

            if context.get("research"):
                with st.expander("Research", expanded=False):
                    st.markdown(context["research"])

            if context.get("debate") or context.get("bull_case") or context.get("bear_case"):
                with st.expander("Debate Transcript", expanded=False):
                    if context.get("bull_case"):
                        st.markdown("**Bull Case**")
                        st.markdown(context["bull_case"])
                    if context.get("bear_case"):
                        st.markdown("**Bear Case**")
                        st.markdown(context["bear_case"])
                    if context.get("neutral_analysis"):
                        st.markdown("**Neutral Analysis**")
                        st.markdown(context["neutral_analysis"])
                    if context.get("debate"):
                        st.markdown("**Debate Rounds**")
                        st.markdown(context["debate"])
                    if context.get("moderator_verdict"):
                        st.markdown("**Moderator Verdict**")
                        st.markdown(context["moderator_verdict"])

            if context.get("prompt"):
                with st.expander("Full Prompt", expanded=False):
                    st.markdown(context["prompt"])

            # Add Note UI
            st.markdown("### Add Note")
            note_key = f"note_{log.id}"
            note_text = st.text_area(
                "Note",
                key=f"{note_key}_text",
                placeholder="Add your observation about this execution...",
                height=120,
            )
            common_tags = ["Earnings", "Fed Decision", "Market Correction", "Strategy Tweak"]
            selected_common = st.multiselect(
                "Quick Tags",
                options=common_tags,
                key=f"{note_key}_common",
            )
            tags_input = st.text_input(
                "Tags (comma-separated)",
                key=f"{note_key}_tags",
            )
            if st.button("Add Note", key=f"{note_key}_add"):
                tags = []
                if tags_input:
                    tags.extend([t.strip() for t in tags_input.split(",") if t.strip()])
                tags.extend(selected_common)
                tags = list(dict.fromkeys(tags))
                try:
                    log_service.add_note(
                        portfolio_name=portfolio_name,
                        note_text=note_text,
                        execution_id=log.id,
                        tags=tags,
                    )
                    st.success("Note added.")
                except Exception as e:
                    st.error(f"Failed to add note: {e}")

    st.divider()
    _render_notes_panel(portfolio_name, log_service)


def _render_notes_panel(
    portfolio_name: str,
    log_service: ExecutionLogService,
) -> None:
    """Render notes panel with filtering and search."""
    st.subheader("Notes")

    notes = log_service.get_notes(portfolio_name)
    if not notes:
        st.info("No notes yet. Add notes from the execution history.")
        return

    all_tags = sorted({tag for note in notes for tag in note.get("tags", [])})
    tag_filter = st.selectbox(
        "Filter by tag",
        options=["All"] + all_tags,
        index=0,
    )
    search_query = st.text_input("Search notes")

    filtered = []
    for note in notes:
        if tag_filter != "All" and tag_filter not in note.get("tags", []):
            continue
        if search_query and search_query.lower() not in note["note_text"].lower():
            continue
        filtered.append(note)

    for note in filtered:
        tags_label = ", ".join(note.get("tags", [])) if note.get("tags") else "No tags"
        header = f"{note['note_date'].strftime('%Y-%m-%d')} — {tags_label}"
        with st.expander(header, expanded=False):
            st.markdown(note["note_text"])


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

    if config.llm_provider == "ollama":
        st.warning(
            "Ollama does not provide built-in web search. "
            "Research uses local holdings and cached price context only."
        )

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

            # Record execution time regardless of trades
            state.last_execution = datetime.now()
            portfolio_service.save_state(portfolio_name, state)
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
                # Sort trades: SELL first, then BUY
                # This ensures cash from sells is available for buys
                sorted_trades = sorted(trades, key=lambda t: 0 if t.action == "SELL" else 1)

                for trade in sorted_trades:
                    state = portfolio_service.execute_trade(
                        state,
                        trade.ticker,
                        trade.action,
                        trade.quantity,
                        trade.reasoning,
                        stop_loss_price=trade.stop_loss_price,
                        take_profit_price=trade.take_profit_price,
                        asset_class=config.asset_class,
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
            asset_class=config.asset_class,
            on_accept=on_accept,
            on_retry=on_retry,
        )
