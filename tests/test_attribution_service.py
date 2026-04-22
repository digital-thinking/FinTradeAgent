"""Tests for AttributionService."""

import pytest
from unittest.mock import MagicMock

from fin_trade.models import Holding, PortfolioConfig, PortfolioState
from fin_trade.services.attribution import (
    AttributionService,
    AttributionResult,
    HoldingAttribution,
    SectorAttribution,
)


@pytest.fixture
def mock_security_service():
    """Create a mock SecurityService with configurable prices and stock info."""
    mock = MagicMock()

    # Default prices: ticker -> price
    prices = {
        "AAPL": 200.0,  # Gain: bought at 150, now 200
        "MSFT": 400.0,  # Gain: bought at 350, now 400
        "TSLA": 150.0,  # Loss: bought at 200, now 150
        "GOOGL": 180.0,  # Gain: bought at 150, now 180
    }

    def get_price(ticker: str) -> float:
        return prices.get(ticker.upper(), 100.0)

    mock.get_price.side_effect = get_price

    # Default stock info: ticker -> info dict
    stock_info = {
        "AAPL": {"sector": "Technology", "industry": "Consumer Electronics"},
        "MSFT": {"sector": "Technology", "industry": "Software"},
        "TSLA": {"sector": "Consumer Cyclical", "industry": "Auto Manufacturers"},
        "GOOGL": {"sector": "Technology", "industry": "Internet Content"},
    }

    def get_stock_info(ticker: str, fundamentals_ticker: str | None = None) -> dict:
        return stock_info.get(ticker.upper(), {})

    mock.get_stock_info.side_effect = get_stock_info

    return mock


@pytest.fixture
def sample_config():
    """Create a sample portfolio config."""
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


class TestAttributionServiceInit:
    """Tests for AttributionService initialization."""

    def test_creates_with_security_service(self, mock_security_service):
        """Test service can be created with a security service."""
        service = AttributionService(mock_security_service)
        assert service.security_service == mock_security_service


class TestCalculateAttributionEmptyPortfolio:
    """Tests for attribution calculation with empty portfolio."""

    def test_returns_empty_result_for_no_holdings(self, mock_security_service, sample_config):
        """Test returns empty attribution result when portfolio has no holdings."""
        service = AttributionService(mock_security_service)
        state = PortfolioState(cash=10000.0, holdings=[])

        result = service.calculate_attribution(sample_config, state)

        assert isinstance(result, AttributionResult)
        assert result.by_holding == []
        assert result.by_sector == []
        assert result.total_gain == 0.0
        assert result.top_contributor is None
        assert result.top_detractor is None


