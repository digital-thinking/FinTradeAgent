"""Tests for PortfolioService."""

import json
from datetime import datetime, timedelta

import pytest

from fin_trade.models import Holding, PortfolioConfig, PortfolioState
from fin_trade.services.portfolio import PortfolioService


class TestPortfolioServiceInit:
    """Tests for PortfolioService initialization."""

    def test_creates_directories_if_not_exist(self, tmp_path, mock_security_service):
        """Test that init creates portfolios and state directories."""
        portfolios_dir = tmp_path / "portfolios"
        state_dir = tmp_path / "state"

        assert not portfolios_dir.exists()
        assert not state_dir.exists()

        PortfolioService(
            portfolios_dir=portfolios_dir,
            state_dir=state_dir,
            security_service=mock_security_service,
        )

        assert portfolios_dir.exists()
        assert state_dir.exists()


class TestListPortfolios:
    """Tests for list_portfolios method."""

    def test_returns_empty_list_when_no_portfolios(
        self, temp_data_dir, mock_security_service
    ):
        """Test returns empty list when no YAML files exist."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )
        assert service.list_portfolios() == []

    def test_returns_sorted_portfolio_names(
        self, temp_data_dir, mock_security_service
    ):
        """Test returns portfolio names sorted alphabetically."""
        # Create config files
        (temp_data_dir["portfolios"] / "zebra.yaml").write_text("name: Zebra")
        (temp_data_dir["portfolios"] / "alpha.yaml").write_text("name: Alpha")
        (temp_data_dir["portfolios"] / "beta.yaml").write_text("name: Beta")

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        assert service.list_portfolios() == ["alpha", "beta", "zebra"]

    def test_ignores_non_yaml_files(self, temp_data_dir, mock_security_service):
        """Test ignores files that aren't YAML."""
        (temp_data_dir["portfolios"] / "valid.yaml").write_text("name: Valid")
        (temp_data_dir["portfolios"] / "invalid.json").write_text("{}")
        (temp_data_dir["portfolios"] / "readme.txt").write_text("readme")

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        assert service.list_portfolios() == ["valid"]


class TestLoadConfig:
    """Tests for _load_config method."""

    def test_loads_valid_config(
        self, temp_data_dir, sample_yaml_config, mock_security_service
    ):
        """Test loading a valid YAML config."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        config = service._load_config("test_portfolio")

        assert config.name == "Test Portfolio"
        assert config.initial_amount == 10000.0
        assert config.trades_per_run == 3
        assert config.run_frequency == "weekly"
        assert config.llm_provider == "openai"
        assert config.agent_mode == "simple"

    def test_raises_file_not_found_for_missing_config(
        self, temp_data_dir, mock_security_service
    ):
        """Test raises FileNotFoundError for non-existent config."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        with pytest.raises(FileNotFoundError):
            service._load_config("nonexistent")

    def test_loads_config_with_debate_config(
        self, temp_data_dir, mock_security_service
    ):
        """Test loading config with debate configuration."""
        config_content = """name: Debate Portfolio
strategy_prompt: Test debate strategy
initial_amount: 5000.0
num_initial_trades: 3
trades_per_run: 2
run_frequency: daily
llm_provider: anthropic
llm_model: claude-3
agent_mode: debate
debate_config:
  rounds: 3
  include_neutral: false
"""
        (temp_data_dir["portfolios"] / "debate.yaml").write_text(config_content)

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        config = service._load_config("debate")

        assert config.agent_mode == "debate"
        assert config.debate_config is not None
        assert config.debate_config.rounds == 3
        assert config.debate_config.include_neutral is False


