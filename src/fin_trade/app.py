import streamlit as st

from fin_trade.services import PortfolioService, AgentService, StockDataService
from fin_trade.pages import render_overview_page, render_portfolio_detail_page


def main():
    st.set_page_config(
        page_title="Agentic Trade Assistant",
        page_icon=":chart_with_upwards_trend:",
        layout="wide",
    )

    stock_service = StockDataService()
    portfolio_service = PortfolioService(stock_service=stock_service)
    agent_service = AgentService(stock_service=stock_service)

    if "current_page" not in st.session_state:
        st.session_state.current_page = "overview"
    if "selected_portfolio" not in st.session_state:
        st.session_state.selected_portfolio = None

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
                stock_service,
                on_back=on_back,
            )
        else:
            st.session_state.current_page = "overview"
            st.rerun()


if __name__ == "__main__":
    main()
