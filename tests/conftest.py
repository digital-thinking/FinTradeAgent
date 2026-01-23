"""Shared fixtures and mocks for tests."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from fin_trade.models import (
    Holding,
    Trade,
    PortfolioConfig,
    PortfolioState,
    TradeRecommendation,
    AgentRecommendation,
)
from fin_trade.services.security import Security


@pytest.fixture
def mock_security_service():
    """Create a mock SecurityService."""
    mock = MagicMock()

    # Default price lookup
    mock.get_price.return_value = 100.0
    mock.force_update_price.return_value = 100.0

    # Default security lookup
    def lookup_ticker(ticker: str) -> Security:
        return Security(
            isin=f"US{ticker}123456",
            ticker=ticker.upper(),
            name=f"{ticker.upper()} Inc.",
        )

    mock.lookup_ticker.side_effect = lookup_ticker

    return mock


@pytest.fixture
def sample_holding():
    """Create a sample holding."""
    return Holding(
        isin="US0378331005",
        ticker="AAPL",
        name="Apple Inc.",
        quantity=10,
        avg_price=150.0,
    )


@pytest.fixture
def sample_trade():
    """Create a sample trade."""
    return Trade(
        timestamp=datetime(2024, 1, 15, 10, 30),
        isin="US0378331005",
        ticker="AAPL",
        name="Apple Inc.",
        action="BUY",
        quantity=10,
        price=150.0,
        reasoning="Strong fundamentals",
    )


@pytest.fixture
def sample_portfolio_config():
    """Create a sample portfolio config."""
    return PortfolioConfig(
        name="Test Portfolio",
        strategy_prompt="Test strategy prompt",
        initial_amount=10000.0,
        num_initial_trades=5,
        trades_per_run=3,
        run_frequency="weekly",
        llm_provider="openai",
        llm_model="gpt-4o",
        agent_mode="simple",
    )


@pytest.fixture
def sample_portfolio_state(sample_holding, sample_trade):
    """Create a sample portfolio state with holdings and trades."""
    return PortfolioState(
        cash=5000.0,
        holdings=[sample_holding],
        trades=[sample_trade],
        last_execution=datetime(2024, 1, 15, 10, 30),
    )


@pytest.fixture
def empty_portfolio_state():
    """Create an empty portfolio state."""
    return PortfolioState(cash=10000.0)


@pytest.fixture
def sample_trade_recommendation():
    """Create a sample trade recommendation."""
    return TradeRecommendation(
        ticker="MSFT",
        name="Microsoft Corp.",
        action="BUY",
        quantity=5,
        reasoning="Strong cloud growth",
    )


@pytest.fixture
def sample_agent_recommendation(sample_trade_recommendation):
    """Create a sample agent recommendation."""
    return AgentRecommendation(
        trades=[sample_trade_recommendation],
        overall_reasoning="Market conditions favorable",
    )


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary directories for portfolios and state."""
    portfolios_dir = tmp_path / "portfolios"
    state_dir = tmp_path / "state"
    portfolios_dir.mkdir()
    state_dir.mkdir()
    return {"portfolios": portfolios_dir, "state": state_dir}


@pytest.fixture
def sample_yaml_config(temp_data_dir):
    """Create a sample YAML config file."""
    config_content = """name: Test Portfolio
strategy_prompt: Test strategy for growth stocks
initial_amount: 10000.0
num_initial_trades: 5
trades_per_run: 3
run_frequency: weekly
llm_provider: openai
llm_model: gpt-4o
agent_mode: simple
"""
    config_path = temp_data_dir["portfolios"] / "test_portfolio.yaml"
    config_path.write_text(config_content)
    return config_path
