"""Portfolio tile component for the overview page."""

import streamlit as st
import plotly.graph_objects as go

from fin_trade.cache import get_portfolio_metrics
from fin_trade.components.status_badge import render_status_badge
from fin_trade.models import PortfolioConfig, PortfolioState
from fin_trade.services import PortfolioService


def render_portfolio_tile(
    config: PortfolioConfig,
    state: PortfolioState,
    portfolio_service: PortfolioService,
    portfolio_name: str | None = None,
) -> bool:
    """Render a portfolio tile and return True if clicked."""
    # Use cached metrics if portfolio_name provided, otherwise calculate directly
    if portfolio_name:
        metrics = get_portfolio_metrics(portfolio_service, portfolio_name)
        value = metrics["value"]
        abs_gain = metrics["absolute_gain"]
        pct_gain = metrics["percentage_gain"]
    else:
        value = portfolio_service.calculate_value(state)
        abs_gain, pct_gain = portfolio_service.calculate_gain(config, state)
    is_overdue = portfolio_service.is_execution_overdue(config, state)
    num_holdings = len(state.holdings)

    # Matrix colors
    gain_color = "#00ff41" if abs_gain >= 0 else "#ff0000"

    with st.container(border=True):
        # Header with name and status badge
        col1, col2 = st.columns([4, 1])

        with col1:
            st.subheader(config.name)

        with col2:
            render_status_badge(is_overdue)

        # Info row
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.caption(f"📊 {num_holdings} holdings • {config.run_frequency.capitalize()}")
        with info_col2:
            if state.last_execution:
                last_exec = state.last_execution.strftime("%b %d, %H:%M")
                st.caption(f"🕐 {last_exec}")
            else:
                st.caption("🕐 Never run")

        # Value metrics
        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
            st.metric("Portfolio Value", f"${value:,.2f}")
        with metric_col2:
            st.metric("Return", f"${abs_gain:,.2f}", delta=f"{pct_gain:+.1f}%")

        # Mini chart
        fig = _create_mini_chart(config, state, gain_color)
        if fig:
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"chart_{config.name}",
            )

        clicked = st.button(
            "View Details →",
            key=f"tile_{config.name}",
            use_container_width=True,
            type="secondary",
        )

        return clicked


def _create_mini_chart(
    config: PortfolioConfig, state: PortfolioState, color: str
) -> go.Figure | None:
    """Create a mini stacked sparkline chart of portfolio performance."""
    if not state.trades:
        return None

    # Calculate portfolio value at each trade point (same logic as detail page)
    cash_values = [config.initial_amount]
    holdings_values = [0.0]
    cash = config.initial_amount
    holdings: dict[str, dict] = {}

    for trade in state.trades[-20:]:  # Last 20 trades for mini chart
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

        holdings_value = sum(h["quantity"] * h["avg_price"] for h in holdings.values())
        cash_values.append(cash)
        holdings_values.append(holdings_value)

    if len(cash_values) < 2:
        return None

    fig = go.Figure()

    # Stacked area - Cash (bottom layer)
    fig.add_trace(
        go.Scatter(
            x=list(range(len(cash_values))),
            y=cash_values,
            mode="lines",
            line=dict(color="#4CAF50", width=0),
            fill="tozeroy",
            fillcolor="rgba(76, 175, 80, 0.6)",
            stackgroup="portfolio",
            showlegend=False,
        )
    )

    # Stacked area - Holdings (top layer)
    fig.add_trace(
        go.Scatter(
            x=list(range(len(holdings_values))),
            y=holdings_values,
            mode="lines",
            line=dict(color="#2196F3", width=0),
            fill="tonexty",
            fillcolor="rgba(33, 150, 243, 0.6)",
            stackgroup="portfolio",
            showlegend=False,
        )
    )

    fig.update_layout(
        height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
