"""Streamlit caching utilities for expensive calculations."""

import streamlit as st

from fin_trade.services import PortfolioService


@st.cache_data(ttl=60)
def get_portfolio_value(_portfolio_service: PortfolioService, portfolio_name: str) -> float:
    """Get cached portfolio value. TTL of 60 seconds for fresh-enough data.

    The underscore prefix on _portfolio_service tells Streamlit not to hash it.
    """
    _, state = _portfolio_service.load_portfolio(portfolio_name)
    return _portfolio_service.calculate_value(state)


@st.cache_data(ttl=60)
def get_portfolio_gain(
    _portfolio_service: PortfolioService, portfolio_name: str
) -> tuple[float, float]:
    """Get cached portfolio gain (absolute, percentage). TTL of 60 seconds.

    The underscore prefix on _portfolio_service tells Streamlit not to hash it.
    """
    config, state = _portfolio_service.load_portfolio(portfolio_name)
    return _portfolio_service.calculate_gain(config, state)


@st.cache_data(ttl=60)
def get_portfolio_metrics(
    _portfolio_service: PortfolioService, portfolio_name: str
) -> dict:
    """Get all portfolio metrics in one cached call.

    Returns dict with: value, absolute_gain, percentage_gain
    More efficient than separate calls when you need multiple values.
    """
    config, state = _portfolio_service.load_portfolio(portfolio_name)
    value = _portfolio_service.calculate_value(state)
    abs_gain, pct_gain = _portfolio_service.calculate_gain(config, state)
    return {
        "value": value,
        "absolute_gain": abs_gain,
        "percentage_gain": pct_gain,
    }


def clear_portfolio_cache(portfolio_name: str | None = None) -> None:
    """Clear cached portfolio data.

    Call this after executing trades to ensure fresh calculations.
    If portfolio_name is None, clears all cached portfolio data.
    """
    get_portfolio_value.clear()
    get_portfolio_gain.clear()
    get_portfolio_metrics.clear()