class TestCalculateAttributionSingleHolding:
    """Tests for attribution calculation with a single holding."""

    def test_single_holding_with_gain(self, mock_security_service, sample_config):
        """Test attribution for a single holding with a gain."""
        service = AttributionService(mock_security_service)
        holdings = [
            Holding(ticker="AAPL",
                name="Apple Inc.",
                quantity=10,
                avg_price=150.0,
            )
        ]
        state = PortfolioState(cash=5000.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        assert len(result.by_holding) == 1
        assert result.by_holding[0].ticker == "AAPL"
        assert result.by_holding[0].cost_basis == 1500.0  # 10 * 150
        assert result.by_holding[0].current_value == 2000.0  # 10 * 200
        assert result.by_holding[0].unrealized_gain == 500.0
        assert result.by_holding[0].gain_pct == pytest.approx(33.33, rel=0.01)
        assert result.by_holding[0].contribution_pct == 100.0  # Only holding

        assert result.total_cost_basis == 1500.0
        assert result.total_current_value == 2000.0
        assert result.total_gain == 500.0

    def test_single_holding_with_loss(self, mock_security_service, sample_config):
        """Test attribution for a single holding with a loss."""
        service = AttributionService(mock_security_service)
        holdings = [
            Holding(ticker="TSLA",
                name="Tesla Inc.",
                quantity=5,
                avg_price=200.0,
            )
        ]
        state = PortfolioState(cash=5000.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        assert len(result.by_holding) == 1
        assert result.by_holding[0].ticker == "TSLA"
        assert result.by_holding[0].unrealized_gain == -250.0  # 5 * (150 - 200)
        assert result.by_holding[0].gain_pct == pytest.approx(-25.0, rel=0.01)

        assert result.top_detractor is not None
        assert result.top_detractor.ticker == "TSLA"


class TestCalculateAttributionMultipleHoldings:
    """Tests for attribution calculation with multiple holdings."""

    def test_multiple_holdings_attribution(self, mock_security_service, sample_config):
        """Test attribution for multiple holdings across sectors."""
        service = AttributionService(mock_security_service)
        holdings = [
            Holding(ticker="AAPL", name="Apple Inc.", quantity=10, avg_price=150.0),
            Holding(ticker="MSFT", name="Microsoft Corp.", quantity=5, avg_price=350.0),
            Holding(ticker="TSLA", name="Tesla Inc.", quantity=10, avg_price=200.0),
        ]
        state = PortfolioState(cash=2000.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        assert len(result.by_holding) == 3

        # AAPL: gain = 10 * (200 - 150) = 500
        aapl = next(h for h in result.by_holding if h.ticker == "AAPL")
        assert aapl.unrealized_gain == 500.0
        assert aapl.sector == "Technology"

        # MSFT: gain = 5 * (400 - 350) = 250
        msft = next(h for h in result.by_holding if h.ticker == "MSFT")
        assert msft.unrealized_gain == 250.0
        assert msft.sector == "Technology"

        # TSLA: gain = 10 * (150 - 200) = -500
        tsla = next(h for h in result.by_holding if h.ticker == "TSLA")
        assert tsla.unrealized_gain == -500.0
        assert tsla.sector == "Consumer Cyclical"

        # Total gain: 500 + 250 - 500 = 250
        assert result.total_gain == 250.0

    def test_contribution_percentages_sum_to_100(self, mock_security_service, sample_config):
        """Test that contribution percentages sum to 100% when total gain is non-zero."""
        service = AttributionService(mock_security_service)
        holdings = [
            Holding(ticker="AAPL", name="Apple Inc.", quantity=10, avg_price=150.0),
            Holding(ticker="MSFT", name="Microsoft Corp.", quantity=5, avg_price=350.0),
        ]
        state = PortfolioState(cash=2000.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        total_contribution = sum(h.contribution_pct for h in result.by_holding)
        assert total_contribution == pytest.approx(100.0, rel=0.01)

    def test_contribution_uses_gross_absolute_basis(self, sample_config):
        """Contribution % must use gross absolute gains in the denominator so
        a near-zero net total does not blow percentages up to ±50,000%.

        Setup: one +$500 winner and one -$499 loser → total gain = $1,
        gross abs = $999. Contributions should be +50.05% / −49.95%.
        """
        mock = MagicMock()
        prices = {"WIN": 200.0, "LOSE": 101.0}
        info = {
            "WIN": {"sector": "Alpha", "industry": "X"},
            "LOSE": {"sector": "Beta", "industry": "Y"},
        }
        mock.get_price.side_effect = lambda t: prices[t.upper()]
        mock.get_stock_info.side_effect = lambda t, fundamentals_ticker=None: info[t.upper()]

        service = AttributionService(mock)
        holdings = [
            Holding(ticker="WIN", name="Winner", quantity=10, avg_price=150.0),     # +500
            Holding(ticker="LOSE", name="Loser", quantity=1, avg_price=600.0),      # -499
        ]
        state = PortfolioState(cash=0.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        # Sanity: net gain really is $1 with these holdings.
        assert result.total_gain == pytest.approx(1.0)

        winner = next(h for h in result.by_holding if h.ticker == "WIN")
        loser = next(h for h in result.by_holding if h.ticker == "LOSE")
        assert winner.contribution_pct == pytest.approx(50.050, abs=0.01)
        assert loser.contribution_pct == pytest.approx(-49.950, abs=0.01)

        # Sectors should mirror the same gross-absolute basis.
        alpha = next(s for s in result.by_sector if s.sector == "Alpha")
        beta = next(s for s in result.by_sector if s.sector == "Beta")
        assert alpha.contribution_pct == pytest.approx(50.050, abs=0.01)
        assert beta.contribution_pct == pytest.approx(-49.950, abs=0.01)


class TestSectorAttribution:
    """Tests for sector-level attribution."""

    def test_sector_aggregation(self, mock_security_service, sample_config):
        """Test that holdings are correctly aggregated by sector."""
        service = AttributionService(mock_security_service)
        holdings = [
            Holding(ticker="AAPL", name="Apple Inc.", quantity=10, avg_price=150.0),
            Holding(ticker="MSFT", name="Microsoft Corp.", quantity=5, avg_price=350.0),
            Holding(ticker="TSLA", name="Tesla Inc.", quantity=10, avg_price=200.0),
        ]
        state = PortfolioState(cash=2000.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        # Should have 2 sectors: Technology and Consumer Cyclical
        assert len(result.by_sector) == 2

        tech_sector = next(s for s in result.by_sector if s.sector == "Technology")
        assert tech_sector.holdings_count == 2
        assert tech_sector.total_gain == 750.0  # AAPL (500) + MSFT (250)

        consumer_sector = next(s for s in result.by_sector if s.sector == "Consumer Cyclical")
        assert consumer_sector.holdings_count == 1
        assert consumer_sector.total_gain == -500.0  # TSLA only

    def test_unknown_sector_handling(self, mock_security_service, sample_config):
        """Test that holdings without sector info are grouped under 'Unknown'."""
        # Override stock info to return empty dict
        mock_security_service.get_stock_info.side_effect = lambda ticker, fundamentals_ticker=None: {}

        service = AttributionService(mock_security_service)
        holdings = [
            Holding(ticker="AAPL", name="Apple Inc.", quantity=10, avg_price=150.0),
        ]
        state = PortfolioState(cash=5000.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        assert len(result.by_sector) == 1
        assert result.by_sector[0].sector == "Unknown"
        assert result.by_sector[0].holdings_count == 1

    def test_sector_allocation_percentages(self, mock_security_service, sample_config):
        """Test sector allocation percentages are calculated correctly."""
        service = AttributionService(mock_security_service)
        holdings = [
            Holding(ticker="AAPL", name="Apple Inc.", quantity=10, avg_price=150.0),
            Holding(ticker="TSLA", name="Tesla Inc.", quantity=10, avg_price=200.0),
        ]
        state = PortfolioState(cash=2000.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        # AAPL current value: 10 * 200 = 2000
        # TSLA current value: 10 * 150 = 1500
        # Total: 3500

        tech_sector = next(s for s in result.by_sector if s.sector == "Technology")
        assert tech_sector.allocation_pct == pytest.approx(57.14, rel=0.01)  # 2000/3500

        consumer_sector = next(s for s in result.by_sector if s.sector == "Consumer Cyclical")
        assert consumer_sector.allocation_pct == pytest.approx(42.86, rel=0.01)  # 1500/3500


class TestTopContributorsAndDetractors:
    """Tests for top contributor and detractor identification."""

    def test_identifies_top_contributor(self, mock_security_service, sample_config):
        """Test correctly identifies the top contributor."""
        service = AttributionService(mock_security_service)
        holdings = [
            Holding(ticker="AAPL", name="Apple Inc.", quantity=10, avg_price=150.0),
            Holding(ticker="MSFT", name="Microsoft Corp.", quantity=5, avg_price=350.0),
        ]
        state = PortfolioState(cash=2000.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        # AAPL gain: 500, MSFT gain: 250
        assert result.top_contributor is not None
        assert result.top_contributor.ticker == "AAPL"
        assert result.top_contributor.unrealized_gain == 500.0

    def test_identifies_top_detractor(self, mock_security_service, sample_config):
        """Test correctly identifies the top detractor (only if negative)."""
        service = AttributionService(mock_security_service)
        holdings = [
            Holding(ticker="AAPL", name="Apple Inc.", quantity=10, avg_price=150.0),
            Holding(ticker="TSLA", name="Tesla Inc.", quantity=10, avg_price=200.0),
        ]
        state = PortfolioState(cash=2000.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        assert result.top_detractor is not None
        assert result.top_detractor.ticker == "TSLA"
        assert result.top_detractor.unrealized_gain == -500.0

    def test_no_detractor_when_all_positive(self, mock_security_service, sample_config):
        """Test that top_detractor is None when all holdings have gains."""
        service = AttributionService(mock_security_service)
        holdings = [
            Holding(ticker="AAPL", name="Apple Inc.", quantity=10, avg_price=150.0),
            Holding(ticker="MSFT", name="Microsoft Corp.", quantity=5, avg_price=350.0),
        ]
        state = PortfolioState(cash=2000.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        # Both AAPL and MSFT have gains
        assert result.top_detractor is None


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_price_fetch_failure_propagates(self, mock_security_service, sample_config):
        """Test that price fetch errors propagate (fail fast per CLAUDE.md)."""
        # Make price fetch raise an exception
        mock_security_service.get_price.side_effect = Exception("Network error")

        service = AttributionService(mock_security_service)
        holdings = [
            Holding(ticker="AAPL", name="Apple Inc.", quantity=10, avg_price=150.0),
        ]
        state = PortfolioState(cash=5000.0, holdings=holdings)

        # Should raise the exception (no fallback behavior)
        with pytest.raises(Exception, match="Network error"):
            service.calculate_attribution(sample_config, state)

    def test_stock_info_fetch_failure_propagates(self, mock_security_service, sample_config):
        """Test that stock info fetch errors propagate (fail fast per CLAUDE.md)."""
        mock_security_service.get_stock_info.side_effect = Exception("API error")

        service = AttributionService(mock_security_service)
        holdings = [
            Holding(ticker="AAPL", name="Apple Inc.", quantity=10, avg_price=150.0),
        ]
        state = PortfolioState(cash=5000.0, holdings=holdings)

        # Should raise the exception (no fallback behavior)
        with pytest.raises(Exception, match="API error"):
            service.calculate_attribution(sample_config, state)

    def test_handles_zero_cost_basis(self, mock_security_service, sample_config):
        """Test handles zero cost basis without division error."""
        service = AttributionService(mock_security_service)
        holdings = [
            Holding(ticker="AAPL", name="Apple Inc.", quantity=10, avg_price=0.0),
        ]
        state = PortfolioState(cash=5000.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        assert result.by_holding[0].gain_pct == 0.0
        assert result.total_gain_pct == 0.0

    def test_handles_zero_total_gain(self, sample_config):
        """Test handles zero total gain for contribution calculation."""
        # Create fresh mock with price equal to avg_price
        mock = MagicMock()
        mock.get_price.return_value = 150.0
        mock.get_stock_info.return_value = {"sector": "Technology"}

        service = AttributionService(mock)
        holdings = [
            Holding(ticker="AAPL", name="Apple Inc.", quantity=10, avg_price=150.0),
        ]
        state = PortfolioState(cash=5000.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        assert result.total_gain == 0.0
        assert result.by_holding[0].contribution_pct == 0.0

    def test_fractional_crypto_quantity_preserves_value(self, sample_config):
        """Fractional crypto quantities must flow through attribution without
        being truncated by an int cast (0.1234 BTC → cost basis/current value > 0).
        """
        mock = MagicMock()
        mock.get_price.return_value = 70_000.0
        mock.get_stock_info.return_value = {
            "sector": "Cryptocurrency", "industry": "Digital Asset",
        }

        service = AttributionService(mock)
        holdings = [
            Holding(
                ticker="BTC-USD",
                name="Bitcoin",
                quantity=0.1234,
                avg_price=60_000.0,
            ),
        ]
        state = PortfolioState(cash=0.0, holdings=holdings)

        result = service.calculate_attribution(sample_config, state)

        btc = result.by_holding[0]
        assert btc.quantity == pytest.approx(0.1234)
        assert btc.cost_basis == pytest.approx(0.1234 * 60_000.0)
        assert btc.current_value == pytest.approx(0.1234 * 70_000.0)
        assert btc.unrealized_gain == pytest.approx(0.1234 * 10_000.0)
        assert btc.cost_basis > 0
        assert btc.current_value > 0
