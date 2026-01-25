"""Test that agent service includes market data in prompts."""

from unittest.mock import MagicMock

from fin_trade.models import Holding, PortfolioConfig, PortfolioState
from fin_trade.services.agent import AgentService
from fin_trade.services.market_data import MarketDataService


def test_agent_includes_market_data_in_prompt():
    """Verify that _build_prompt includes market data context."""
    mock_market_data = MagicMock(spec=MarketDataService)
    mock_market_data.get_full_context_for_holdings.return_value = (
        "MARKET OVERVIEW:\n  S&P 500: 4,800.00 +1.25%"
    )

    mock_security = MagicMock()
    mock_security.get_price.return_value = 150.0

    agent = AgentService(
        security_service=mock_security, market_data_service=mock_market_data
    )

    config = PortfolioConfig(
        name="Test",
        strategy_prompt="Test strategy",
        initial_amount=10000.0,
        num_initial_trades=5,
        trades_per_run=3,
        run_frequency="weekly",
        llm_provider="openai",
        llm_model="gpt-4o",
    )
    state = PortfolioState(
        cash=5000.0,
        holdings=[
            Holding(
                isin="US0378331005",
                ticker="AAPL",
                name="Apple Inc.",
                quantity=10,
                avg_price=145.0,
            )
        ],
        trades=[],
    )

    prompt = agent._build_prompt(config, state)

    # Verify market data section is present
    assert "MARKET INTELLIGENCE DATA" in prompt
    assert "S&P 500" in prompt
    assert "USING MARKET INTELLIGENCE DATA" in prompt

    # Verify the service was called with correct tickers
    mock_market_data.get_full_context_for_holdings.assert_called_once_with(["AAPL"])
