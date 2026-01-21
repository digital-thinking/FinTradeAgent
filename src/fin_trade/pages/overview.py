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
        gain_pct = (total_gain / (total_value - total_gain) * 100) if (total_value - total_gain) > 0 else 0
        st.metric("Total Gain/Loss", f"${total_gain:,.2f}", delta=f"{gain_pct:+.1f}%")
    with col3:
        if overdue_count > 0:
            st.markdown(
                f"""<div style="background: linear-gradient(135deg, #ff6b6b, #ee5a5a);
                padding: 16px; border-radius: 10px; text-align: center; margin-top: 4px;">
                <span style="font-size: 0.85em; color: rgba(255,255,255,0.8);">Attention Needed</span><br>
                <span style="font-size: 1.5em; font-weight: bold; color: white;">⚠️ {overdue_count} Overdue</span>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """<div style="background: linear-gradient(135deg, #51cf66, #40c057);
                padding: 16px; border-radius: 10px; text-align: center; margin-top: 4px;">
                <span style="font-size: 0.85em; color: rgba(255,255,255,0.8);">Status</span><br>
                <span style="font-size: 1.5em; font-weight: bold; color: white;">✓ All Current</span>
                </div>""",
                unsafe_allow_html=True,
            )

    st.divider()

    # Display portfolios in a 2-column grid
    # Create new row of columns for every 2 portfolios
    for i in range(0, len(portfolio_data), 2):
        cols = st.columns(2)

        # First item in the row
        filename, config, state = portfolio_data[i]
        with cols[0]:
            if render_portfolio_tile(config, state, portfolio_service):
                return filename

        # Second item in the row (if exists)
        if i + 1 < len(portfolio_data):
            filename, config, state = portfolio_data[i + 1]
            with cols[1]:
                if render_portfolio_tile(config, state, portfolio_service):
                    return filename

    return None
