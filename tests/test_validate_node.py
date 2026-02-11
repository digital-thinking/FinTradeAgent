"""Tests for validate_node function."""

import pytest
from unittest.mock import patch, MagicMock

from backend.fin_trade.agents.nodes.validate import validate_node
from backend.fin_trade.models import (
    Holding,
    PortfolioState,
    TradeRecommendation,
    AgentRecommendation,
)


class TestValidateNodeNoRecommendations:
    """Tests for validate_node when no recommendations are present."""

    def test_returns_error_when_recommendations_none(self):
        """Test returns error when recommendations is None."""
        state = {
            "recommendations": None,
            "portfolio_state": PortfolioState(cash=10000.0),
            "error": "Parsing failed",
            "retry_count": 0,
        }

        result = validate_node(state)

        assert result["error"] == "Parsing failed"
        assert result["retry_count"] == 1
        assert "_metrics_validate" in result

    def test_increments_retry_count(self):
        """Test increments retry count on failure."""
        state = {
            "recommendations": None,
            "portfolio_state": PortfolioState(cash=10000.0),
            "retry_count": 2,
        }

        result = validate_node(state)

        assert result["retry_count"] == 3


class TestValidateNodeInvalidActions:
    """Tests for validate_node with invalid actions."""

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    def test_rejects_invalid_action(self, mock_security_class):
        """Test rejects trades with invalid action (not BUY/SELL)."""
        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="HOLD",  # Invalid action
                    quantity=10,
                    reasoning="Test",
                )
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=10000.0),
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        assert result["error"] is not None
        assert "Invalid action" in result["error"]
        assert result["retry_count"] == 1


class TestValidateNodeInvalidQuantity:
    """Tests for validate_node with invalid quantities."""

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    def test_rejects_zero_quantity(self, mock_security_class):
        """Test rejects trades with zero quantity."""
        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="BUY",
                    quantity=0,
                    reasoning="Test",
                )
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=10000.0),
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        assert result["error"] is not None
        assert "Quantity must be positive" in result["error"]

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    def test_rejects_negative_quantity(self, mock_security_class):
        """Test rejects trades with negative quantity."""
        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="BUY",
                    quantity=-5,
                    reasoning="Test",
                )
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=10000.0),
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        assert result["error"] is not None
        assert "Quantity must be positive" in result["error"]


class TestValidateNodeSellValidation:
    """Tests for validate_node SELL validation."""

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    def test_rejects_sell_without_holdings(self, mock_security_class):
        """Test rejects SELL when ticker not in holdings."""
        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="SELL",
                    quantity=10,
                    reasoning="Test",
                )
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=10000.0, holdings=[]),
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        assert result["error"] is not None
        assert "Cannot SELL" in result["error"]
        assert "not in holdings" in result["error"]

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    def test_rejects_sell_with_insufficient_shares(self, mock_security_class):
        """Test rejects SELL when not enough shares owned."""
        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="SELL",
                    quantity=100,  # Want to sell 100
                    reasoning="Test",
                )
            ]
        )

        holdings = [
            Holding(ticker="AAPL",
                name="Apple",
                quantity=10,  # Only have 10
                avg_price=150.0,
            )
        ]

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=10000.0, holdings=holdings),
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        assert result["error"] is not None
        assert "Cannot SELL 100 shares" in result["error"]
        assert "only own 10" in result["error"]

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    @patch("fin_trade.agents.nodes.validate.get_stock_price")
    def test_accepts_valid_sell(self, mock_get_price, mock_security_class):
        """Test accepts valid SELL with sufficient holdings."""
        mock_get_price.return_value = 150.0  # Price for cash estimation

        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="SELL",
                    quantity=5,
                    reasoning="Test",
                )
            ]
        )

        holdings = [
            Holding(ticker="AAPL",
                name="Apple",
                quantity=10,
                avg_price=150.0,
            )
        ]

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=10000.0, holdings=holdings),
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        assert result["error"] is None
        assert result["retry_count"] == 0


