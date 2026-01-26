"""Tests for AgentService."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from fin_trade.models import (
    Holding,
    PortfolioConfig,
    PortfolioState,
    TradeRecommendation,
)
from fin_trade.services.agent import AgentService


@pytest.fixture
def agent_service(mock_security_service, mock_stock_data_service):
    """Create an AgentService with mocked services."""
    with patch("fin_trade.services.agent.load_dotenv"):
        service = AgentService(
            security_service=mock_security_service,
            stock_data_service=mock_stock_data_service,
        )
    return service


@pytest.fixture
def config():
    """Create a sample portfolio config."""
    return PortfolioConfig(
        name="Test Portfolio",
        strategy_prompt="Buy growth stocks with strong fundamentals",
        initial_amount=10000.0,
        num_initial_trades=5,
        trades_per_run=3,
        run_frequency="weekly",
        llm_provider="openai",
        llm_model="gpt-4o",
    )


@pytest.fixture
def state_with_holdings():
    """Create a portfolio state with holdings."""
    return PortfolioState(
        cash=5000.0,
        holdings=[
            Holding(
                ticker="AAPL",
                name="Apple Inc.",
                quantity=10,
                avg_price=150.0,
            ),
            Holding(
                ticker="MSFT",
                name="Microsoft Corp.",
                quantity=5,
                avg_price=350.0,
            ),
        ],
        trades=[],
        last_execution=datetime(2024, 1, 15, 10, 30),
    )


class TestBuildPrompt:
    """Tests for _build_prompt method."""

    def test_includes_strategy_prompt(self, agent_service, config, empty_portfolio_state):
        """Test that strategy prompt is included."""
        prompt = agent_service._build_prompt(config, empty_portfolio_state)

        assert "Buy growth stocks with strong fundamentals" in prompt

    def test_includes_cash_amount(self, agent_service, config, empty_portfolio_state):
        """Test that cash amount is included."""
        prompt = agent_service._build_prompt(config, empty_portfolio_state)

        assert "$10000.00" in prompt

    def test_includes_holdings_info(
        self, agent_service, config, state_with_holdings, mock_security_service
    ):
        """Test that holdings info is included."""
        mock_security_service.get_price.side_effect = [175.0, 400.0]  # AAPL, MSFT

        prompt = agent_service._build_prompt(config, state_with_holdings)

        assert "AAPL" in prompt
        assert "Apple Inc." in prompt
        assert "MSFT" in prompt

    def test_shows_gain_percentage_for_holdings(
        self, agent_service, config, state_with_holdings, mock_stock_data_service
    ):
        """Test that gain percentage is calculated and shown."""
        # Set mock prices: AAPL up 20%, MSFT up 10%
        mock_stock_data_service.set_prices({"AAPL": 180.0, "MSFT": 385.0})

        prompt = agent_service._build_prompt(config, state_with_holdings)

        # AAPL: (180-150)/150 = 20%
        assert "+20.0%" in prompt or "+20%" in prompt

    def test_price_lookup_error_propagates(
        self, agent_service, config, state_with_holdings, mock_stock_data_service
    ):
        """Test that price lookup errors propagate (fail fast per CLAUDE.md)."""
        # Make format_holdings_for_prompt raise an error
        mock_stock_data_service.format_holdings_for_prompt.side_effect = Exception("API error")

        # Should raise the exception (no fallback behavior)
        with pytest.raises(Exception, match="API error"):
            agent_service._build_prompt(config, state_with_holdings)

    def test_empty_portfolio_shows_none(self, agent_service, config, empty_portfolio_state):
        """Test that empty portfolio shows None for holdings."""
        prompt = agent_service._build_prompt(config, empty_portfolio_state)

        assert "None" in prompt

    def test_includes_trades_per_run(self, agent_service, config, empty_portfolio_state):
        """Test that trades_per_run constraint is included."""
        prompt = agent_service._build_prompt(config, empty_portfolio_state)

        assert "3" in prompt  # trades_per_run


class TestParseResponse:
    """Tests for _parse_response method."""

    def test_parses_valid_json_response(self, agent_service):
        """Test parsing a valid JSON response."""
        response = json.dumps({
            "trades": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "action": "BUY",
                    "quantity": 10,
                    "reasoning": "Strong growth",
                }
            ],
            "overall_reasoning": "Market looks bullish",
        })

        result = agent_service._parse_response(response)

        assert len(result.trades) == 1
        assert result.trades[0].ticker == "AAPL"
        assert result.trades[0].action == "BUY"
        assert result.trades[0].quantity == 10
        assert result.overall_reasoning == "Market looks bullish"

    def test_parses_json_with_markdown_code_blocks(self, agent_service):
        """Test parsing JSON wrapped in markdown code blocks."""
        response = """```json
{
    "trades": [
        {"ticker": "MSFT", "name": "Microsoft", "action": "SELL", "quantity": 5, "reasoning": "Taking profits"}
    ],
    "overall_reasoning": "Rebalancing portfolio"
}
```"""

        result = agent_service._parse_response(response)

        assert len(result.trades) == 1
        assert result.trades[0].ticker == "MSFT"
        assert result.trades[0].action == "SELL"

    def test_parses_json_with_plain_code_blocks(self, agent_service):
        """Test parsing JSON wrapped in plain code blocks."""
        response = """```
{"trades": [], "overall_reasoning": "No opportunities found"}
```"""

        result = agent_service._parse_response(response)

        assert len(result.trades) == 0
        assert result.overall_reasoning == "No opportunities found"

    def test_handles_empty_trades(self, agent_service):
        """Test parsing response with empty trades array."""
        response = json.dumps({
            "trades": [],
            "overall_reasoning": "Market uncertainty, holding cash",
        })

        result = agent_service._parse_response(response)

        assert len(result.trades) == 0
        assert result.overall_reasoning == "Market uncertainty, holding cash"

    def test_handles_missing_name_field(self, agent_service):
        """Test that missing name field falls back to ticker."""
        response = json.dumps({
            "trades": [
                {
                    "ticker": "GOOGL",
                    "action": "BUY",
                    "quantity": 3,
                    "reasoning": "AI momentum",
                }
            ],
            "overall_reasoning": "Tech sector strong",
        })

        result = agent_service._parse_response(response)

        assert result.trades[0].name == "GOOGL"  # Falls back to ticker

    def test_handles_missing_overall_reasoning(self, agent_service):
        """Test that missing overall_reasoning defaults to empty string."""
        response = json.dumps({
            "trades": [
                {"ticker": "NVDA", "name": "NVIDIA", "action": "BUY", "quantity": 2, "reasoning": "GPU demand"}
            ],
        })

        result = agent_service._parse_response(response)

        assert result.overall_reasoning == ""

    def test_raises_on_invalid_json(self, agent_service):
        """Test that invalid JSON raises ValueError."""
        response = "This is not valid JSON at all"

        with pytest.raises(ValueError, match="Failed to parse LLM response"):
            agent_service._parse_response(response)

    def test_raises_on_malformed_json(self, agent_service):
        """Test that malformed JSON raises ValueError."""
        response = '{"trades": [{"ticker": "AAPL"'  # Incomplete

        with pytest.raises(ValueError, match="Failed to parse LLM response"):
            agent_service._parse_response(response)

    def test_converts_quantity_to_int(self, agent_service):
        """Test that quantity is converted to int."""
        response = json.dumps({
            "trades": [
                {"ticker": "AAPL", "name": "Apple", "action": "BUY", "quantity": "10", "reasoning": "Test"}
            ],
            "overall_reasoning": "",
        })

        result = agent_service._parse_response(response)

        assert result.trades[0].quantity == 10
        assert isinstance(result.trades[0].quantity, int)


class TestSaveLog:
    """Tests for _save_log method."""

    def test_saves_log_file(self, agent_service, tmp_path):
        """Test that log file is created with correct content."""
        with patch("fin_trade.services.agent._logs_dir", tmp_path):
            agent_service._save_log(
                portfolio_name="test_portfolio",
                prompt="Test prompt content",
                response="Test response content",
                provider="openai",
                model="gpt-4o",
            )

        log_files = list(tmp_path.glob("*.md"))
        assert len(log_files) == 1

        content = log_files[0].read_text()
        assert "test_portfolio" in content
        assert "Test prompt content" in content
        assert "Test response content" in content
        assert "openai" in content
        assert "gpt-4o" in content

    def test_log_filename_includes_portfolio_name(self, agent_service, tmp_path):
        """Test that log filename includes portfolio name."""
        with patch("fin_trade.services.agent._logs_dir", tmp_path):
            agent_service._save_log(
                portfolio_name="my_special_portfolio",
                prompt="Prompt",
                response="Response",
                provider="anthropic",
                model="claude-3",
            )

        log_files = list(tmp_path.glob("*.md"))
        assert "my_special_portfolio" in log_files[0].name


class TestExecute:
    """Tests for execute method."""

    def test_execute_calls_llm_and_parses_response(
        self, agent_service, config, empty_portfolio_state, tmp_path
    ):
        """Test execute orchestrates prompt building, LLM call, and parsing."""
        mock_provider = MagicMock()
        mock_provider.generate.return_value = json.dumps({
            "trades": [
                {"ticker": "AAPL", "name": "Apple", "action": "BUY", "quantity": 5, "reasoning": "Test"}
            ],
            "overall_reasoning": "Test reasoning",
        })

        with patch("fin_trade.services.agent.LLMProviderFactory") as mock_factory:
            with patch("fin_trade.services.agent._logs_dir", tmp_path):
                mock_factory.get_provider.return_value = mock_provider

                result = agent_service.execute(config, empty_portfolio_state)

        assert len(result.trades) == 1
        assert result.trades[0].ticker == "AAPL"
        mock_factory.get_provider.assert_called_once_with("openai")
        mock_provider.generate.assert_called_once()

    def test_execute_saves_log(
        self, agent_service, config, empty_portfolio_state, tmp_path
    ):
        """Test that execute saves a log file."""
        mock_provider = MagicMock()
        mock_provider.generate.return_value = json.dumps({
            "trades": [],
            "overall_reasoning": "No trades",
        })

        with patch("fin_trade.services.agent.LLMProviderFactory") as mock_factory:
            with patch("fin_trade.services.agent._logs_dir", tmp_path):
                mock_factory.get_provider.return_value = mock_provider

                agent_service.execute(config, empty_portfolio_state)

        log_files = list(tmp_path.glob("*.md"))
        assert len(log_files) == 1
