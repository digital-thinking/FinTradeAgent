"""Tests for ComparisonService."""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from fin_trade.models import AssetClass, Holding, PortfolioConfig, PortfolioState, Trade
from fin_trade.services.comparison import ComparisonService, PortfolioMetrics


@pytest.fixture
def mock_portfolio_service():
    """Create a mock PortfolioService."""
    return MagicMock()


@pytest.fixture
def mock_stock_data_service():
    """Create a mock StockDataService."""
    mock = MagicMock()
    mock.get_price.return_value = 100.0

    def get_closes(tickers, start, end):
        dates = pd.date_range(
            start=pd.Timestamp(start).normalize(),
            end=pd.Timestamp(end).normalize(),
            freq="D",
        )
        return pd.DataFrame(
            {ticker.upper(): [mock.get_price.return_value] * len(dates) for ticker in tickers},
            index=dates,
        )

    mock.get_closes.side_effect = get_closes
    return mock


@pytest.fixture
def comparison_service(mock_portfolio_service, mock_stock_data_service):
    """Create a ComparisonService with mocked dependencies."""
    return ComparisonService(
        portfolio_service=mock_portfolio_service,
        stock_data_service=mock_stock_data_service,
    )


@pytest.fixture
def sample_config():
    """Sample portfolio config."""
    return PortfolioConfig(
        name="Test Portfolio",
        strategy_prompt="Test strategy",
        initial_amount=10000.0,
        num_initial_trades=5,
        trades_per_run=3,
        run_frequency="weekly",
        llm_provider="openai",
        llm_model="gpt-4o",
    )


@pytest.fixture
def sample_trades():
    """Sample trade history with profits and losses."""
    base_date = datetime.now() - timedelta(days=30)
    return [
        Trade(
            timestamp=base_date,
            ticker="AAPL",
            name="Apple Inc.",
            action="BUY",
            quantity=10,
            price=150.0,
            reasoning="Test buy",
        ),
        Trade(
            timestamp=base_date + timedelta(days=10),
            ticker="AAPL",
            name="Apple Inc.",
            action="SELL",
            quantity=5,
            price=160.0,  # Profit
            reasoning="Taking profits",
        ),
        Trade(
            timestamp=base_date + timedelta(days=15),
            ticker="MSFT",
            name="Microsoft Corp.",
            action="BUY",
            quantity=5,
            price=300.0,
            reasoning="Test buy",
        ),
        Trade(
            timestamp=base_date + timedelta(days=20),
            ticker="MSFT",
            name="Microsoft Corp.",
            action="SELL",
            quantity=5,
            price=280.0,  # Loss
            reasoning="Stop loss",
        ),
    ]


class TestCalculateMetricsNoTrades:
    """Tests for calculate_metrics with no trades."""

    def test_returns_zero_metrics_for_empty_portfolio(
        self, comparison_service, mock_portfolio_service, sample_config
    ):
        """Test returns zero metrics when no trades exist."""
        empty_state = PortfolioState(cash=10000.0, trades=[], holdings=[])
        mock_portfolio_service.load_portfolio.return_value = (sample_config, empty_state)

        metrics = comparison_service.calculate_metrics("test")

        assert metrics.total_return_pct == 0.0
        assert metrics.max_drawdown_pct == 0.0
        assert metrics.num_trades == 0
        assert metrics.days_active == 0
        assert metrics.win_rate_pct is None
        assert metrics.sharpe_ratio is None


class TestCalculateMetricsWithTrades:
    """Tests for calculate_metrics with trades."""

    def test_calculates_total_return(
        self, comparison_service, mock_portfolio_service, mock_stock_data_service,
        sample_config, sample_trades
    ):
        """Test calculates total return correctly."""
        # After trades: bought AAPL 10@150=1500, sold 5@160=800
        # Bought MSFT 5@300=1500, sold 5@280=1400
        # Net: -1500+800-1500+1400 = -800 from trades
        # Plus remaining 5 AAPL shares worth 5*100=500 (mock price)
        # Cash: 10000 - 1500 + 800 - 1500 + 1400 = 9200
        # Total: 9200 + 500 = 9700

        state = PortfolioState(
            cash=9200.0,
            trades=sample_trades,
            holdings=[Holding(ticker="AAPL", name="Apple Inc.", quantity=5, avg_price=150.0)],
            initial_investment=10000.0,
        )
        mock_portfolio_service.load_portfolio.return_value = (sample_config, state)
        mock_stock_data_service.get_price.return_value = 100.0

        # Mock benchmark data
        mock_stock_data_service.get_benchmark_performance.return_value = pd.DataFrame({
            "date": [datetime.now() - timedelta(days=30), datetime.now()],
            "price": [400.0, 420.0],
            "cumulative_return": [0.0, 5.0],
        })

        metrics = comparison_service.calculate_metrics("test")

        assert metrics.num_trades == 4
        assert metrics.days_active >= 20  # At least 20 days from first to last trade

    def test_calculates_win_rate(
        self, comparison_service, mock_portfolio_service, mock_stock_data_service,
        sample_config, sample_trades
    ):
        """Test win rate calculation (1 profitable, 1 losing trade)."""
        state = PortfolioState(
            cash=9200.0,
            trades=sample_trades,
            holdings=[Holding(ticker="AAPL", name="Apple Inc.", quantity=5, avg_price=150.0)],
            initial_investment=10000.0,
        )
        mock_portfolio_service.load_portfolio.return_value = (sample_config, state)
        mock_stock_data_service.get_benchmark_performance.return_value = pd.DataFrame({
            "date": [datetime.now()],
            "price": [400.0],
            "cumulative_return": [0.0],
        })

        metrics = comparison_service.calculate_metrics("test")

        # 1 profitable AAPL sell (160 > 150), 1 losing MSFT sell (280 < 300)
        assert metrics.win_rate_pct == 50.0