class TestValidateNodeBuyValidation:
    """Tests for validate_node BUY validation."""

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    @patch("fin_trade.agents.nodes.validate.get_stock_price")
    def test_rejects_buy_with_insufficient_cash(
        self, mock_get_price, mock_security_class
    ):
        """Test rejects BUY when insufficient cash."""
        mock_get_price.return_value = 1000.0  # $1000 per share

        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="EXPENSIVE",
                    name="Expensive Stock",
                    action="BUY",
                    quantity=100,  # Would cost $100,000
                    reasoning="Test",
                )
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=10000.0),  # Only $10,000
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        assert result["error"] is not None
        assert "Insufficient cash" in result["error"]

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    def test_uses_cached_price_data(self, mock_security_class):
        """Test uses price_data from state instead of fetching."""
        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="BUY",
                    quantity=10,
                    reasoning="Test",
                )
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=10000.0),
            "price_data": {"AAPL": 100.0},  # Cached price
            "retry_count": 0,
        }

        result = validate_node(state)

        # 10 shares * $100 = $1000 < $10000 cash, should pass
        assert result["error"] is None

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    @patch("fin_trade.agents.nodes.validate.get_stock_price")
    def test_accepts_valid_buy(self, mock_get_price, mock_security_class):
        """Test accepts valid BUY with sufficient cash."""
        mock_get_price.return_value = 100.0

        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="BUY",
                    quantity=10,
                    reasoning="Test",
                )
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=10000.0),
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        assert result["error"] is None
        assert result["retry_count"] == 0

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    @patch("fin_trade.agents.nodes.validate.get_stock_price")
    def test_allows_buy_when_price_lookup_fails(
        self, mock_get_price, mock_security_class
    ):
        """Test allows BUY through when price lookup fails."""
        mock_get_price.side_effect = Exception("API error")

        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="UNKNOWN",
                    name="Unknown Stock",
                    action="BUY",
                    quantity=10,
                    reasoning="Test",
                )
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=10000.0),
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        # Should pass through since we can't validate without price
        assert result["error"] is None


class TestValidateNodeMultipleTrades:
    """Tests for validate_node with multiple trades."""

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    @patch("fin_trade.agents.nodes.validate.get_stock_price")
    def test_validates_total_cash_across_buys(
        self, mock_get_price, mock_security_class
    ):
        """Test validates total cash needed across all BUY orders."""
        mock_get_price.return_value = 100.0

        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="BUY",
                    quantity=50,  # $5000
                    reasoning="Test",
                ),
                TradeRecommendation(
                    ticker="MSFT",
                    name="Microsoft",
                    action="BUY",
                    quantity=60,  # $6000
                    reasoning="Test",
                ),
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=10000.0),  # Only $10,000
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        # Total cost: $11,000 > $10,000 cash
        assert result["error"] is not None
        assert "Insufficient cash" in result["error"]

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    def test_collects_multiple_errors(self, mock_security_class):
        """Test collects and reports multiple validation errors."""
        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="INVALID",
                    quantity=10,
                    reasoning="Test",
                ),
                TradeRecommendation(
                    ticker="MSFT",
                    name="Microsoft",
                    action="BUY",
                    quantity=-5,
                    reasoning="Test",
                ),
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=10000.0),
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        assert result["error"] is not None
        # Should have both errors separated by semicolon
        assert "Invalid action" in result["error"]
        assert "Quantity must be positive" in result["error"]


class TestValidateNodeMetrics:
    """Tests for validate_node metrics."""

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    def test_includes_metrics_in_result(self, mock_security_class):
        """Test includes metrics in the result."""
        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="BUY",
                    quantity=10,
                    reasoning="Test",
                )
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=10000.0),
            "price_data": {"AAPL": 100.0},
            "retry_count": 0,
        }

        result = validate_node(state)

        assert "_metrics_validate" in result
        assert "duration_ms" in result["_metrics_validate"]
        assert "input_tokens" in result["_metrics_validate"]
        assert "output_tokens" in result["_metrics_validate"]
        # Validate node doesn't use tokens
        assert result["_metrics_validate"]["input_tokens"] == 0
        assert result["_metrics_validate"]["output_tokens"] == 0


