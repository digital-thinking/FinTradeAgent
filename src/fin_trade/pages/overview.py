"""Overview page showing all portfolio tiles."""

import streamlit as st

from fin_trade.components import render_portfolio_tile
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

    total_value = 0
    total_gain = 0
    overdue_count = 0

    portfolio_data = []
    for filename in portfolios:
        try:
            config, state = portfolio_service.load_portfolio(filename)
            value = portfolio_service.calculate_value(state)
            abs_gain, _ = portfolio_service.calculate_gain(config, state)
            is_overdue = portfolio_service.is_execution_overdue(config, state)

            total_value += value
            total_gain += abs_gain
            if is_overdue:
                overdue_count += 1

            portfolio_data.append((filename, config, state))
        except Exception as e:
            st.error(f"Error loading portfolio {filename}: {e}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Value", f"${total_value:,.2f}")
    with col2:
        st.metric("Total Gain/Loss", f"${total_gain:,.2f}")
    with col3:
        if overdue_count > 0:
            st.metric("Overdue", f"{overdue_count} portfolios", delta="-Needs attention")
        else:
            st.metric("Status", "All current")

    st.divider()

    cols = st.columns(2)
    for i, (filename, config, state) in enumerate(portfolio_data):
        with cols[i % 2]:
            if render_portfolio_tile(config, state, portfolio_service):
                return filename

    return None
