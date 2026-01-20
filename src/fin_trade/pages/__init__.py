"""Page modules for the Fin Trade application."""

from fin_trade.pages.overview import render_overview_page
from fin_trade.pages.portfolio_detail import render_portfolio_detail_page

__all__ = [
    "render_overview_page",
    "render_portfolio_detail_page",
]
