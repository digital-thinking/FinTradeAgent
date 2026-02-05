import streamlit as st
from pathlib import Path

from fin_trade.services import PortfolioService, AgentService, SecurityService
from fin_trade.pages.overview import render_overview_page
from fin_trade.pages.portfolio_detail import render_portfolio_detail_page
from fin_trade.pages.system_health import render_system_health_page
from fin_trade.pages.dashboard import render_dashboard_page
from fin_trade.pages.pending_trades import render_pending_trades_page


def load_css():
    """Load the external CSS file."""
    css_path = Path(__file__).parent / "style.css"
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def main():
    st.set_page_config(
        page_title="Agentic Trade Assistant",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Load custom CSS
    load_css()

    # Initialize services (cached for performance)
    @st.cache_resource
    def get_services():
        security_service = SecurityService()
        portfolio_service = PortfolioService(security_service=security_service)
        agent_service = AgentService(security_service=security_service)
        return security_service, portfolio_service, agent_service

    security_service, portfolio_service, agent_service = get_services()

    # Initialize session state
    if "current_page" not in st.session_state:
        st.session_state.current_page = "dashboard"
    if "selected_portfolio" not in st.session_state:
        st.session_state.selected_portfolio = None

    # Sidebar navigation
    with st.sidebar:
        st.title("📈 Trade Assistant")
        st.divider()

        if st.button("📈 Summary Dashboard", use_container_width=True,
                     type="primary" if st.session_state.current_page == "dashboard" else "secondary"):
            st.session_state.current_page = "dashboard"
            st.session_state.selected_portfolio = None
            if "recommendation" in st.session_state:
                del st.session_state.recommendation
            st.rerun()

        if st.button("🏠 Portfolios", use_container_width=True,
                     type="primary" if st.session_state.current_page == "overview" else "secondary"):
            st.session_state.current_page = "overview"
            st.session_state.selected_portfolio = None
            if "recommendation" in st.session_state:
                del st.session_state.recommendation
            st.rerun()

        if st.button("📋 Pending Trades", use_container_width=True,
                     type="primary" if st.session_state.current_page == "pending_trades" else "secondary"):
            st.session_state.current_page = "pending_trades"
            st.session_state.selected_portfolio = None
            if "recommendation" in st.session_state:
                del st.session_state.recommendation
            st.rerun()

        if st.button("📊 System Health", use_container_width=True,
                     type="primary" if st.session_state.current_page == "system_health" else "secondary"):
            st.session_state.current_page = "system_health"
            st.session_state.selected_portfolio = None
            if "recommendation" in st.session_state:
                del st.session_state.recommendation
            st.rerun()

        # Show available portfolios in sidebar
        st.divider()
        st.markdown("### PORTFOLIOS")
        for portfolio_name in portfolio_service.list_portfolios():
            is_selected = (
                st.session_state.current_page == "detail"
                and st.session_state.selected_portfolio == portfolio_name
            )
            if st.button(
                f"{portfolio_name}",
                key=f"sidebar_{portfolio_name}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.selected_portfolio = portfolio_name
                st.session_state.current_page = "detail"
                if "recommendation" in st.session_state:
                    del st.session_state.recommendation
                st.rerun()

    # Main content routing
    if st.session_state.current_page == "overview":
        selected = render_overview_page(portfolio_service, agent_service, security_service)
        if selected:
            st.session_state.selected_portfolio = selected
            st.session_state.current_page = "detail"
            st.rerun()

    elif st.session_state.current_page == "dashboard":
        render_dashboard_page(portfolio_service)

    elif st.session_state.current_page == "detail":
        if st.session_state.selected_portfolio:
            def on_back():
                st.session_state.current_page = "overview"
                st.session_state.selected_portfolio = None
                if "recommendation" in st.session_state:
                    del st.session_state.recommendation
                st.rerun()

            def on_navigate_to_portfolio(name: str):
                st.session_state.selected_portfolio = name
                st.session_state.current_page = "detail"
                if "recommendation" in st.session_state:
                    del st.session_state.recommendation
                st.rerun()

            render_portfolio_detail_page(
                st.session_state.selected_portfolio,
                portfolio_service,
                agent_service,
                security_service,
                on_back=on_back,
                on_navigate_to_portfolio=on_navigate_to_portfolio,
            )
        else:
            st.session_state.current_page = "overview"
            st.rerun()

    elif st.session_state.current_page == "pending_trades":
        render_pending_trades_page()

    elif st.session_state.current_page == "system_health":
        render_system_health_page()


if __name__ == "__main__":
    main()
