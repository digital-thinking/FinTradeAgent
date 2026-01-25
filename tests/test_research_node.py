"""Tests for research_node prompt building."""

import pytest

from fin_trade.agents.nodes.research import _build_research_prompt
from fin_trade.models import (
    Holding,
    PortfolioConfig,
    PortfolioState,
)


@pytest.fixture
def research_state():
    """Create a state dict for research node testing."""
    config = PortfolioConfig(
        name="Test Portfolio",
        strategy_prompt="Invest in undervalued dividend stocks with strong cash flows",
        initial_amount=10000.0,
        num_initial_trades=5,
        trades_per_run=3,
        run_frequency="weekly",
        llm_provider="openai",
        llm_model="gpt-4o",
    )
    portfolio_state = PortfolioState(
        cash=5000.0,
        holdings=[
            Holding(ticker="AAPL",
                name="Apple Inc.",
                quantity=10,
                avg_price=150.0,
            ),
            Holding(ticker="MSFT",
                name="Microsoft Corp.",
                quantity=5,
                avg_price=350.0,
            ),
        ],
        trades=[],
    )
    return {
        "portfolio_config": config,
        "portfolio_state": portfolio_state,
    }


@pytest.fixture
def empty_research_state():
    """Create state for empty portfolio."""
    config = PortfolioConfig(
        name="Test Portfolio",
        strategy_prompt="Buy momentum stocks",
        initial_amount=10000.0,
        num_initial_trades=5,
        trades_per_run=3,
        run_frequency="weekly",
        llm_provider="openai",
        llm_model="gpt-4o",
    )
    portfolio_state = PortfolioState(cash=10000.0, holdings=[], trades=[])
    return {
        "portfolio_config": config,
        "portfolio_state": portfolio_state,
    }


class TestBuildResearchPrompt:
    """Tests for _build_research_prompt function."""

    def test_includes_strategy_prompt(self, research_state):
        """Test that strategy prompt is included."""
        prompt = _build_research_prompt(research_state)

        assert "undervalued dividend stocks" in prompt
        assert "strong cash flows" in prompt

    def test_includes_holdings_tickers(self, research_state):
        """Test that current holdings tickers are listed."""
        prompt = _build_research_prompt(research_state)

        assert "AAPL" in prompt
        assert "MSFT" in prompt

    def test_shows_none_for_empty_holdings(self, empty_research_state):
        """Test that empty holdings shows None."""
        prompt = _build_research_prompt(empty_research_state)

        assert "None" in prompt

    def test_prompt_includes_research_instructions(self, research_state):
        """Test that research instructions are present."""
        prompt = _build_research_prompt(research_state)

        assert "market conditions" in prompt.lower()
        assert "search" in prompt.lower()

    def test_holdings_are_comma_separated(self, research_state):
        """Test that multiple holdings are comma separated."""
        prompt = _build_research_prompt(research_state)

        assert "AAPL, MSFT" in prompt or "MSFT, AAPL" in prompt
