"""Tests for portfolio detail calculations."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pandas as pd
import pytest

from fin_trade.models import Holding, PortfolioConfig, PortfolioState, Trade
from fin_trade.pages.portfolio_detail import _calculate_performance_data


def test_performance_data_marks_holdings_to_market_daily():
    """Value reflects daily closes instead of the original cost basis."""
    trade_date = (datetime.now() - timedelta(days=5)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    config = PortfolioConfig(
        name="Test Portfolio",
        strategy_prompt="Test strategy",
        initial_amount=10000.0,
        num_initial_trades=1,
        trades_per_run=1,
        run_frequency="weekly",
        llm_provider="openai",
        llm_model="gpt-4o",
    )
    trade = Trade(
        timestamp=trade_date,
        ticker="AAPL",
        name="Apple Inc.",
        action="BUY",
        quantity=10,
        price=100.0,
        reasoning="Test buy",
    )
    state = PortfolioState(
        cash=9000.0,
        trades=[trade],
        holdings=[Holding(ticker="AAPL", name="Apple Inc.", quantity=10, avg_price=100.0)],
        initial_investment=10000.0,
    )
    security_service = MagicMock()

    def rising_closes(tickers, start, end):
        dates = pd.date_range(
            start=pd.Timestamp(start).normalize(),
            end=pd.Timestamp(end).normalize(),
            freq="D",
        )
        closes = [100.0 + (10.0 * i / (len(dates) - 1)) for i in range(len(dates))]
        return pd.DataFrame({"AAPL": closes}, index=dates)

    security_service.get_closes.side_effect = rising_closes

    result = _calculate_performance_data(config, state, security_service)

    assert len(result["timestamps"]) == 6
    assert result["cash_values"][-1] == 9000.0
    assert result["holdings_values"][-1] == pytest.approx(1100.0)
    assert result["values"][-1] == pytest.approx(10100.0)


def test_performance_data_returns_empty_lists_without_trades():
    """No-trade portfolios have no historical curve."""
    config = PortfolioConfig(
        name="Test Portfolio",
        strategy_prompt="Test strategy",
        initial_amount=10000.0,
        num_initial_trades=1,
        trades_per_run=1,
        run_frequency="weekly",
        llm_provider="openai",
        llm_model="gpt-4o",
    )
    state = PortfolioState(cash=10000.0, trades=[], holdings=[])

    result = _calculate_performance_data(config, state, MagicMock())

    assert result == {
        "timestamps": [],
        "values": [],
        "cash_values": [],
        "holdings_values": [],
        "trade_points": [],
    }