class TestLoadState:
    """Tests for _load_state method."""

    def test_creates_new_state_when_no_file_exists(
        self, temp_data_dir, mock_security_service
    ):
        """Test creates new state with initial cash when no file exists."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        state = service._load_state("new_portfolio", initial_amount=10000.0)

        assert state.cash == 10000.0
        assert state.holdings == []
        assert state.trades == []
        assert state.last_execution is None

    def test_loads_existing_state(self, temp_data_dir, mock_security_service):
        """Test loads state from existing JSON file."""
        state_data = {
            "cash": 5000.0,
            "holdings": [
                {
                    "isin": "US0378331005",
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "quantity": 10,
                    "avg_price": 150.0,
                }
            ],
            "trades": [
                {
                    "timestamp": "2024-01-15T10:30:00",
                    "isin": "US0378331005",
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "action": "BUY",
                    "quantity": 10,
                    "price": 150.0,
                    "reasoning": "Strong growth",
                }
            ],
            "last_execution": "2024-01-15T10:30:00",
        }

        state_path = temp_data_dir["state"] / "existing.json"
        state_path.write_text(json.dumps(state_data))

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        state = service._load_state("existing", initial_amount=10000.0)

        assert state.cash == 5000.0
        assert len(state.holdings) == 1
        assert state.holdings[0].ticker == "AAPL"
        assert len(state.trades) == 1
        assert state.last_execution == datetime(2024, 1, 15, 10, 30)


class TestSaveState:
    """Tests for save_state method."""

    def test_saves_state_to_json(
        self, temp_data_dir, mock_security_service, sample_portfolio_state
    ):
        """Test saves portfolio state to JSON file."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        service.save_state("test", sample_portfolio_state)

        state_path = temp_data_dir["state"] / "test.json"
        assert state_path.exists()

        data = json.loads(state_path.read_text())
        assert data["cash"] == 5000.0
        assert len(data["holdings"]) == 1
        assert data["holdings"][0]["ticker"] == "AAPL"


