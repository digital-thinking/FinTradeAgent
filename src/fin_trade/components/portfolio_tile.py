"""Portfolio tile component for the overview page."""

import streamlit as st
import plotly.graph_objects as go

from fin_trade.models import PortfolioConfig, PortfolioState
from fin_trade.services import PortfolioService


def render_portfolio_tile(
    config: PortfolioConfig,
    state: PortfolioState,
    portfolio_service: PortfolioService,
) -> bool:
    """Render a portfolio tile and return True if clicked."""
    value = portfolio_service.calculate_value(state)
    abs_gain, pct_gain = portfolio_service.calculate_gain(config, state)
    is_overdue = portfolio_service.is_execution_overdue(config, state)
    num_holdings = len(state.holdings)

    gain_color = "green" if abs_gain >= 0 else "red"
    border_color = "#ff4b4b" if is_overdue else "#e0e0e0"

    with st.container():
        tile_style = f"""
        <style>
        .portfolio-tile {{
            border: 2px solid {border_color};
            border-radius: 10px;
            padding: 15px;
            margin: 5px 0;
            background: #1e1e1e;
        }}
        </style>
        """
        st.markdown(tile_style, unsafe_allow_html=True)

        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader(config.name)
            st.caption(f"{num_holdings} holdings | {config.run_frequency}")

            if state.last_execution:
                last_exec = state.last_execution.strftime("%Y-%m-%d %H:%M")
                if is_overdue:
                    st.caption(f":red[Last run: {last_exec} (OVERDUE)]")
                else:
                    st.caption(f"Last run: {last_exec}")
            else:
                st.caption(":red[Never executed]")

        with col2:
            st.metric(
                label="Value",
                value=f"${value:,.2f}",
                delta=f"{pct_gain:+.1f}%",
                delta_color="normal",
            )

        fig = _create_mini_chart(state, gain_color)
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        clicked = st.button(
            "View Details",
            key=f"tile_{config.name}",
            use_container_width=True,
        )

        return clicked


def _create_mini_chart(state: PortfolioState, color: str) -> go.Figure | None:
    """Create a mini sparkline chart of portfolio performance."""
    if not state.trades:
        return None

    values = []
    timestamps = []
    running_cash = state.cash
    for holding in state.holdings:
        running_cash += holding.avg_price * holding.quantity

    for trade in state.trades[-20:]:
        timestamps.append(trade.timestamp)
        if trade.action == "BUY":
            running_cash -= trade.price * trade.quantity
        else:
            running_cash += trade.price * trade.quantity
        values.append(running_cash)

    if not values:
        return None

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(range(len(values))),
            y=values,
            mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=f"rgba({'0,255,0' if color == 'green' else '255,0,0'}, 0.1)",
        )
    )
    fig.update_layout(
        height=80,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