class TestValidateNodeSellProceeds:
    """Tests for validate_node SELL proceeds counting towards BUY validation."""

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    @patch("fin_trade.agents.nodes.validate.get_stock_price")
    def test_sell_proceeds_count_toward_buy_cash(
        self, mock_get_price, mock_security_class
    ):
        """Test that SELL proceeds are added to available cash for BUY validation."""
        mock_get_price.return_value = 100.0  # $100 per share

        holdings = [
            Holding(ticker="MSFT",
                name="Microsoft",
                quantity=100,  # Can sell 50 shares = $5000
                avg_price=100.0,
            )
        ]

        # SELL 50 MSFT = +$5000, BUY 80 AAPL = -$8000
        # With only $5000 cash, this would fail without SELL proceeds
        # With SELL proceeds: $5000 + $5000 = $10000 available, enough for $8000 BUY
        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="BUY",
                    quantity=80,  # $8000
                    reasoning="Test",
                ),
                TradeRecommendation(
                    ticker="MSFT",
                    name="Microsoft",
                    action="SELL",
                    quantity=50,  # $5000
                    reasoning="Test",
                ),
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=5000.0, holdings=holdings),
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        # Should pass because SELL proceeds ($5000) + cash ($5000) = $10000 >= $8000 BUY
        assert result["error"] is None
        assert result["retry_count"] == 0

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    @patch("fin_trade.agents.nodes.validate.get_stock_price")
    def test_still_fails_when_sell_proceeds_not_enough(
        self, mock_get_price, mock_security_class
    ):
        """Test that validation still fails when SELL proceeds + cash not enough."""
        mock_get_price.return_value = 100.0

        holdings = [
            Holding(ticker="MSFT",
                name="Microsoft",
                quantity=20,  # Can only sell 20 shares = $2000
                avg_price=100.0,
            )
        ]

        # SELL 20 MSFT = +$2000, BUY 80 AAPL = -$8000
        # Cash $1000 + SELL $2000 = $3000, not enough for $8000
        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="BUY",
                    quantity=80,  # $8000
                    reasoning="Test",
                ),
                TradeRecommendation(
                    ticker="MSFT",
                    name="Microsoft",
                    action="SELL",
                    quantity=20,  # $2000
                    reasoning="Test",
                ),
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=1000.0, holdings=holdings),
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        # Should fail: $1000 cash + $2000 sell = $3000 < $8000 needed
        assert result["error"] is not None
        assert "Insufficient cash" in result["error"]
        assert "$3000.00 available" in result["error"]

    @patch("fin_trade.agents.nodes.validate.SecurityService")
    @patch("fin_trade.agents.nodes.validate.get_stock_price")
    def test_invalid_sell_does_not_count_toward_cash(
        self, mock_get_price, mock_security_class
    ):
        """Test that invalid SELL orders don't count toward available cash."""
        mock_get_price.return_value = 100.0

        holdings = [
            Holding(ticker="MSFT",
                name="Microsoft",
                quantity=10,  # Only 10 shares, trying to sell 50
                avg_price=100.0,
            )
        ]

        recommendation = AgentRecommendation(
            trades=[
                TradeRecommendation(
                    ticker="AAPL",
                    name="Apple",
                    action="BUY",
                    quantity=80,  # $8000
                    reasoning="Test",
                ),
                TradeRecommendation(
                    ticker="MSFT",
                    name="Microsoft",
                    action="SELL",
                    quantity=50,  # Invalid - only have 10
                    reasoning="Test",
                ),
            ]
        )

        state = {
            "recommendations": recommendation,
            "portfolio_state": PortfolioState(cash=5000.0, holdings=holdings),
            "price_data": {},
            "retry_count": 0,
        }

        result = validate_node(state)

        # Should have error for invalid SELL
        assert result["error"] is not None
        assert "Cannot SELL 50 shares" in result["error"]