class TestBuildPortfolioValueSeries:
    """Tests for historical portfolio value reconstruction."""

    def test_marks_holdings_to_market_each_day(
        self, comparison_service, mock_portfolio_service, mock_stock_data_service,
        sample_config
    ):
        """Value reflects daily closes instead of the original cost basis."""
        trade_date = (datetime.now() - timedelta(days=5)).replace(
            hour=10, minute=0, second=0, microsecond=0
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
        mock_portfolio_service.load_portfolio.return_value = (sample_config, state)

        def rising_closes(tickers, start, end):
            dates = pd.date_range(
                start=pd.Timestamp(start).normalize(),
                end=pd.Timestamp(end).normalize(),
                freq="D",
            )
            closes = [100.0 + (10.0 * i / (len(dates) - 1)) for i in range(len(dates))]
            return pd.DataFrame({"AAPL": closes}, index=dates)

        mock_stock_data_service.get_closes.side_effect = rising_closes

        result = comparison_service._build_portfolio_value_series("test")

        assert len(result) == 6
        assert result["value"].iloc[-1] == pytest.approx(10100.0)


class TestWinRateCalculation:
    """Tests for _calculate_win_rate method."""

    def test_win_rate_all_winners(self, comparison_service):
        """Test 100% win rate."""
        trades = [
            Trade(
                timestamp=datetime.now() - timedelta(days=10),
                ticker="AAPL", name="Apple", action="BUY",
                quantity=10, price=100.0, reasoning="Buy",
            ),
            Trade(
                timestamp=datetime.now(),
                ticker="AAPL", name="Apple", action="SELL",
                quantity=10, price=110.0, reasoning="Sell",  # Winner
            ),
        ]
        win_rate = comparison_service._calculate_win_rate(trades)
        assert win_rate == 100.0

    def test_win_rate_all_losers(self, comparison_service):
        """Test 0% win rate."""
        trades = [
            Trade(
                timestamp=datetime.now() - timedelta(days=10),
                ticker="AAPL", name="Apple", action="BUY",
                quantity=10, price=100.0, reasoning="Buy",
            ),
            Trade(
                timestamp=datetime.now(),
                ticker="AAPL", name="Apple", action="SELL",
                quantity=10, price=90.0, reasoning="Sell",  # Loser
            ),
        ]
        win_rate = comparison_service._calculate_win_rate(trades)
        assert win_rate == 0.0

    def test_win_rate_no_closed_positions(self, comparison_service):
        """Test returns None when no positions have been closed."""
        trades = [
            Trade(
                timestamp=datetime.now(),
                ticker="AAPL", name="Apple", action="BUY",
                quantity=10, price=100.0, reasoning="Buy",
            ),
        ]
        win_rate = comparison_service._calculate_win_rate(trades)
        assert win_rate is None

    def test_win_rate_empty_trades(self, comparison_service):
        """Test returns None for empty trades list."""
        win_rate = comparison_service._calculate_win_rate([])
        assert win_rate is None


class TestMaxDrawdownCalculation:
    """Tests for _calculate_max_drawdown method."""

    def test_no_drawdown(self, comparison_service):
        """Test when values only increase."""
        values = [100, 110, 120, 130]
        max_dd = comparison_service._calculate_max_drawdown(values)
        assert max_dd == 0.0

    def test_simple_drawdown(self, comparison_service):
        """Test simple drawdown calculation."""
        values = [100, 120, 100, 110]  # Peak 120, trough 100 = 16.67% drawdown
        max_dd = comparison_service._calculate_max_drawdown(values)
        assert abs(max_dd - 16.67) < 0.1

    def test_multiple_drawdowns(self, comparison_service):
        """Test finds the maximum of multiple drawdowns."""
        values = [100, 110, 100, 120, 90]  # Second drawdown is larger (25%)
        max_dd = comparison_service._calculate_max_drawdown(values)
        assert abs(max_dd - 25.0) < 0.1

    def test_empty_values(self, comparison_service):
        """Test returns 0 for empty values."""
        max_dd = comparison_service._calculate_max_drawdown([])
        assert max_dd == 0.0

    def test_single_value(self, comparison_service):
        """Test returns 0 for single value."""
        max_dd = comparison_service._calculate_max_drawdown([100])
        assert max_dd == 0.0


class TestGetNormalizedReturns:
    """Tests for get_normalized_returns method."""

    def test_returns_empty_dataframe_for_no_portfolios(
        self, comparison_service, mock_portfolio_service, sample_config
    ):
        """Test returns empty DataFrame when no portfolios have trades."""
        empty_state = PortfolioState(cash=10000.0, trades=[], holdings=[])
        mock_portfolio_service.load_portfolio.return_value = (sample_config, empty_state)

        result = comparison_service.get_normalized_returns(["test"])

        assert result.empty

    def test_includes_benchmark_when_requested(
        self, comparison_service, mock_portfolio_service, mock_stock_data_service,
        sample_config, sample_trades
    ):
        """Test includes benchmark column when include_benchmark=True."""
        state = PortfolioState(
            cash=9200.0,
            trades=sample_trades,
            holdings=[],
            initial_investment=10000.0,
        )
        mock_portfolio_service.load_portfolio.return_value = (sample_config, state)
        mock_stock_data_service.get_benchmark_performance.return_value = pd.DataFrame({
            "date": pd.date_range(start=datetime.now() - timedelta(days=30), periods=30, freq="D"),
            "price": [400.0 + i for i in range(30)],
            "cumulative_return": [i * 0.1 for i in range(30)],
        })

        result = comparison_service.get_normalized_returns(
            ["test"], include_benchmark=True, benchmark_symbol="SPY"
        )

        assert "SPY_benchmark" in result.columns


class TestGetComparisonTable:
    """Tests for get_comparison_table method."""

    def test_returns_dataframe_with_metrics(
        self, comparison_service, mock_portfolio_service, mock_stock_data_service,
        sample_config, sample_trades
    ):
        """Test returns DataFrame with all metrics."""
        state = PortfolioState(
            cash=9200.0,
            trades=sample_trades,
            holdings=[Holding(ticker="AAPL", name="Apple", quantity=5, avg_price=150.0)],
            initial_investment=10000.0,
        )
        mock_portfolio_service.load_portfolio.return_value = (sample_config, state)
        mock_stock_data_service.get_benchmark_performance.return_value = pd.DataFrame({
            "date": [datetime.now() - timedelta(days=30), datetime.now()],
            "price": [400.0, 420.0],
            "cumulative_return": [0.0, 5.0],
        })

        result = comparison_service.get_comparison_table(["test"])

        assert "test" in result.columns
        assert "Total Return" in result.index
        assert "Sharpe Ratio" in result.index
        assert "Max Drawdown" in result.index
        assert "Win Rate" in result.index


class TestPortfolioMetricsDataclass:
    """Tests for PortfolioMetrics dataclass."""

    def test_all_fields_set(self):
        """Test all fields can be set."""
        metrics = PortfolioMetrics(
            total_return_pct=15.5,
            annualized_return_pct=12.3,
            volatility_pct=18.5,
            sharpe_ratio=0.85,
            max_drawdown_pct=10.2,
            win_rate_pct=65.0,
            alpha_pct=3.5,
            beta=1.1,
            days_active=180,
            num_trades=25,
        )

        assert metrics.total_return_pct == 15.5
        assert metrics.annualized_return_pct == 12.3
        assert metrics.volatility_pct == 18.5
        assert metrics.sharpe_ratio == 0.85
        assert metrics.max_drawdown_pct == 10.2
        assert metrics.win_rate_pct == 65.0
        assert metrics.alpha_pct == 3.5
        assert metrics.beta == 1.1
        assert metrics.days_active == 180
        assert metrics.num_trades == 25

    def test_optional_fields_can_be_none(self):
        """Test optional fields accept None."""
        metrics = PortfolioMetrics(
            total_return_pct=0.0,
            annualized_return_pct=None,
            volatility_pct=None,
            sharpe_ratio=None,
            max_drawdown_pct=0.0,
            win_rate_pct=None,
            alpha_pct=None,
            beta=None,
            days_active=0,
            num_trades=0,
        )

        assert metrics.annualized_return_pct is None
        assert metrics.sharpe_ratio is None
        assert metrics.win_rate_pct is None


class TestDefaultBenchmark:
    """Tests for asset-class default benchmark selection."""

    def test_returns_spy_for_stocks(self, comparison_service):
        assert comparison_service.get_default_benchmark(AssetClass.STOCKS) == "SPY"

    def test_returns_btc_for_crypto(self, comparison_service):
        assert comparison_service.get_default_benchmark(AssetClass.CRYPTO) == "BTC-USD"
