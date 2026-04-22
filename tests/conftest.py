"""Shared fixtures and mocks for tests."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from fin_trade.models import (
    AssetClass,
    Holding,
    Trade,
    PortfolioConfig,
    PortfolioState,
    TradeRecommendation,
    AgentRecommendation,
)
from fin_trade.services.security import Security
from fin_trade.services.stock_data import PriceContext


@pytest.fixture(autouse=True)
def _identity_fx_service():
    """Replace FxService with an identity stub for all tests.

    Any PortfolioService instantiated without an explicit fx_service would
    otherwise spin up a real FxService, hitting yfinance and the on-disk
    cache. Tests that genuinely exercise FX should patch fin_trade.services.fx
    themselves.
    """
    stub = MagicMock()
    stub.return_value.get_rate.return_value = 1.0
    stub.return_value.convert.side_effect = (
        lambda amount, from_ccy=None, to_ccy=None, at=None: amount
    )
    with patch("fin_trade.services.portfolio.FxService", stub):
        yield stub


@pytest.fixture
def mock_security_service():
    """Create a mock SecurityService."""
    mock = MagicMock()

    # Default price lookup
    mock.get_price.return_value = 100.0
    mock.force_update_price.return_value = 100.0

    # Default listing currency — tests that care about FX can override
    mock.get_currency.return_value = "USD"

    # Default fundamentals-derived fields — return None so market_data short-circuits
    mock.get_earnings_timestamp.return_value = None
    mock.get_52w_range.return_value = None
    mock.get_moving_averages.return_value = None
    mock.get_short_interest.return_value = None
    mock.get_analyst_data.return_value = None
    mock.get_volume_data.return_value = None
    mock.get_valuation_metrics.return_value = None

    # Default security lookup
    def lookup_ticker(ticker: str, fundamentals_ticker: str | None = None) -> Security:
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
def mock_fx_service():
    """Create a mock FxService that performs identity conversions.

    Returns 1.0 for any rate and passes amounts through unchanged — keeps
    unit tests independent of yfinance and the on-disk FX cache.
    """
    mock = MagicMock()
    mock.get_rate.return_value = 1.0
    mock.convert.side_effect = lambda amount, from_ccy=None, to_ccy=None, at=None: amount
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

