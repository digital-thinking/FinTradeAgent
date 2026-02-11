"""Shared fixtures and mocks for tests."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from backend.fin_trade.models import (
    AssetClass,
    Holding,
    Trade,
    PortfolioConfig,
    PortfolioState,
    TradeRecommendation,
    AgentRecommendation,
)
from backend.fin_trade.services.security import Security
from backend.fin_trade.services.stock_data import PriceContext


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
            ticker=ticker.upper(),
            name=f"{ticker.upper()} Inc.",
        )

    mock.lookup_ticker.side_effect = lookup_ticker
    mock.is_crypto_ticker.side_effect = lambda ticker: ticker.upper().endswith("-USD")

    def validate_ticker_for_asset_class(ticker: str, asset_class: AssetClass) -> bool:
        normalized = ticker.upper()
        is_crypto = normalized.endswith("-USD")
        if asset_class == AssetClass.CRYPTO and not is_crypto:
            raise ValueError(f"Ticker {normalized} is not a crypto ticker. Use format like BTC-USD.")
        if asset_class == AssetClass.STOCKS and is_crypto:
            raise ValueError(
                f"Ticker {normalized} is a crypto ticker. This portfolio only allows stocks."
            )
        return True

    mock.validate_ticker_for_asset_class.side_effect = validate_ticker_for_asset_class

    return mock


@pytest.fixture
def sample_holding():
    """Create a sample holding."""
    return Holding(
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


def create_mock_price_context(
    ticker: str,
    current_price: float,
    change_5d_pct: float = 5.0,
    change_30d_pct: float = 10.0,
) -> PriceContext:
    """Helper to create a mock PriceContext."""
    return PriceContext(
        ticker=ticker,
        current_price=current_price,
        change_5d_pct=change_5d_pct,
        change_30d_pct=change_30d_pct,
        high_52w=current_price * 1.2,
        low_52w=current_price * 0.8,
        pct_from_52w_high=-16.7,
        pct_from_52w_low=25.0,
        rsi_14=50.0,
        volume_avg_20d=1000000.0,
        volume_ratio=1.0,
        ma_20=current_price * 0.98,
        ma_50=current_price * 0.95,
        trend_summary=f"↗+{change_5d_pct:.1f}% (5d), above 20-MA",
    )


@pytest.fixture
def mock_stock_data_service():
    """Create a mock StockDataService with configurable prices."""
    mock = MagicMock()
    mock._mock_prices = {}  # Initialize to empty dict to avoid MagicMock auto-creation

    # Default behavior - returns formatted string for holdings
    def format_holdings(
        holdings,
        price_contexts=None,
        security_service=None,
        asset_class=AssetClass.STOCKS,
    ):
        if not holdings:
            return "  None (empty portfolio)"

        unit_label = "units" if asset_class == AssetClass.CRYPTO else "shares"
        lines = []
        for h in holdings:
            # Use the _mock_prices dict if set, otherwise default
            price = getattr(mock, "_mock_prices", {}).get(h.ticker, h.avg_price * 1.1)
            gain = ((price - h.avg_price) / h.avg_price * 100) if h.avg_price > 0 else 0
            quantity = (
                f"{h.quantity:.8f}".rstrip("0").rstrip(".")
                if asset_class == AssetClass.CRYPTO
                else f"{int(h.quantity)}"
            )
            line = (
                f"  - {h.ticker} - {h.name}: {quantity} {unit_label} @ avg ${h.avg_price:.2f}\n"
                f"    Current: ${price:.2f} | +5.0% (5d) | +10.0% (30d)\n"
                f"    P/L: {gain:+.1f}%"
            )
            lines.append(line)
        return "\n".join(lines)

    mock.format_holdings_for_prompt.side_effect = format_holdings

    # Get price context
    def get_price_context(ticker, security_service=None):
        price = getattr(mock, "_mock_prices", {}).get(ticker, 100.0)
        return create_mock_price_context(ticker, price)

    mock.get_price_context.side_effect = get_price_context

    # Get holdings context
    def get_holdings_context(tickers, security_service=None):
        return {t: get_price_context(t) for t in tickers}

    mock.get_holdings_context.side_effect = get_holdings_context

    # Helper method to set mock prices
    def set_prices(prices: dict):
        mock._mock_prices = prices

    mock.set_prices = set_prices

    return mock


# FastAPI specific fixtures
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

# Add src and backend to path for API tests
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent / "backend"))


@pytest.fixture
def client():
    """Create FastAPI test client."""
    try:
        from backend.main import app
        return TestClient(app)
    except ImportError:
        # If backend modules not available, skip API tests
        pytest.skip("Backend modules not available for API testing")


@pytest.fixture
def sample_portfolio_config_api():
    """Sample portfolio configuration for API testing."""
    return {
        "name": "test_portfolio",
        "initial_capital": 10000.0,
        "llm_model": "gpt-4",
        "asset_class": "stocks", 
        "agent_mode": "langgraph",
        "run_frequency": "daily",
        "scheduler_enabled": False,
        "auto_apply_trades": False,
        "ollama_base_url": "http://localhost:11434"
    }


@pytest.fixture
def sample_portfolio_response_api(sample_portfolio_config_api):
    """Sample portfolio response for API testing."""
    return {
        "config": sample_portfolio_config_api,
        "state": {
            "cash": 2500.0,
            "holdings": [
                {
                    "symbol": "AAPL",
                    "quantity": 10,
                    "avg_cost": 150.0,
                    "current_price": 155.0
                }
            ],
            "total_value": 12500.0,
            "last_updated": datetime.now().isoformat()
        }
    }


@pytest.fixture
def sample_agent_request_api():
    """Sample agent execution request for API testing."""
    return {
        "portfolio_name": "test_portfolio",
        "user_context": "Focus on growth stocks"
    }


@pytest.fixture
def sample_agent_response_api():
    """Sample agent execution response for API testing."""
    try:
        from backend.models.agent import AgentExecuteResponse, TradeRecommendation
        return AgentExecuteResponse(
            success=True,
            recommendations=[
                TradeRecommendation(
                    action="buy",
                    symbol="MSFT", 
                    quantity=5,
                    price=300.0,
                    reasoning="Strong cloud growth prospects"
                )
            ],
            execution_time_ms=2500,
            total_tokens=150
        )
    except ImportError:
        return None


@pytest.fixture
def mock_portfolio_service():
    """Mock portfolio API service."""
    mock = MagicMock()
    mock.list_portfolios = MagicMock()
    mock.get_portfolio = MagicMock()
    mock.create_portfolio = MagicMock()
    mock.update_portfolio = MagicMock()
    mock.delete_portfolio = MagicMock()
    return mock


@pytest.fixture
def mock_agent_service():
    """Mock agent API service."""
    mock = MagicMock()
    mock.execute_agent = AsyncMock()
    return mock


@pytest.fixture
def mock_execution_log_service():
    """Mock execution log service."""
    mock = MagicMock()
    mock.get_recent_logs = MagicMock()
    return mock

