"""Tests for ReflectionService."""

from datetime import datetime, timedelta

import pytest

from fin_trade.models import PortfolioState, Trade
from fin_trade.services.reflection import (
    BiasAnalysis,
    CompletedTrade,
    ReflectionResult,
    ReflectionService,
    TradeMetrics,
)


class TestCompletedTrade:
    """Tests for CompletedTrade dataclass."""

    def test_completed_trade_winner(self):
        """Test creating a winning trade."""
        trade = CompletedTrade(
            ticker="AAPL",
            name="Apple Inc.",
            buy_date=datetime(2025, 1, 1),
            sell_date=datetime(2025, 1, 15),
            buy_price=150.0,
            sell_price=165.0,
            quantity=10,
            buy_reasoning="Growth opportunity",
            sell_reasoning="Target reached",
            holding_days=14,
            profit_loss=150.0,
            return_pct=10.0,
            is_winner=True,
        )

        assert trade.is_winner is True
        assert trade.return_pct == 10.0
        assert trade.holding_days == 14

    def test_completed_trade_loser(self):
        """Test creating a losing trade."""
        trade = CompletedTrade(
            ticker="MSFT",
            name="Microsoft Corp.",
            buy_date=datetime(2025, 1, 1),
            sell_date=datetime(2025, 1, 10),
            buy_price=400.0,
            sell_price=380.0,
            quantity=5,
            buy_reasoning="Value play",
            sell_reasoning="Stop loss hit",
            holding_days=9,
            profit_loss=-100.0,
            return_pct=-5.0,
            is_winner=False,
        )

        assert trade.is_winner is False
        assert trade.return_pct == -5.0


class TestReflectionResult:
    """Tests for ReflectionResult dataclass."""

    def test_to_context_string_no_trades(self):
        """Test context string with no completed trades."""
        result = ReflectionResult(
            metrics=TradeMetrics(
                total_completed_trades=0,
                winners=0,
                losers=0,
                win_rate=0.0,
                avg_gain_pct=0.0,
                avg_loss_pct=0.0,
                avg_holding_days=0.0,
                total_realized_profit=0.0,
                best_trade=None,
                worst_trade=None,
                avg_winner_holding_days=0.0,
                avg_loser_holding_days=0.0,
            ),
            bias_analysis=BiasAnalysis(),
            completed_trades=[],
            insights=[],
        )

        context = result.to_context_string()

        assert "No completed trade cycles" in context

    def test_to_context_string_with_trades(self):
        """Test context string with completed trades."""
        best_trade = CompletedTrade(
            ticker="NVDA",
            name="NVIDIA",
            buy_date=datetime(2025, 1, 1),
            sell_date=datetime(2025, 1, 20),
            buy_price=500.0,
            sell_price=600.0,
            quantity=5,
            buy_reasoning="AI growth opportunity",
            sell_reasoning="Target reached",
            holding_days=19,
            profit_loss=500.0,
            return_pct=20.0,
            is_winner=True,
        )

        worst_trade = CompletedTrade(
            ticker="META",
            name="Meta",
            buy_date=datetime(2025, 1, 5),
            sell_date=datetime(2025, 1, 12),
            buy_price=350.0,
            sell_price=315.0,
            quantity=3,
            buy_reasoning="Social media dominance",
            sell_reasoning="Cut losses",
            holding_days=7,
            profit_loss=-105.0,
            return_pct=-10.0,
            is_winner=False,
        )

        result = ReflectionResult(
            metrics=TradeMetrics(
                total_completed_trades=5,
                winners=3,
                losers=2,
                win_rate=60.0,
                avg_gain_pct=15.0,
                avg_loss_pct=-8.0,
                avg_holding_days=14.0,
                total_realized_profit=1500.0,
                best_trade=best_trade,
                worst_trade=worst_trade,
                avg_winner_holding_days=18.0,
                avg_loser_holding_days=8.0,
            ),
            bias_analysis=BiasAnalysis(warnings=["Low win rate"]),
            completed_trades=[best_trade, worst_trade],
            insights=["Strong win rate", "Good risk/reward"],
        )

        context = result.to_context_string()

        assert "SELF-REFLECTION" in context
        assert "3W-2L" in context
        assert "60.0% win rate" in context
        assert "NVDA" in context
        assert "META" in context
        assert "KEY INSIGHTS" in context


class TestReflectionServiceInit:
    """Tests for ReflectionService initialization."""

    def test_creates_service(self):
        """Test service creation."""
        service = ReflectionService()
        assert service is not None


