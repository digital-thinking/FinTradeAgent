"""Tests for generate_trades_node."""

import json
import pytest

from fin_trade.agents.nodes.generate import (
    _build_generate_prompt,
    _parse_json_response,
)
from fin_trade.models import (
    Holding,
    PortfolioConfig,
    PortfolioState,
)


@pytest.fixture
def simple_state():
    """Create a minimal state dict for testing."""
    config = PortfolioConfig(
        name="Test",
        strategy_prompt="Growth strategy",
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
        ],
        trades=[],
    )
    return {
        "portfolio_config": config,
        "portfolio_state": portfolio_state,
        "analysis": "Buy NVDA for AI growth, sell AAPL due to slowing iPhone sales",
        "price_data": {"AAPL": 155.0},
    }


@pytest.fixture
def empty_portfolio_state_dict():
    """Create state for an empty portfolio."""
    config = PortfolioConfig(
        name="Test",
        strategy_prompt="Growth strategy",
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
        "analysis": "Initial portfolio setup - buy diversified tech stocks",
        "price_data": {},
    }


class TestBuildGeneratePrompt:
    """Tests for _build_generate_prompt function."""

    def test_includes_analysis(self, simple_state):
        """Test that analysis is included in prompt."""
        prompt = _build_generate_prompt(simple_state)

        assert "Buy NVDA for AI growth" in prompt
        assert "sell AAPL" in prompt

    def test_includes_cash_amount(self, simple_state):
        """Test that cash amount is included."""
        prompt = _build_generate_prompt(simple_state)

        assert "$5000.00" in prompt

    def test_includes_holdings_with_current_prices(self, simple_state):
        """Test that holdings with current prices are included."""
        prompt = _build_generate_prompt(simple_state)

        assert "AAPL" in prompt
        assert "10 shares" in prompt
        assert "$155.00" in prompt  # From price_data

    def test_falls_back_to_avg_price_when_no_current(self, simple_state):
        """Test fallback to avg_price when no current price."""
        simple_state["price_data"] = {}  # No current prices

        prompt = _build_generate_prompt(simple_state)

        assert "$150.00" in prompt  # avg_price

    def test_initial_portfolio_instruction(self, empty_portfolio_state_dict):
        """Test special instruction for initial portfolio."""
        prompt = _build_generate_prompt(empty_portfolio_state_dict)

        assert "NEW PORTFOLIO" in prompt
        assert "5 initial trades" in prompt or "at least 5" in prompt

    def test_existing_portfolio_instruction(self, simple_state):
        """Test max trades instruction for existing portfolio."""
        prompt = _build_generate_prompt(simple_state)

        assert "Maximum 3 trades" in prompt

    def test_empty_holdings_shows_empty(self, empty_portfolio_state_dict):
        """Test that empty holdings shows appropriate message."""
        prompt = _build_generate_prompt(empty_portfolio_state_dict)

        assert "empty portfolio" in prompt.lower() or "None" in prompt

    def test_includes_user_context_when_provided(self, simple_state):
        """Test that user context is included when provided."""
        simple_state["user_context"] = "Focus on semiconductor stocks"

        prompt = _build_generate_prompt(simple_state)

        assert "Focus on semiconductor stocks" in prompt
        assert "USER GUIDANCE" in prompt

    def test_handles_missing_user_context(self, simple_state):
        """Test graceful handling when user_context not in state."""
        simple_state.pop("user_context", None)

        prompt = _build_generate_prompt(simple_state)

        # Should not raise, just exclude user context section
        assert "USER GUIDANCE" not in prompt

    def test_uses_moderator_analysis_for_debate_mode(self, simple_state):
        """Test that moderator_analysis is used when analysis is missing."""
        simple_state.pop("analysis", None)
        simple_state["moderator_analysis"] = "Debate consensus: buy tech stocks"

        prompt = _build_generate_prompt(simple_state)

        assert "Debate consensus: buy tech stocks" in prompt


