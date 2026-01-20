"""UI components for the Fin Trade application."""

from fin_trade.components.portfolio_tile import render_portfolio_tile
from fin_trade.components.trade_display import render_trade_recommendations

__all__ = [
    "render_portfolio_tile",
    "render_trade_recommendations",
]