class TestFindCompletedTrades:
    """Tests for _find_completed_trades method."""

    def test_empty_trades_list(self):
        """Test with no trades."""
        service = ReflectionService()
        result = service._find_completed_trades([])
        assert result == []

    def test_only_buy_trades(self):
        """Test with only buy trades (no completed cycles)."""
        service = ReflectionService()
        trades = [
            Trade(
                timestamp=datetime(2025, 1, 1),
                isin="US0378331005",
                ticker="AAPL",
                name="Apple Inc.",
                action="BUY",
                quantity=10,
                price=150.0,
                reasoning="Growth opportunity",
            )
        ]
        result = service._find_completed_trades(trades)
        assert result == []

    def test_completed_trade_cycle(self):
        """Test detecting a completed BUY->SELL cycle."""
        service = ReflectionService()
        trades = [
            Trade(
                timestamp=datetime(2025, 1, 1),
                isin="US0378331005",
                ticker="AAPL",
                name="Apple Inc.",
                action="BUY",
                quantity=10,
                price=150.0,
                reasoning="Growth opportunity",
            ),
            Trade(
                timestamp=datetime(2025, 1, 15),
                isin="US0378331005",
                ticker="AAPL",
                name="Apple Inc.",
                action="SELL",
                quantity=10,
                price=165.0,
                reasoning="Target reached",
            ),
        ]

        result = service._find_completed_trades(trades)

        assert len(result) == 1
        assert result[0].ticker == "AAPL"
        assert result[0].return_pct == 10.0
        assert result[0].is_winner is True
        assert result[0].holding_days == 14

    def test_multiple_trade_cycles(self):
        """Test detecting multiple completed cycles."""
        service = ReflectionService()
        trades = [
            Trade(
                timestamp=datetime(2025, 1, 1),
                isin="US0378331005",
                ticker="AAPL",
                name="Apple Inc.",
                action="BUY",
                quantity=10,
                price=150.0,
                reasoning="Buy AAPL",
            ),
            Trade(
                timestamp=datetime(2025, 1, 5),
                isin="US5949181045",
                ticker="MSFT",
                name="Microsoft Corp.",
                action="BUY",
                quantity=5,
                price=400.0,
                reasoning="Buy MSFT",
            ),
            Trade(
                timestamp=datetime(2025, 1, 15),
                isin="US0378331005",
                ticker="AAPL",
                name="Apple Inc.",
                action="SELL",
                quantity=10,
                price=165.0,
                reasoning="Sell AAPL",
            ),
            Trade(
                timestamp=datetime(2025, 1, 20),
                isin="US5949181045",
                ticker="MSFT",
                name="Microsoft Corp.",
                action="SELL",
                quantity=5,
                price=380.0,
                reasoning="Sell MSFT",
            ),
        ]

        result = service._find_completed_trades(trades)

        assert len(result) == 2
        tickers = {t.ticker for t in result}
        assert tickers == {"AAPL", "MSFT"}

    def test_fifo_matching(self):
        """Test that FIFO matching is used for multiple buys."""
        service = ReflectionService()
        trades = [
            Trade(
                timestamp=datetime(2025, 1, 1),
                isin="US0378331005",
                ticker="AAPL",
                name="Apple Inc.",
                action="BUY",
                quantity=10,
                price=150.0,
                reasoning="First buy",
            ),
            Trade(
                timestamp=datetime(2025, 1, 5),
                isin="US0378331005",
                ticker="AAPL",
                name="Apple Inc.",
                action="BUY",
                quantity=10,
                price=160.0,
                reasoning="Second buy",
            ),
            Trade(
                timestamp=datetime(2025, 1, 15),
                isin="US0378331005",
                ticker="AAPL",
                name="Apple Inc.",
                action="SELL",
                quantity=10,
                price=170.0,
                reasoning="Sell",
            ),
        ]

        result = service._find_completed_trades(trades)

        assert len(result) == 1
        # FIFO: first buy at $150 matched with sell at $170
        assert result[0].buy_price == 150.0
        assert result[0].return_pct == pytest.approx(13.33, rel=0.1)


