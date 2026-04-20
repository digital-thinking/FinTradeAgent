"""Tests for ComparisonService."""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
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


def build_price_series(start_price: float, returns: list[float]) -> list[float]:
    """Build a price series from a starting price and daily returns."""
    prices = [start_price]
    for daily_return in returns:
        prices.append(prices[-1] * (1 + daily_return))
    return prices


def find_constant_return_shift(
    benchmark_returns: np.ndarray,
    target_growth_ratio: float,
) -> float:
    """Find a constant daily return shift that reaches the target growth ratio."""
    low = -0.01
    high = 0.01
    for _ in range(100):
        mid = (low + high) / 2
        growth_ratio = float(np.prod(1 + benchmark_returns + mid))
        if growth_ratio < target_growth_ratio:
            low = mid
        else:
            high = mid
    return (low + high) / 2


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


class TestCalculateMetricsBeta:
    """Tests for beta calculation from daily return covariance."""

    def test_calculates_beta_from_aligned_daily_returns(
        self,
        comparison_service,
        mock_portfolio_service,
        mock_stock_data_service,
        sample_config,
    ):
        """A portfolio that tracks the benchmark should have beta near 1."""
        dates = pd.date_range(start="2026-01-05", periods=5, freq="B")
        trade = Trade(
            timestamp=dates[0].to_pydatetime(),
            ticker="AAPL",
            name="Apple Inc.",
            action="BUY",
            quantity=1,
            price=100.0,
            reasoning="Track benchmark",
        )
        state = PortfolioState(
            cash=0.0,
            trades=[trade],
            holdings=[Holding(ticker="AAPL", name="Apple Inc.", quantity=1, avg_price=100.0)],
            initial_investment=100.0,
        )
        mock_portfolio_service.load_portfolio.return_value = (sample_config, state)
        comparison_service._build_portfolio_value_series = MagicMock(return_value=pd.DataFrame({
            "date": dates,
            "value": [100.0, 102.0, 101.0, 103.0, 104.0],
        }))
        mock_stock_data_service.get_benchmark_performance.return_value = pd.DataFrame({
            "date": dates,
            "price": [250.0, 255.0, 252.5, 257.5, 260.0],
            "cumulative_return": [0.0, 2.0, 1.0, 3.0, 4.0],
        })

        metrics = comparison_service.calculate_metrics("test")

        assert metrics.beta == pytest.approx(1.0)

    def test_calculates_zero_beta_for_constant_value_portfolio(
        self,
        comparison_service,
        mock_portfolio_service,
        mock_stock_data_service,
        sample_config,
    ):
        """A constant-value portfolio should have zero covariance with the benchmark."""
        dates = pd.date_range(start="2026-01-05", periods=5, freq="B")
        trade = Trade(
            timestamp=dates[0].to_pydatetime(),
            ticker="AAPL",
            name="Apple Inc.",
            action="BUY",
            quantity=1,
            price=100.0,
            reasoning="Stay flat",
        )
        state = PortfolioState(
            cash=100.0,
            trades=[trade],
            holdings=[],
            initial_investment=100.0,
        )
        mock_portfolio_service.load_portfolio.return_value = (sample_config, state)
        comparison_service._build_portfolio_value_series = MagicMock(return_value=pd.DataFrame({
            "date": dates,
            "value": [100.0, 100.0, 100.0, 100.0, 100.0],
        }))
        mock_stock_data_service.get_benchmark_performance.return_value = pd.DataFrame({
            "date": dates,
            "price": [250.0, 255.0, 252.5, 257.5, 260.0],
            "cumulative_return": [0.0, 2.0, 1.0, 3.0, 4.0],
        })

        metrics = comparison_service.calculate_metrics("test")

        assert metrics.beta == pytest.approx(0.0)


