import streamlit as st

from fin_trade.services import PortfolioService, AgentService, SecurityService
from fin_trade.pages.overview import render_overview_page
from fin_trade.pages.portfolio_detail import render_portfolio_detail_page


def main():
    st.set_page_config(
        page_title="Agentic Trade Assistant",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Custom CSS for better styling
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
        }
        .stButton > button {
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.5rem;
        }
        /* Hide sidebar navigation items */
        [data-testid="stSidebarNav"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

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
        st.session_state.current_page = "overview"
    if "selected_portfolio" not in st.session_state:
        st.session_state.selected_portfolio = None

    # Sidebar navigation
    with st.sidebar:
        st.title("📈 Trade Assistant")
        st.divider()

        if st.button("🏠 Portfolio Overview", use_container_width=True,
                     type="primary" if st.session_state.current_page == "overview" else "secondary"):
            st.session_state.current_page = "overview"
            st.session_state.selected_portfolio = None
            if "recommendation" in st.session_state:
                del st.session_state.recommendation
            st.rerun()

        # Show available portfolios in sidebar
        st.divider()
        st.caption("PORTFOLIOS")
        for portfolio_name in portfolio_service.list_portfolios():
            is_selected = (
                st.session_state.current_page == "detail"
                and st.session_state.selected_portfolio == portfolio_name
            )
            if st.button(
                f"📊 {portfolio_name}",
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
        selected = render_overview_page(portfolio_service)
        if selected:
            st.session_state.selected_portfolio = selected
            st.session_state.current_page = "detail"
            st.rerun()

    elif st.session_state.current_page == "detail":
        if st.session_state.selected_portfolio:
            def on_back():
                st.session_state.current_page = "overview"
                st.session_state.selected_portfolio = None
                if "recommendation" in st.session_state:
                    del st.session_state.recommendation
                st.rerun()

            render_portfolio_detail_page(
                st.session_state.selected_portfolio,
                portfolio_service,
                agent_service,
                security_service,
                on_back=on_back,
            )
        else:
            st.session_state.current_page = "overview"
            st.rerun()


if __name__ == "__main__":
    main()