class TestCalculateMetrics:
    """Tests for _calculate_metrics method."""

    def test_empty_trades(self):
        """Test metrics with no trades."""
        service = ReflectionService()
        metrics = service._calculate_metrics([])

        assert metrics.total_completed_trades == 0
        assert metrics.win_rate == 0.0
        assert metrics.best_trade is None
        assert metrics.worst_trade is None

    def test_all_winners(self):
        """Test metrics with all winning trades."""
        service = ReflectionService()
        trades = [
            CompletedTrade(
                ticker="AAPL",
                name="Apple",
                buy_date=datetime(2025, 1, 1),
                sell_date=datetime(2025, 1, 15),
                buy_price=150.0,
                sell_price=165.0,
                quantity=10,
                buy_reasoning="Buy",
                sell_reasoning="Sell",
                holding_days=14,
                profit_loss=150.0,
                return_pct=10.0,
                is_winner=True,
            ),
            CompletedTrade(
                ticker="MSFT",
                name="Microsoft",
                buy_date=datetime(2025, 1, 5),
                sell_date=datetime(2025, 1, 20),
                buy_price=400.0,
                sell_price=440.0,
                quantity=5,
                buy_reasoning="Buy",
                sell_reasoning="Sell",
                holding_days=15,
                profit_loss=200.0,
                return_pct=10.0,
                is_winner=True,
            ),
        ]

        metrics = service._calculate_metrics(trades)

        assert metrics.total_completed_trades == 2
        assert metrics.winners == 2
        assert metrics.losers == 0
        assert metrics.win_rate == 100.0
        assert metrics.avg_gain_pct == 10.0

    def test_mixed_results(self):
        """Test metrics with mixed winning/losing trades."""
        service = ReflectionService()
        trades = [
            CompletedTrade(
                ticker="AAPL",
                name="Apple",
                buy_date=datetime(2025, 1, 1),
                sell_date=datetime(2025, 1, 15),
                buy_price=150.0,
                sell_price=180.0,
                quantity=10,
                buy_reasoning="Buy",
                sell_reasoning="Sell",
                holding_days=14,
                profit_loss=300.0,
                return_pct=20.0,
                is_winner=True,
            ),
            CompletedTrade(
                ticker="MSFT",
                name="Microsoft",
                buy_date=datetime(2025, 1, 5),
                sell_date=datetime(2025, 1, 12),
                buy_price=400.0,
                sell_price=360.0,
                quantity=5,
                buy_reasoning="Buy",
                sell_reasoning="Sell",
                holding_days=7,
                profit_loss=-200.0,
                return_pct=-10.0,
                is_winner=False,
            ),
        ]

        metrics = service._calculate_metrics(trades)

        assert metrics.total_completed_trades == 2
        assert metrics.winners == 1
        assert metrics.losers == 1
        assert metrics.win_rate == 50.0
        assert metrics.avg_gain_pct == 20.0
        assert metrics.avg_loss_pct == -10.0
        assert metrics.best_trade.ticker == "AAPL"
        assert metrics.worst_trade.ticker == "MSFT"


class TestAnalyzeBiases:
    """Tests for _analyze_biases method."""

    def test_empty_trades(self):
        """Test bias analysis with no trades."""
        service = ReflectionService()
        metrics = TradeMetrics(
            total_completed_trades=0,
            winners=0,
            losers=0,
            win_rate=0.0,
            avg_gain_pct=0.0,
            avg_loss_pct=0.0,
            avg_holding_days=0.0,
            total_realized_profit=0.0,
            best_trade=None,
            worst_trade=None,
            avg_winner_holding_days=0.0,
            avg_loser_holding_days=0.0,
        )

        bias = service._analyze_biases([], metrics)

        assert len(bias.warnings) == 0

    def test_detects_low_win_rate(self):
        """Test detection of low win rate warning."""
        service = ReflectionService()

        # Create trades with low win rate
        trades = []
        for i in range(6):
            trades.append(
                CompletedTrade(
                    ticker=f"TICK{i}",
                    name=f"Stock {i}",
                    buy_date=datetime(2025, 1, 1),
                    sell_date=datetime(2025, 1, 15),
                    buy_price=100.0,
                    sell_price=90.0 if i < 4 else 110.0,  # 4 losers, 2 winners = 33% win rate
                    quantity=10,
                    buy_reasoning="Buy",
                    sell_reasoning="Sell",
                    holding_days=14,
                    profit_loss=-100.0 if i < 4 else 100.0,
                    return_pct=-10.0 if i < 4 else 10.0,
                    is_winner=i >= 4,
                )
            )

        metrics = service._calculate_metrics(trades)
        bias = service._analyze_biases(trades, metrics)

        # Should detect low win rate
        assert any("win rate" in w.lower() for w in bias.warnings)

    def test_detects_quick_trades(self):
        """Test detection of quick trading pattern."""
        service = ReflectionService()

        # Create trades with short holding periods
        trades = []
        for i in range(4):
            trades.append(
                CompletedTrade(
                    ticker=f"TICK{i}",
                    name=f"Stock {i}",
                    buy_date=datetime(2025, 1, 1),
                    sell_date=datetime(2025, 1, 4),  # 3 days
                    buy_price=100.0,
                    sell_price=105.0,
                    quantity=10,
                    buy_reasoning="Buy",
                    sell_reasoning="Sell",
                    holding_days=3,
                    profit_loss=50.0,
                    return_pct=5.0,
                    is_winner=True,
                )
            )

        metrics = service._calculate_metrics(trades)
        bias = service._analyze_biases(trades, metrics)

        assert bias.quick_trades_count == 4

    def test_detects_reasoning_themes(self):
        """Test detection of reasoning themes."""
        service = ReflectionService()

        trades = [
            CompletedTrade(
                ticker="AAPL",
                name="Apple",
                buy_date=datetime(2025, 1, 1),
                sell_date=datetime(2025, 1, 15),
                buy_price=150.0,
                sell_price=165.0,
                quantity=10,
                buy_reasoning="Strong momentum and breakout pattern",
                sell_reasoning="Target reached based on technical resistance",
                holding_days=14,
                profit_loss=150.0,
                return_pct=10.0,
                is_winner=True,
            ),
        ]

        metrics = service._calculate_metrics(trades)
        bias = service._analyze_biases(trades, metrics)

        # Should detect momentum and technical themes
        theme_names = [t[0] for t in bias.buy_themes]
        assert "momentum" in theme_names or "technical" in theme_names