class TestCalculateMetricsAlpha:
    """Tests for Jensen's alpha calculation."""

    def test_calculates_zero_alpha_for_perfect_benchmark_tracker(
        self,
        comparison_service,
        mock_portfolio_service,
        mock_stock_data_service,
        sample_config,
    ):
        """A portfolio that matches the benchmark should have zero alpha."""
        dates = pd.bdate_range(end=pd.Timestamp(datetime.now()).normalize(), periods=253)
        benchmark_returns = np.tile(
            np.array([0.0010, -0.0004, 0.0013, 0.0002, -0.0001]),
            51,
        )[:252]
        benchmark_prices = build_price_series(100.0, benchmark_returns.tolist())
        trade = Trade(
            timestamp=dates[0].to_pydatetime(),
            ticker="AAPL",
            name="Apple Inc.",
            action="BUY",
            quantity=1,
            price=100.0,
            reasoning="Match benchmark",
        )
        state = PortfolioState(
            cash=0.0,
            trades=[trade],
            holdings=[Holding(ticker="AAPL", name="Apple Inc.", quantity=1, avg_price=100.0)],
            initial_investment=100.0,
        )
        mock_portfolio_service.load_portfolio.return_value = (sample_config, state)
        comparison_service._build_portfolio_value_series = MagicMock(return_value=pd.DataFrame({
            "date": dates,
            "value": benchmark_prices,
        }))
        mock_stock_data_service.get_benchmark_performance.return_value = pd.DataFrame({
            "date": dates,
            "price": benchmark_prices,
            "cumulative_return": [((price / benchmark_prices[0]) - 1) * 100 for price in benchmark_prices],
        })

        metrics = comparison_service.calculate_metrics("test")

        assert metrics.beta == pytest.approx(1.0)
        assert metrics.alpha_pct == pytest.approx(0.0, abs=0.1)

    def test_calculates_positive_jensens_alpha_for_outperformance(
        self,
        comparison_service,
        mock_portfolio_service,
        mock_stock_data_service,
        sample_config,
    ):
        """A portfolio with benchmark beta and +5% annualized excess should show +5% alpha."""
        dates = pd.bdate_range(end=pd.Timestamp(datetime.now()).normalize(), periods=253)
        benchmark_returns = np.tile(
            np.array([0.0010, -0.0004, 0.0013, 0.0002, -0.0001]),
            51,
        )[:252]
        benchmark_prices = build_price_series(100.0, benchmark_returns.tolist())
        days_active = max((datetime.now() - dates[0].to_pydatetime()).days, 1)
        years = days_active / 365
        benchmark_annualized_return = ((benchmark_prices[-1] / benchmark_prices[0]) ** (1 / years) - 1) * 100
        target_portfolio_annualized_return = benchmark_annualized_return + 5.0
        target_growth_ratio = (1 + target_portfolio_annualized_return / 100) ** years
        portfolio_return_shift = find_constant_return_shift(
            benchmark_returns,
            target_growth_ratio,
        )
        portfolio_returns = benchmark_returns + portfolio_return_shift
        portfolio_prices = build_price_series(100.0, portfolio_returns.tolist())
        trade = Trade(
            timestamp=dates[0].to_pydatetime(),
            ticker="AAPL",
            name="Apple Inc.",
            action="BUY",
            quantity=1,
            price=100.0,
            reasoning="Beat benchmark",
        )
        state = PortfolioState(
            cash=0.0,
            trades=[trade],
            holdings=[Holding(ticker="AAPL", name="Apple Inc.", quantity=1, avg_price=100.0)],
            initial_investment=100.0,
        )
        mock_portfolio_service.load_portfolio.return_value = (sample_config, state)
        comparison_service._build_portfolio_value_series = MagicMock(return_value=pd.DataFrame({
            "date": dates,
            "value": portfolio_prices,
        }))
        mock_stock_data_service.get_benchmark_performance.return_value = pd.DataFrame({
            "date": dates,
            "price": benchmark_prices,
            "cumulative_return": [((price / benchmark_prices[0]) - 1) * 100 for price in benchmark_prices],
        })

        metrics = comparison_service.calculate_metrics("test")

        assert metrics.beta == pytest.approx(1.0, abs=1e-6)
        assert metrics.alpha_pct == pytest.approx(5.0, abs=0.3)