class TestParseJsonResponse:
    """Tests for _parse_json_response function."""

    def test_parses_valid_response(self):
        """Test parsing a valid JSON response."""
        response = json.dumps({
            "trades": [
                {
                    "ticker": "NVDA",
                    "name": "NVIDIA Corp",
                    "action": "BUY",
                    "quantity": 5,
                    "reasoning": "AI demand",
                    "stop_loss_price": 850.0,
                    "take_profit_price": 1100.0,
                }
            ],
            "overall_reasoning": "Tech sector momentum",
        })

        result = _parse_json_response(response)

        assert len(result.trades) == 1
        assert result.trades[0].ticker == "NVDA"
        assert result.trades[0].stop_loss_price == 850.0
        assert result.trades[0].take_profit_price == 1100.0

    def test_uppercases_ticker(self):
        """Test that ticker is uppercased."""
        response = json.dumps({
            "trades": [
                {"ticker": "aapl", "name": "Apple", "action": "buy", "quantity": 10, "reasoning": "Test"}
            ],
            "overall_reasoning": "",
        })

        result = _parse_json_response(response)

        assert result.trades[0].ticker == "AAPL"
        assert result.trades[0].action == "BUY"

    def test_strips_markdown_json_block(self):
        """Test stripping ```json blocks."""
        response = """```json
{
    "trades": [{"ticker": "MSFT", "name": "Microsoft", "action": "SELL", "quantity": 3, "reasoning": "Test"}],
    "overall_reasoning": "Test"
}
```"""

        result = _parse_json_response(response)

        assert len(result.trades) == 1
        assert result.trades[0].ticker == "MSFT"

    def test_strips_plain_code_block(self):
        """Test stripping plain ``` blocks."""
        response = """```
{"trades": [], "overall_reasoning": "No trades"}
```"""

        result = _parse_json_response(response)

        assert len(result.trades) == 0

    def test_handles_missing_stop_loss(self):
        """Test that missing stop_loss_price results in None."""
        response = json.dumps({
            "trades": [
                {"ticker": "AAPL", "name": "Apple", "action": "SELL", "quantity": 5, "reasoning": "Taking profits"}
            ],
            "overall_reasoning": "",
        })

        result = _parse_json_response(response)

        assert result.trades[0].stop_loss_price is None
        assert result.trades[0].take_profit_price is None

    def test_handles_null_stop_loss(self):
        """Test that null stop_loss values result in None."""
        response = json.dumps({
            "trades": [
                {
                    "ticker": "AAPL",
                    "name": "Apple",
                    "action": "SELL",
                    "quantity": 5,
                    "reasoning": "Test",
                    "stop_loss_price": None,
                    "take_profit_price": None,
                }
            ],
            "overall_reasoning": "",
        })

        result = _parse_json_response(response)

        assert result.trades[0].stop_loss_price is None

    def test_converts_quantity_to_int(self):
        """Test quantity is converted to int."""
        response = json.dumps({
            "trades": [
                {"ticker": "AAPL", "name": "Apple", "action": "BUY", "quantity": "15", "reasoning": "Test"}
            ],
            "overall_reasoning": "",
        })

        result = _parse_json_response(response)

        assert result.trades[0].quantity == 15
        assert isinstance(result.trades[0].quantity, int)

    def test_converts_prices_to_float(self):
        """Test stop_loss and take_profit are converted to float."""
        response = json.dumps({
            "trades": [
                {
                    "ticker": "AAPL",
                    "name": "Apple",
                    "action": "BUY",
                    "quantity": 10,
                    "reasoning": "Test",
                    "stop_loss_price": "175",
                    "take_profit_price": "210",
                }
            ],
            "overall_reasoning": "",
        })

        result = _parse_json_response(response)

        assert result.trades[0].stop_loss_price == 175.0
        assert result.trades[0].take_profit_price == 210.0

    def test_handles_empty_trades(self):
        """Test parsing empty trades array."""
        response = json.dumps({
            "trades": [],
            "overall_reasoning": "No good opportunities",
        })

        result = _parse_json_response(response)

        assert len(result.trades) == 0
        assert result.overall_reasoning == "No good opportunities"

    def test_fallback_name_to_ticker(self):
        """Test that missing name falls back to ticker."""
        response = json.dumps({
            "trades": [
                {"ticker": "GOOGL", "action": "BUY", "quantity": 2, "reasoning": "Search dominance"}
            ],
            "overall_reasoning": "",
        })

        result = _parse_json_response(response)

        assert result.trades[0].name == "GOOGL"

    def test_raises_on_invalid_json(self):
        """Test that invalid JSON raises error."""
        response = "Not valid JSON at all"

        with pytest.raises(json.JSONDecodeError):
            _parse_json_response(response)

    def test_handles_multiple_trades(self):
        """Test parsing multiple trades."""
        response = json.dumps({
            "trades": [
                {"ticker": "AAPL", "name": "Apple", "action": "SELL", "quantity": 5, "reasoning": "Profit taking"},
                {"ticker": "NVDA", "name": "NVIDIA", "action": "BUY", "quantity": 3, "reasoning": "AI growth"},
                {"ticker": "MSFT", "name": "Microsoft", "action": "BUY", "quantity": 2, "reasoning": "Cloud momentum"},
            ],
            "overall_reasoning": "Rebalancing portfolio",
        })

        result = _parse_json_response(response)

        assert len(result.trades) == 3
        assert result.trades[0].action == "SELL"
        assert result.trades[1].action == "BUY"
        assert result.trades[2].action == "BUY"

    def test_handles_whitespace_in_response(self):
        """Test parsing response with extra whitespace."""
        response = """

        {
            "trades": [],
            "overall_reasoning": "Holding"
        }

        """

        result = _parse_json_response(response)

        assert result.overall_reasoning == "Holding"
