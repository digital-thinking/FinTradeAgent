"""Overview page showing all portfolio tiles."""

import streamlit as st

from fin_trade.cache import get_portfolio_metrics
from fin_trade.components import (
    render_portfolio_tile,
    render_large_status_badge,
    render_skeleton_card,
    render_skeleton_metrics_row,
)
from fin_trade.services import PortfolioService


def render_overview_page(portfolio_service: PortfolioService) -> str | None:
    """Render the overview page and return selected portfolio name if clicked."""
    st.title("Portfolio Overview")

    portfolios = portfolio_service.list_portfolios()

    if not portfolios:
        st.warning("No portfolios found. Create a YAML config in data/portfolios/")
        st.code(
            """# Example portfolio config (data/portfolios/growth.yaml)
name: "Growth Strategy"
strategy_prompt: "You are a growth-focused investor..."
initial_amount: 10000.0
num_initial_trades: 5
trades_per_run: 3
run_frequency: weekly
llm_provider: openai
llm_model: gpt-4o""",
            language="yaml",
        )
        return None

    # Create placeholders for metrics - show skeletons while loading
    metrics_placeholder = st.empty()
    with metrics_placeholder.container():
        render_skeleton_metrics_row(count=3)

    st.divider()

    # Create placeholders for portfolio cards - show skeletons while loading
    cards_placeholder = st.empty()
    with cards_placeholder.container():
        for i in range(0, min(len(portfolios), 4), 2):
            cols = st.columns(2)
            with cols[0]:
                render_skeleton_card()
            if i + 1 < len(portfolios):
                with cols[1]:
                    render_skeleton_card()

    # Load portfolio data
    total_value = 0
    total_gain = 0
    overdue_count = 0

    portfolio_data = []
    for filename in portfolios:
        try:
            config, state = portfolio_service.load_portfolio(filename)
            metrics = get_portfolio_metrics(portfolio_service, filename)
            is_overdue = portfolio_service.is_execution_overdue(config, state)

            total_value += metrics["value"]
            total_gain += metrics["absolute_gain"]
            if is_overdue:
                overdue_count += 1

            portfolio_data.append((filename, config, state))
        except Exception as e:
            st.error(f"Error loading portfolio {filename}: {e}")

    # Replace metrics skeleton with actual metrics
    with metrics_placeholder.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Value", f"${total_value:,.2f}")
        with col2:
            gain_pct = (total_gain / (total_value - total_gain) * 100) if (total_value - total_gain) > 0 else 0
            st.metric("Total Gain/Loss", f"${total_gain:,.2f}", delta=f"{gain_pct:+.1f}%")
        with col3:
            render_large_status_badge(overdue_count > 0, overdue_count)

    # Replace cards skeleton with actual portfolio tiles
    with cards_placeholder.container():
        for i in range(0, len(portfolio_data), 2):
            cols = st.columns(2)

            # First item in the row
            filename, config, state = portfolio_data[i]
            with cols[0]:
                if render_portfolio_tile(config, state, portfolio_service, portfolio_name=filename):
                    return filename

            # Second item in the row (if exists)
            if i + 1 < len(portfolio_data):
                filename, config, state = portfolio_data[i + 1]
                with cols[1]:
                    if render_portfolio_tile(config, state, portfolio_service, portfolio_name=filename):
                        return filename

    return None