class TestGenerateInsights:
    """Tests for _generate_insights method."""

    def test_empty_trades(self):
        """Test insights with no trades."""
        service = ReflectionService()
        metrics = TradeMetrics(
            total_completed_trades=0,
            winners=0,
            losers=0,
            win_rate=0.0,
            avg_gain_pct=0.0,
            avg_loss_pct=0.0,
            avg_holding_days=0.0,
            total_realized_profit=0.0,
            best_trade=None,
            worst_trade=None,
            avg_winner_holding_days=0.0,
            avg_loser_holding_days=0.0,
        )
        bias = BiasAnalysis()

        insights = service._generate_insights(metrics, bias)

        assert len(insights) == 1
        assert "Not enough" in insights[0]

    def test_high_win_rate_insight(self):
        """Test insight for high win rate."""
        service = ReflectionService()
        metrics = TradeMetrics(
            total_completed_trades=10,
            winners=7,
            losers=3,
            win_rate=70.0,
            avg_gain_pct=15.0,
            avg_loss_pct=-5.0,
            avg_holding_days=14.0,
            total_realized_profit=1000.0,
            best_trade=None,
            worst_trade=None,
            avg_winner_holding_days=20.0,
            avg_loser_holding_days=8.0,
        )
        bias = BiasAnalysis()

        insights = service._generate_insights(metrics, bias)

        # Should have positive insight about win rate
        assert any("70" in i for i in insights)


class TestAnalyzePerformance:
    """Tests for analyze_performance method."""

    def test_full_analysis(self):
        """Test full performance analysis."""
        service = ReflectionService()

        trades = [
            Trade(
                timestamp=datetime(2025, 1, 1),
                isin="US0378331005",
                ticker="AAPL",
                name="Apple Inc.",
                action="BUY",
                quantity=10,
                price=150.0,
                reasoning="Growth opportunity with strong momentum",
            ),
            Trade(
                timestamp=datetime(2025, 1, 15),
                isin="US0378331005",
                ticker="AAPL",
                name="Apple Inc.",
                action="SELL",
                quantity=10,
                price=165.0,
                reasoning="Target reached",
            ),
        ]

        state = PortfolioState(
            cash=10000.0,
            holdings=[],
            trades=trades,
        )

        result = service.analyze_performance(state)

        assert result.metrics.total_completed_trades == 1
        assert result.metrics.win_rate == 100.0
        assert len(result.completed_trades) == 1
        assert result.completed_trades[0].ticker == "AAPL"

    def test_empty_portfolio(self):
        """Test analysis with empty portfolio."""
        service = ReflectionService()

        state = PortfolioState(
            cash=10000.0,
            holdings=[],
            trades=[],
        )

        result = service.analyze_performance(state)

        assert result.metrics.total_completed_trades == 0
        assert "No completed trade cycles" in result.to_context_string()