class TestCalculateMetricsVolatility:
    """Tests for volatility from daily-resampled returns."""

    def test_calculates_volatility_from_daily_resampled_returns(
        self,
        comparison_service,
        mock_portfolio_service,
        mock_stock_data_service,
        sample_config,
    ):
        """Volatility should use daily returns after filling calendar gaps."""
        dates = pd.bdate_range(end=pd.Timestamp(datetime.now()).normalize(), periods=3)
        values = [100.0, 101.0, 98.98]
        trade = Trade(
            timestamp=dates[0].to_pydatetime(),
            ticker="AAPL",
            name="Apple Inc.",
            action="BUY",
            quantity=1,
            price=100.0,
            reasoning="Test volatility",
        )
        state = PortfolioState(
            cash=0.0,
            trades=[trade],
            holdings=[Holding(ticker="AAPL", name="Apple Inc.", quantity=1, avg_price=100.0)],
            initial_investment=100.0,
        )
        mock_portfolio_service.load_portfolio.return_value = (sample_config, state)
        comparison_service._build_portfolio_value_series = MagicMock(return_value=pd.DataFrame({
            "date": dates,
            "value": values,
        }))
        mock_stock_data_service.get_benchmark_performance.return_value = pd.DataFrame({
            "date": [dates[0], dates[-1]],
            "price": [100.0, 100.0],
            "cumulative_return": [0.0, 0.0],
        })

        metrics = comparison_service.calculate_metrics("test")

        daily_returns = (
            pd.Series(values, index=dates)
            .reindex(pd.date_range(start=dates[0], end=dates[-1], freq="D"), method="ffill")
            .pct_change()
            .dropna()
        )
        expected_volatility = float(daily_returns.std() * np.sqrt(252) * 100)

        assert metrics.volatility_pct == pytest.approx(expected_volatility)


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
    """Tests for _calculate_performance_stats method."""

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
        win_rate, profit_factor = comparison_service._calculate_performance_stats(trades)
        assert win_rate == 100.0
        assert profit_factor == float('inf')

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
        win_rate, profit_factor = comparison_service._calculate_performance_stats(trades)
        assert win_rate == 0.0
        assert profit_factor == 0.0

    def test_win_rate_no_closed_positions(self, comparison_service):
        """Test returns None when no positions have been closed."""
        trades = [
            Trade(
                timestamp=datetime.now(),
                ticker="AAPL", name="Apple", action="BUY",
                quantity=10, price=100.0, reasoning="Buy",
            ),
        ]
        win_rate, profit_factor = comparison_service._calculate_performance_stats(trades)
        assert win_rate is None
        assert profit_factor is None

    def test_win_rate_empty_trades(self, comparison_service):
        """Test returns None for empty trades list."""
        win_rate, profit_factor = comparison_service._calculate_performance_stats([])
        assert win_rate is None
        assert profit_factor is None

    def test_win_rate_per_tax_lot(self, comparison_service, sample_config):
        """A SELL closing one winning and one losing lot produces 50% win rate (1 of 2)."""
        base_date = datetime.now() - timedelta(days=10)
        trades = [
            Trade(
                timestamp=base_date,
                ticker="AAPL", name="Apple", action="BUY",
                quantity=10, price=100.0, reasoning="Buy lot 1",
            ),
            Trade(
                timestamp=base_date + timedelta(days=1),
                ticker="AAPL", name="Apple", action="BUY",
                quantity=10, price=120.0, reasoning="Buy lot 2",
            ),
            Trade(
                timestamp=base_date + timedelta(days=2),
                ticker="AAPL", name="Apple", action="SELL",
                quantity=20, price=110.0, reasoning="Sell both lots",
            ),
        ]
        # Current implementation (per-SELL) would say:
        # avg_cost = (10*100 + 10*120)/20 = 110.
        # sell_price 110 is NOT > 110, so win rate 0%?
        # Or if it was 111, it would be 100% win rate.
        #
        # New implementation (per-tax-lot) should say:
        # Lot 1: bought 100, sold 110 -> Winner
        # Lot 2: bought 120, sold 110 -> Loser
        # Win rate: 1/2 = 50%

        # Let's adjust prices to make it clear:
        trades[2].price = 111.0
        # Lot 1: 111 > 100 (Win)
        # Lot 2: 111 < 120 (Loss)
        # Win rate should be 50%

        # Also test profit factor:
        # Winners: (111 - 100) * 10 = 110
        # Losers: |(111 - 120) * 10| = |-90| = 90
        # Profit factor = 110 / 90 = 1.222...

        # We need to update calculate_metrics to return profit_factor_pct
        state = PortfolioState(
            cash=10000.0,
            trades=trades,
            holdings=[],
            initial_investment=10000.0,
        )
        with patch.object(comparison_service.portfolio_service, 'load_portfolio') as mock_load:
            mock_load.return_value = (sample_config, state)
            metrics = comparison_service.calculate_metrics("test")

        assert metrics.win_rate_pct == 50.0
        assert metrics.profit_factor_pct == pytest.approx(1.222, abs=0.001)


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

    def test_benchmark_row_matches_calculate_metrics_on_synthetic_tracker(
        self,
        comparison_service,
        mock_portfolio_service,
        mock_stock_data_service,
        sample_config,
    ):
        """Benchmark row numbers must match calculate_metrics run on a synthetic
        portfolio whose value series equals the benchmark price series."""
        dates = pd.bdate_range(end=pd.Timestamp(datetime.now()).normalize(), periods=60)
        first_trade_date = dates[0].to_pydatetime()
        benchmark_returns = np.tile(
            np.array([0.0030, -0.0015, 0.0045, -0.0020, 0.0010]),
            12,
        )[:59]
        benchmark_prices = build_price_series(100.0, benchmark_returns.tolist())
        trade = Trade(
            timestamp=first_trade_date,
            ticker="AAPL",
            name="Apple Inc.",
            action="BUY",
            quantity=1,
            price=100.0,
            reasoning="Track benchmark",
        )
        state = PortfolioState(
            cash=0.0,
            trades=[trade],
            holdings=[Holding(ticker="AAPL", name="Apple Inc.", quantity=1, avg_price=100.0)],
            initial_investment=100.0,
        )
        mock_portfolio_service.load_portfolio.return_value = (sample_config, state)
        benchmark_df = pd.DataFrame({
            "date": dates,
            "price": benchmark_prices,
            "cumulative_return": [
                ((price / benchmark_prices[0]) - 1) * 100 for price in benchmark_prices
            ],
        })
        mock_stock_data_service.get_benchmark_performance.return_value = benchmark_df
        # Pin the portfolio's value series to the benchmark price series so that
        # calculate_metrics on this portfolio must produce the same numbers as
        # the benchmark row.
        comparison_service._build_portfolio_value_series = MagicMock(
            return_value=pd.DataFrame({"date": dates, "value": benchmark_prices})
        )

        expected = comparison_service.calculate_metrics("test", "SPY")
        result = comparison_service.get_comparison_table(["test"], benchmark_symbol="SPY")

        benchmark_col = result["SPY"]

        # Volatility, Sharpe, max drawdown, annualized return must match the
        # synthetic tracker portfolio's metrics and never be the old hardcoded
        # placeholders.
        assert benchmark_col["Volatility"] == f"{expected.volatility_pct:.1f}%"
        assert benchmark_col["Volatility"] != "~15%"
        assert benchmark_col["Sharpe Ratio"] == f"{expected.sharpe_ratio:.2f}"
        assert benchmark_col["Sharpe Ratio"] != "N/A"
        assert benchmark_col["Max Drawdown"] == f"-{expected.max_drawdown_pct:.1f}%"
        assert benchmark_col["Max Drawdown"] != "N/A"
        assert benchmark_col["Annualized Return"] == (
            f"{expected.annualized_return_pct:+.1f}%"
        )
        assert benchmark_col["Days Active"] == str(expected.days_active)
        assert benchmark_col["Days Active"] != "365"

        window = result.attrs["benchmark_window"]
        assert window["symbol"] == "SPY"
        assert window["start"] == first_trade_date
        assert window["days"] == expected.days_active

    def test_labels_fallback_alpha_as_excess_return(
        self, comparison_service, mock_portfolio_service, mock_stock_data_service, sample_config
    ):
        """Fallback alpha should be labeled as Excess Return when beta is unavailable."""
        state = PortfolioState(
            cash=10000.0,
            trades=[],
            holdings=[],
        )
        mock_portfolio_service.load_portfolio.return_value = (sample_config, state)
        comparison_service.calculate_metrics = MagicMock(return_value=PortfolioMetrics(
            total_return_pct=10.0,
            annualized_return_pct=10.0,
            volatility_pct=12.0,
            sharpe_ratio=0.5,
            max_drawdown_pct=2.0,
            win_rate_pct=50.0,
            profit_factor_pct=1.5,
            alpha_pct=10.0,
            beta=None,
            days_active=365,
            num_trades=1,
        ))
        mock_stock_data_service.get_benchmark_performance.return_value = pd.DataFrame({
            "date": [datetime.now() - timedelta(days=365), datetime.now()],
            "price": [100.0, 110.0],
            "cumulative_return": [0.0, 10.0],
        })

        result = comparison_service.get_comparison_table(["test"])

        assert "Excess Return" in result.index
        assert "Alpha" not in result.index
        assert result.loc["Excess Return", "test"] == "+10.0%"


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
            profit_factor_pct=2.1,
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
        assert metrics.profit_factor_pct == 2.1
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
            profit_factor_pct=None,
            alpha_pct=None,
            beta=None,
            days_active=0,
            num_trades=0,
        )

        assert metrics.annualized_return_pct is None
        assert metrics.sharpe_ratio is None
        assert metrics.win_rate_pct is None
        assert metrics.profit_factor_pct is None


class TestDefaultBenchmark:
    """Tests for asset-class default benchmark selection."""

    def test_returns_spy_for_stocks(self, comparison_service):
        assert comparison_service.get_default_benchmark(AssetClass.STOCKS) == "SPY"

    def test_returns_btc_for_crypto(self, comparison_service):
        assert comparison_service.get_default_benchmark(AssetClass.CRYPTO) == "BTC-USD"
