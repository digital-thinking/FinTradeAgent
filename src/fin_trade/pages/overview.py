"""Overview page showing all portfolio tiles."""

from datetime import datetime

import streamlit as st

from fin_trade.cache import get_portfolio_metrics
from fin_trade.components import (
    render_portfolio_tile,
    render_large_status_badge,
    render_skeleton_card,
    render_skeleton_metrics_row,
)
from fin_trade.services import PortfolioService, SecurityService
from fin_trade.agents.service import LangGraphAgentService, DebateAgentService


def render_overview_page(
    portfolio_service: PortfolioService,
    agent_service=None,  # Not used, kept for compatibility
    security_service: SecurityService | None = None,
) -> str | None:
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
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            st.metric("Total Value", f"${total_value:,.2f}")
        with col2:
            gain_pct = (total_gain / (total_value - total_gain) * 100) if (total_value - total_gain) > 0 else 0
            st.metric("Total Gain/Loss", f"${total_gain:,.2f}", delta=f"{gain_pct:+.1f}%")
        with col3:
            render_large_status_badge(overdue_count > 0, overdue_count)
        with col4:
            if security_service:
                _render_run_all_button(portfolio_data, security_service, portfolio_service)

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


def _render_run_all_button(
    portfolio_data: list,
    security_service: SecurityService,
    portfolio_service: PortfolioService,
) -> None:
    """Render the Run All Agents button and handle execution."""
    if st.button("🚀 Run All", type="primary", use_container_width=True):
        _execute_all_agents(portfolio_data, security_service, portfolio_service)


@st.dialog("Running All Agents", width="large")
def _execute_all_agents(
    portfolio_data: list,
    security_service: SecurityService,
    portfolio_service: PortfolioService,
) -> None:
    """Execute agents for all portfolios and store recommendations."""
    total = len(portfolio_data)

    st.write(f"Running agents for {total} portfolio(s)...")

    progress_bar = st.progress(0, text="Starting...")
    status_text = st.empty()
    results_container = st.container()

    results = []

    for i, (filename, config, state) in enumerate(portfolio_data):
        progress = (i) / total
        progress_bar.progress(progress, text=f"Running {config.name}...")
        status_text.info(f"🔄 Running agent for **{config.name}** ({i + 1}/{total})...")

        try:
            # Determine which agent to use based on config
            if config.debate_config:
                agent = DebateAgentService(security_service=security_service)
                recommendations, metrics = agent.execute(config, state)
            else:
                agent = LangGraphAgentService(security_service=security_service)
                recommendations, metrics = agent.execute(config, state)

            state.last_execution = datetime.now()
            portfolio_service.save_state(filename, state)

            results.append({
                "portfolio": config.name,
                "success": True,
                "num_trades": len(recommendations.trades) if recommendations else 0,
            })

        except Exception as e:
            results.append({
                "portfolio": config.name,
                "success": False,
                "error": str(e),
            })

    progress_bar.progress(1.0, text="Complete!")
    status_text.empty()

    # Show summary
    with results_container:
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        if successful:
            total_trades = sum(r["num_trades"] for r in successful)
            st.success(
                f"✅ Ran {len(successful)} agent(s) - {total_trades} recommendations generated"
            )
            for r in successful:
                st.write(f"  • {r['portfolio']}: {r['num_trades']} trades")

        if failed:
            st.error(f"❌ {len(failed)} agent(s) failed:")
            for r in failed:
                st.write(f"  • {r['portfolio']}: {r.get('error', 'Unknown error')}")

    st.divider()
    st.info("👉 Go to **Pending Trades** in the sidebar to review and apply recommendations.")
    st.caption("Click outside this dialog or press ESC to close.")
