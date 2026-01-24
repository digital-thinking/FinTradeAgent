"""Tests for analysis_node prompt building."""

import pytest

from fin_trade.agents.nodes.analysis import _build_analysis_prompt
from fin_trade.models import (
    Holding,
    PortfolioConfig,
    PortfolioState,
)


@pytest.fixture
def analysis_state():
    """Create a state dict for analysis node testing."""
    config = PortfolioConfig(
        name="Test Portfolio",
        strategy_prompt="Focus on high-growth tech companies with strong moats",
        initial_amount=10000.0,
        num_initial_trades=5,
        trades_per_run=3,
        run_frequency="weekly",
        llm_provider="openai",
        llm_model="gpt-4o",
    )
    portfolio_state = PortfolioState(
        cash=3500.0,
        holdings=[
            Holding(
                isin="US0378331005",
                ticker="AAPL",
                name="Apple Inc.",
                quantity=10,
                avg_price=150.0,
            ),
            Holding(
                isin="US67066G1040",
                ticker="NVDA",
                name="NVIDIA Corp.",
                quantity=5,
                avg_price=800.0,
            ),
        ],
        trades=[],
    )
    return {
        "portfolio_config": config,
        "portfolio_state": portfolio_state,
        "market_research": "NVDA up 5% on AI datacenter demand. AAPL reports earnings next week.",
        "price_data": {"AAPL": 165.0, "NVDA": 880.0},
    }


@pytest.fixture
def empty_analysis_state():
    """Create state for empty portfolio."""
    config = PortfolioConfig(
        name="Test Portfolio",
        strategy_prompt="Buy value stocks",
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
        "market_research": "Market conditions favorable",
        "price_data": {},
    }


class TestBuildAnalysisPrompt:
    """Tests for _build_analysis_prompt function."""

    def test_includes_strategy_prompt(self, analysis_state):
        """Test that strategy prompt is included."""
        prompt = _build_analysis_prompt(analysis_state)

        assert "high-growth tech companies" in prompt
        assert "strong moats" in prompt

    def test_includes_cash_amount(self, analysis_state):
        """Test that cash amount is included."""
        prompt = _build_analysis_prompt(analysis_state)

        assert "$3500.00" in prompt

    def test_includes_initial_amount(self, analysis_state):
        """Test that initial investment is included."""
        prompt = _build_analysis_prompt(analysis_state)

        assert "$10000.00" in prompt

    def test_includes_market_research(self, analysis_state):
        """Test that market research is included."""
        prompt = _build_analysis_prompt(analysis_state)

        assert "NVDA up 5%" in prompt
        assert "AI datacenter demand" in prompt
        assert "AAPL reports earnings" in prompt

    def test_includes_holdings_with_gain(self, analysis_state):
        """Test that holdings with gain/loss percentage are shown."""
        prompt = _build_analysis_prompt(analysis_state)

        # AAPL: (165-150)/150 = 10%
        assert "AAPL" in prompt
        assert "+10.0%" in prompt

        # NVDA: (880-800)/800 = 10%
        assert "NVDA" in prompt

    def test_uses_current_price_from_price_data(self, analysis_state):
        """Test that current price from price_data is used."""
        prompt = _build_analysis_prompt(analysis_state)

        assert "$165.00" in prompt  # AAPL current price
        assert "$880.00" in prompt  # NVDA current price

    def test_falls_back_to_avg_price_when_no_current(self, analysis_state):
        """Test fallback to avg_price when no current price available."""
        analysis_state["price_data"] = {}  # No price data

        prompt = _build_analysis_prompt(analysis_state)

        assert "$150.00" in prompt  # Falls back to avg_price

    def test_empty_holdings_shows_empty_message(self, empty_analysis_state):
        """Test that empty holdings shows appropriate message."""
        prompt = _build_analysis_prompt(empty_analysis_state)

        assert "empty portfolio" in prompt.lower() or "None" in prompt

    def test_includes_user_context_when_provided(self, analysis_state):
        """Test that user context is included when present."""
        analysis_state["user_context"] = "Consider selling Apple before earnings"

        prompt = _build_analysis_prompt(analysis_state)

        assert "Consider selling Apple before earnings" in prompt
        assert "USER GUIDANCE" in prompt

    def test_no_user_context_section_when_missing(self, analysis_state):
        """Test that no user context section when not provided."""
        analysis_state.pop("user_context", None)

        prompt = _build_analysis_prompt(analysis_state)

        assert "USER GUIDANCE" not in prompt

    def test_handles_missing_market_research(self, analysis_state):
        """Test graceful handling when market_research not in state."""
        analysis_state.pop("market_research", None)

        prompt = _build_analysis_prompt(analysis_state)

        assert "No research available" in prompt

    def test_calculates_gain_correctly_for_loss(self, analysis_state):
        """Test that negative gain (loss) is calculated correctly."""
        analysis_state["price_data"]["AAPL"] = 120.0  # Below avg price of 150

        prompt = _build_analysis_prompt(analysis_state)

        # (120-150)/150 = -20%
        assert "-20.0%" in prompt

    def test_handles_zero_avg_price(self):
        """Test handling of zero average price edge case."""
        config = PortfolioConfig(
            name="Test",
            strategy_prompt="Test",
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
                Holding(
                    isin="US123",
                    ticker="TEST",
                    name="Test Stock",
                    quantity=10,
                    avg_price=0.0,  # Edge case: zero avg price
                )
            ],
            trades=[],
        )
        state = {
            "portfolio_config": config,
            "portfolio_state": portfolio_state,
            "market_research": "Test",
            "price_data": {"TEST": 100.0},
        }

        prompt = _build_analysis_prompt(state)

        # Should show 0% gain when avg_price is 0 (not division by zero)
        assert "+0.0%" in prompt or "0.0%" in prompt