class TestCalculateValue:
    """Tests for calculate_value method."""

    def test_calculates_value_with_holdings(
        self, temp_data_dir, mock_security_service, sample_portfolio_state
    ):
        """Test calculates total value including holdings."""
        mock_security_service.get_price.return_value = 200.0  # AAPL price

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        value = service.calculate_value(sample_portfolio_state)

        # 5000 cash + (10 shares * $200) = 7000
        assert value == 7000.0

    def test_calculates_value_with_only_cash(
        self, temp_data_dir, mock_security_service, empty_portfolio_state
    ):
        """Test calculates value when only cash, no holdings."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        value = service.calculate_value(empty_portfolio_state)

        assert value == 10000.0

    def test_falls_back_to_avg_price_on_error(
        self, temp_data_dir, mock_security_service, sample_portfolio_state
    ):
        """Test uses avg_price when price lookup fails."""
        mock_security_service.get_price.side_effect = Exception("API error")

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        value = service.calculate_value(sample_portfolio_state)

        # 5000 cash + (10 shares * $150 avg_price) = 6500
        assert value == 6500.0


class TestCalculateGain:
    """Tests for calculate_gain method."""

    def test_calculates_positive_gain(
        self, temp_data_dir, mock_security_service, sample_portfolio_config
    ):
        """Test calculates positive gain correctly."""
        mock_security_service.get_price.return_value = 200.0

        state = PortfolioState(
            cash=8000.0,
            holdings=[
                Holding(
                    isin="US123",
                    ticker="TEST",
                    name="Test",
                    quantity=20,
                    avg_price=100.0,
                )
            ],
        )

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        abs_gain, pct_gain = service.calculate_gain(sample_portfolio_config, state)

        # Value: 8000 + (20 * 200) = 12000
        # Initial: 10000
        # Gain: 2000 (20%)
        assert abs_gain == 2000.0
        assert pct_gain == 20.0

    def test_calculates_negative_gain(
        self, temp_data_dir, mock_security_service, sample_portfolio_config
    ):
        """Test calculates negative gain (loss) correctly."""
        mock_security_service.get_price.return_value = 50.0

        state = PortfolioState(
            cash=5000.0,
            holdings=[
                Holding(
                    isin="US123",
                    ticker="TEST",
                    name="Test",
                    quantity=50,
                    avg_price=100.0,
                )
            ],
        )

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        abs_gain, pct_gain = service.calculate_gain(sample_portfolio_config, state)

        # Value: 5000 + (50 * 50) = 7500
        # Initial: 10000
        # Loss: -2500 (-25%)
        assert abs_gain == -2500.0
        assert pct_gain == -25.0


class TestIsExecutionOverdue:
    """Tests for is_execution_overdue method."""

    def test_overdue_when_never_executed(
        self, temp_data_dir, mock_security_service, sample_portfolio_config
    ):
        """Test returns True when portfolio has never been executed."""
        state = PortfolioState(cash=10000.0, last_execution=None)

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        assert service.is_execution_overdue(sample_portfolio_config, state) is True

    def test_not_overdue_when_recently_executed(
        self, temp_data_dir, mock_security_service, sample_portfolio_config
    ):
        """Test returns False when executed recently (within frequency)."""
        state = PortfolioState(cash=10000.0, last_execution=datetime.now())

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        # sample_portfolio_config has weekly frequency
        assert service.is_execution_overdue(sample_portfolio_config, state) is False

    def test_overdue_for_daily_frequency(
        self, temp_data_dir, mock_security_service
    ):
        """Test daily frequency is overdue after 1 day."""
        config = PortfolioConfig(
            name="Daily",
            strategy_prompt="Test",
            initial_amount=10000.0,
            num_initial_trades=5,
            trades_per_run=3,
            run_frequency="daily",
            llm_provider="openai",
            llm_model="gpt-4o",
        )

        # Executed 2 days ago
        state = PortfolioState(
            cash=10000.0, last_execution=datetime.now() - timedelta(days=2)
        )

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        assert service.is_execution_overdue(config, state) is True


class TestExecuteTrade:
    """Tests for execute_trade method."""

    def test_executes_buy_trade(
        self, temp_data_dir, mock_security_service, empty_portfolio_state
    ):
        """Test executing a BUY trade."""
        mock_security_service.force_update_price.return_value = 100.0

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        new_state = service.execute_trade(
            empty_portfolio_state,
            ticker="AAPL",
            action="BUY",
            quantity=10,
            reasoning="Test buy",
        )

        # Cash should decrease: 10000 - (10 * 100) = 9000
        assert new_state.cash == 9000.0
        assert len(new_state.holdings) == 1
        assert new_state.holdings[0].ticker == "AAPL"
        assert new_state.holdings[0].quantity == 10
        assert len(new_state.trades) == 1
        assert new_state.trades[0].action == "BUY"

    def test_executes_sell_trade(
        self, temp_data_dir, mock_security_service, sample_portfolio_state
    ):
        """Test executing a SELL trade."""
        mock_security_service.force_update_price.return_value = 200.0
        mock_security_service.lookup_ticker.return_value = sample_portfolio_state.holdings[0]

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        new_state = service.execute_trade(
            sample_portfolio_state,
            ticker="AAPL",
            action="SELL",
            quantity=5,
            reasoning="Taking profits",
        )

        # Cash should increase: 5000 + (5 * 200) = 6000
        assert new_state.cash == 6000.0
        # Should still have 5 shares
        assert len(new_state.holdings) == 1
        assert new_state.holdings[0].quantity == 5

    def test_buy_fails_with_insufficient_cash(
        self, temp_data_dir, mock_security_service, empty_portfolio_state
    ):
        """Test BUY fails when insufficient cash."""
        mock_security_service.force_update_price.return_value = 5000.0  # Very expensive

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        with pytest.raises(ValueError, match="Insufficient cash"):
            service.execute_trade(
                empty_portfolio_state,
                ticker="EXPENSIVE",
                action="BUY",
                quantity=10,  # Would cost 50000, but only have 10000
                reasoning="Test",
            )

    def test_sell_fails_with_insufficient_holdings(
        self, temp_data_dir, mock_security_service, sample_portfolio_state
    ):
        """Test SELL fails when insufficient holdings."""
        mock_security_service.force_update_price.return_value = 100.0

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        with pytest.raises(ValueError, match="Insufficient holdings"):
            service.execute_trade(
                sample_portfolio_state,
                ticker="AAPL",
                action="SELL",
                quantity=100,  # Only have 10 shares
                reasoning="Test",
            )

    def test_sell_fails_when_not_holding_stock(
        self, temp_data_dir, mock_security_service, empty_portfolio_state
    ):
        """Test SELL fails when not holding the stock."""
        mock_security_service.force_update_price.return_value = 100.0

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        with pytest.raises(ValueError, match="Insufficient holdings"):
            service.execute_trade(
                empty_portfolio_state,
                ticker="AAPL",
                action="SELL",
                quantity=10,
                reasoning="Test",
            )

    def test_buy_updates_average_price_for_existing_holding(
        self, temp_data_dir, mock_security_service, sample_portfolio_state
    ):
        """Test BUY updates average price when adding to existing position."""
        mock_security_service.force_update_price.return_value = 200.0

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        new_state = service.execute_trade(
            sample_portfolio_state,
            ticker="AAPL",
            action="BUY",
            quantity=10,  # Buy 10 more at $200
            reasoning="Averaging up",
        )

        # Now have 20 shares total
        holding = new_state.holdings[0]
        assert holding.quantity == 20

        # Avg price: (10 * 150 + 10 * 200) / 20 = 3500 / 20 = 175
        assert holding.avg_price == 175.0
