"""Tests for PortfolioService."""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from fin_trade.models import AssetClass, Holding, PortfolioConfig, PortfolioState
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

    def test_loads_default_ollama_base_url(
        self, temp_data_dir, mock_security_service
    ):
        """Test config defaults ollama_base_url when omitted."""
        config_content = """name: Ollama Portfolio
strategy_prompt: Test strategy
initial_amount: 10000.0
num_initial_trades: 3
trades_per_run: 2
run_frequency: weekly
llm_provider: ollama
llm_model: llama3.2
"""
        (temp_data_dir["portfolios"] / "ollama_default.yaml").write_text(config_content)

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        config = service._load_config("ollama_default")
        assert config.ollama_base_url == "http://localhost:11434"

    def test_loads_custom_ollama_base_url(
        self, temp_data_dir, mock_security_service
    ):
        """Test config reads custom ollama_base_url."""
        config_content = """name: Ollama Portfolio
strategy_prompt: Test strategy
initial_amount: 10000.0
num_initial_trades: 3
trades_per_run: 2
run_frequency: weekly
llm_provider: ollama
llm_model: llama3.2
ollama_base_url: http://127.0.0.1:11434
"""
        (temp_data_dir["portfolios"] / "ollama_custom.yaml").write_text(config_content)

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        config = service._load_config("ollama_custom")
        assert config.ollama_base_url == "http://127.0.0.1:11434"


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

    def test_price_error_propagates(
        self, temp_data_dir, mock_security_service, sample_portfolio_state
    ):
        """Test that price lookup errors propagate (fail fast per CLAUDE.md)."""
        mock_security_service.get_price.side_effect = Exception("API error")

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        with pytest.raises(Exception, match="API error"):
            service.calculate_value(sample_portfolio_state)


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
                Holding(ticker="TEST",
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
                Holding(ticker="TEST",
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

    def test_buy_with_stop_loss_and_take_profit(
        self, temp_data_dir, mock_security_service, empty_portfolio_state
    ):
        """Test BUY trade records stop-loss and take-profit prices."""
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
            stop_loss_price=90.0,
            take_profit_price=120.0,
        )

        holding = new_state.holdings[0]
        assert holding.stop_loss_price == 90.0
        assert holding.take_profit_price == 120.0

        # Also check the trade record
        trade = new_state.trades[0]
        assert trade.stop_loss_price == 90.0
        assert trade.take_profit_price == 120.0

    def test_buy_updates_stop_loss_on_existing_holding(
        self, temp_data_dir, mock_security_service
    ):
        """Test BUY updates stop-loss/take-profit when adding to position."""
        mock_security_service.force_update_price.return_value = 100.0

        # Start with a holding that has SL/TP
        initial_state = PortfolioState(
            cash=5000.0,
            holdings=[
                Holding(ticker="AAPL",
                    name="Apple Inc.",
                    quantity=10,
                    avg_price=90.0,
                    stop_loss_price=80.0,
                    take_profit_price=110.0,
                )
            ],
            trades=[],
        )

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        new_state = service.execute_trade(
            initial_state,
            ticker="AAPL",
            action="BUY",
            quantity=5,
            reasoning="Adding to position",
            stop_loss_price=85.0,  # New SL/TP
            take_profit_price=130.0,
        )

        holding = new_state.holdings[0]
        # New SL/TP should override
        assert holding.stop_loss_price == 85.0
        assert holding.take_profit_price == 130.0

    def test_buy_preserves_existing_stop_loss_when_not_provided(
        self, temp_data_dir, mock_security_service
    ):
        """Test BUY preserves existing SL/TP when not provided in new trade."""
        mock_security_service.force_update_price.return_value = 100.0

        # Start with a holding that has SL/TP
        initial_state = PortfolioState(
            cash=5000.0,
            holdings=[
                Holding(ticker="AAPL",
                    name="Apple Inc.",
                    quantity=10,
                    avg_price=90.0,
                    stop_loss_price=80.0,
                    take_profit_price=110.0,
                )
            ],
            trades=[],
        )

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        new_state = service.execute_trade(
            initial_state,
            ticker="AAPL",
            action="BUY",
            quantity=5,
            reasoning="Adding to position",
            # Not providing SL/TP
        )

        holding = new_state.holdings[0]
        # Existing SL/TP should be preserved
        assert holding.stop_loss_price == 80.0
        assert holding.take_profit_price == 110.0

    def test_sell_preserves_stop_loss_on_remaining_shares(
        self, temp_data_dir, mock_security_service
    ):
        """Test partial SELL preserves SL/TP on remaining shares."""
        mock_security_service.force_update_price.return_value = 100.0
        mock_security_service.lookup_ticker.return_value = MagicMock(
            ticker="AAPL", name="Apple Inc."
        )

        initial_state = PortfolioState(
            cash=5000.0,
            holdings=[
                Holding(ticker="AAPL",
                    name="Apple Inc.",
                    quantity=10,
                    avg_price=90.0,
                    stop_loss_price=80.0,
                    take_profit_price=120.0,
                )
            ],
            trades=[],
        )

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        new_state = service.execute_trade(
            initial_state,
            ticker="AAPL",
            action="SELL",
            quantity=5,
            reasoning="Taking partial profits",
        )

        holding = new_state.holdings[0]
        assert holding.quantity == 5
        # SL/TP should still be on remaining shares
        assert holding.stop_loss_price == 80.0
        assert holding.take_profit_price == 120.0

    def test_rejects_zero_quantity(
        self, temp_data_dir, mock_security_service, empty_portfolio_state
    ):
        """Test that zero quantity is rejected."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        with pytest.raises(ValueError, match="Invalid quantity"):
            service.execute_trade(
                empty_portfolio_state,
                ticker="AAPL",
                action="BUY",
                quantity=0,
                reasoning="Test",
            )

    def test_rejects_negative_quantity(
        self, temp_data_dir, mock_security_service, empty_portfolio_state
    ):
        """Test that negative quantity is rejected."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        with pytest.raises(ValueError, match="Invalid quantity"):
            service.execute_trade(
                empty_portfolio_state,
                ticker="AAPL",
                action="BUY",
                quantity=-5,
                reasoning="Test",
            )


class TestLoadPortfolio:
    """Tests for load_portfolio method."""

    def test_loads_config_and_state(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test load_portfolio returns both config and state."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        config, state = service.load_portfolio("test_portfolio")

        assert config.name == "Test Portfolio"
        assert state.cash == 10000.0  # Default from config

    def test_creates_new_state_for_new_portfolio(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test creates fresh state when no state file exists."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        config, state = service.load_portfolio("test_portfolio")

        assert state.holdings == []
        assert state.trades == []
        assert state.last_execution is None

    def test_loads_existing_state_file(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test loads state from existing JSON file."""
        # Create a state file
        state_data = {
            "cash": 7500.0,
            "holdings": [
                {
                    "isin": "US0378331005",
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "quantity": 15,
                    "avg_price": 165.0,
                }
            ],
            "trades": [],
            "last_execution": "2024-01-20T14:00:00",
        }
        state_path = temp_data_dir["state"] / "test_portfolio.json"
        state_path.write_text(json.dumps(state_data))

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        config, state = service.load_portfolio("test_portfolio")

        assert state.cash == 7500.0
        assert len(state.holdings) == 1
        assert state.holdings[0].ticker == "AAPL"
        assert state.holdings[0].quantity == 15


class TestLoadStateStopLoss:
    """Tests for loading state with stop-loss/take-profit."""

    def test_loads_stop_loss_from_state(self, temp_data_dir, mock_security_service):
        """Test that stop-loss values are loaded from state file."""
        state_data = {
            "cash": 5000.0,
            "holdings": [
                {
                    "isin": "US123",
                    "ticker": "AAPL",
                    "name": "Apple",
                    "quantity": 10,
                    "avg_price": 150.0,
                    "stop_loss_price": 135.0,
                    "take_profit_price": 180.0,
                }
            ],
            "trades": [],
        }
        state_path = temp_data_dir["state"] / "test.json"
        state_path.write_text(json.dumps(state_data))

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        state = service._load_state("test", initial_amount=10000.0)

        assert state.holdings[0].stop_loss_price == 135.0
        assert state.holdings[0].take_profit_price == 180.0

    def test_handles_missing_stop_loss_in_state(
        self, temp_data_dir, mock_security_service
    ):
        """Test graceful handling of missing stop-loss in older state files."""
        state_data = {
            "cash": 5000.0,
            "holdings": [
                {
                    "isin": "US123",
                    "ticker": "AAPL",
                    "name": "Apple",
                    "quantity": 10,
                    "avg_price": 150.0,
                    # No stop_loss_price or take_profit_price
                }
            ],
            "trades": [],
        }
        state_path = temp_data_dir["state"] / "test.json"
        state_path.write_text(json.dumps(state_data))

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        state = service._load_state("test", initial_amount=10000.0)

        assert state.holdings[0].stop_loss_price is None
        assert state.holdings[0].take_profit_price is None


class TestClonePortfolio:
    """Tests for clone_portfolio method."""

    def test_clone_portfolio_config_only(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test cloning a portfolio without state."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        # Create state for source portfolio
        state_data = {"cash": 5000.0, "holdings": [], "trades": []}
        state_path = temp_data_dir["state"] / "test_portfolio.json"
        state_path.write_text(json.dumps(state_data))

        # Clone without state
        cloned_config = service.clone_portfolio(
            "test_portfolio", "cloned_portfolio", include_state=False
        )

        assert cloned_config.name == "cloned_portfolio"
        assert cloned_config.initial_amount == 10000.0

        # Verify config file was created
        cloned_config_path = temp_data_dir["portfolios"] / "cloned_portfolio.yaml"
        assert cloned_config_path.exists()

        # Verify no state file was created
        cloned_state_path = temp_data_dir["state"] / "cloned_portfolio.json"
        assert not cloned_state_path.exists()

    def test_clone_portfolio_with_state(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test cloning a portfolio with state."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        # Create state for source portfolio
        state_data = {
            "cash": 5000.0,
            "holdings": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "quantity": 10,
                    "avg_price": 150.0,
                }
            ],
            "trades": [],
        }
        state_path = temp_data_dir["state"] / "test_portfolio.json"
        state_path.write_text(json.dumps(state_data))

        # Clone with state
        cloned_config = service.clone_portfolio(
            "test_portfolio", "cloned_with_state", include_state=True
        )

        assert cloned_config.name == "cloned_with_state"

        # Verify state file was copied
        cloned_state_path = temp_data_dir["state"] / "cloned_with_state.json"
        assert cloned_state_path.exists()

        cloned_state_data = json.loads(cloned_state_path.read_text())
        assert cloned_state_data["cash"] == 5000.0
        assert len(cloned_state_data["holdings"]) == 1
        assert cloned_state_data["holdings"][0]["ticker"] == "AAPL"

    def test_clone_portfolio_duplicate_name_error(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test cloning fails when target name already exists."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        # Create another portfolio with the target name
        (temp_data_dir["portfolios"] / "existing.yaml").write_text("name: Existing")

        with pytest.raises(ValueError, match="Portfolio already exists"):
            service.clone_portfolio("test_portfolio", "existing")

    def test_clone_portfolio_source_not_found(
        self, temp_data_dir, mock_security_service
    ):
        """Test cloning fails when source doesn't exist."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        with pytest.raises(FileNotFoundError, match="Source portfolio not found"):
            service.clone_portfolio("nonexistent", "new_name")

    def test_clone_portfolio_invalid_name_characters(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test cloning fails with invalid characters in name."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        with pytest.raises(ValueError, match="invalid characters"):
            service.clone_portfolio("test_portfolio", "bad/name")

        with pytest.raises(ValueError, match="invalid characters"):
            service.clone_portfolio("test_portfolio", "bad:name")

    def test_clone_portfolio_empty_name(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test cloning fails with empty name."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        with pytest.raises(ValueError, match="cannot be empty"):
            service.clone_portfolio("test_portfolio", "")

        with pytest.raises(ValueError, match="cannot be empty"):
            service.clone_portfolio("test_portfolio", "   ")


class TestResetPortfolio:
    """Tests for reset_portfolio method."""

    def test_reset_portfolio_with_archive(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test resetting a portfolio archives the state."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        # Create state with holdings
        state_data = {
            "cash": 5000.0,
            "holdings": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "quantity": 10,
                    "avg_price": 150.0,
                }
            ],
            "trades": [
                {
                    "timestamp": "2024-01-15T10:30:00",
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "action": "BUY",
                    "quantity": 10,
                    "price": 150.0,
                    "reasoning": "Test",
                }
            ],
        }
        state_path = temp_data_dir["state"] / "test_portfolio.json"
        state_path.write_text(json.dumps(state_data))

        # Reset with archive
        service.reset_portfolio("test_portfolio", archive=True)

        # Verify archive was created
        archive_dir = temp_data_dir["state"] / "archive"
        assert archive_dir.exists()
        archive_files = list(archive_dir.glob("test_portfolio_*.json"))
        assert len(archive_files) == 1

        # Verify archived content
        archived_data = json.loads(archive_files[0].read_text())
        assert archived_data["cash"] == 5000.0
        assert len(archived_data["holdings"]) == 1

        # Verify new state is fresh
        _, new_state = service.load_portfolio("test_portfolio")
        assert new_state.cash == 10000.0  # initial_amount from config
        assert new_state.holdings == []
        assert new_state.trades == []

    def test_reset_portfolio_no_archive(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test resetting a portfolio without archiving."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        # Create state
        state_data = {"cash": 5000.0, "holdings": [], "trades": []}
        state_path = temp_data_dir["state"] / "test_portfolio.json"
        state_path.write_text(json.dumps(state_data))

        # Reset without archive
        service.reset_portfolio("test_portfolio", archive=False)

        # Verify no archive was created
        archive_dir = temp_data_dir["state"] / "archive"
        assert not archive_dir.exists() or not list(archive_dir.glob("*.json"))

        # Verify state was reset
        _, new_state = service.load_portfolio("test_portfolio")
        assert new_state.cash == 10000.0

    def test_reset_portfolio_preserves_config(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test reset doesn't modify the config file."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        # Get original config content
        config_path = temp_data_dir["portfolios"] / "test_portfolio.yaml"
        original_content = config_path.read_text()

        # Create and reset state
        state_path = temp_data_dir["state"] / "test_portfolio.json"
        state_path.write_text(json.dumps({"cash": 5000.0, "holdings": [], "trades": []}))

        service.reset_portfolio("test_portfolio")

        # Verify config unchanged
        assert config_path.read_text() == original_content

    def test_reset_portfolio_no_state_file(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test reset works when no state file exists."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        # Reset without existing state file
        service.reset_portfolio("test_portfolio", archive=True)

        # Verify fresh state was created
        _, new_state = service.load_portfolio("test_portfolio")
        assert new_state.cash == 10000.0
        assert new_state.holdings == []

    def test_reset_portfolio_not_found(
        self, temp_data_dir, mock_security_service
    ):
        """Test reset fails when portfolio doesn't exist."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        with pytest.raises(FileNotFoundError):
            service.reset_portfolio("nonexistent")


class TestDeletePortfolio:
    """Tests for delete_portfolio method."""

    def test_delete_portfolio_with_archive(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test deleting a portfolio archives the state."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        # Create state
        state_path = temp_data_dir["state"] / "test_portfolio.json"
        state_path.write_text(json.dumps({"cash": 5000.0, "holdings": [], "trades": []}))

        service.delete_portfolio("test_portfolio", archive_state=True)

        # Verify config deleted
        config_path = temp_data_dir["portfolios"] / "test_portfolio.yaml"
        assert not config_path.exists()

        # Verify state archived
        archive_dir = temp_data_dir["state"] / "archive"
        archive_files = list(archive_dir.glob("test_portfolio_*.json"))
        assert len(archive_files) == 1

    def test_delete_portfolio_without_archive(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        """Test deleting a portfolio without archiving."""
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        # Create state
        state_path = temp_data_dir["state"] / "test_portfolio.json"
        state_path.write_text(json.dumps({"cash": 5000.0, "holdings": [], "trades": []}))

        service.delete_portfolio("test_portfolio", archive_state=False)

        # Verify config deleted
        assert not (temp_data_dir["portfolios"] / "test_portfolio.yaml").exists()

        # Verify state deleted (not archived)
        assert not state_path.exists()
        archive_dir = temp_data_dir["state"] / "archive"
        assert not archive_dir.exists() or not list(archive_dir.glob("*.json"))


class TestAssetClassConfig:
    """Tests for asset class config loading."""

    def test_load_config_defaults_to_stocks(
        self, temp_data_dir, mock_security_service, sample_yaml_config
    ):
        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        config = service._load_config("test_portfolio")
        assert config.asset_class == AssetClass.STOCKS

    def test_load_config_reads_crypto_asset_class(
        self, temp_data_dir, mock_security_service
    ):
        config_content = """name: Crypto Portfolio
strategy_prompt: Trade major cryptocurrencies
initial_amount: 5000.0
num_initial_trades: 2
trades_per_run: 2
run_frequency: daily
llm_provider: openai
llm_model: gpt-5.2
asset_class: crypto
"""
        (temp_data_dir["portfolios"] / "crypto.yaml").write_text(config_content)

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        config = service._load_config("crypto")
        assert config.asset_class == AssetClass.CRYPTO


class TestExecuteTradeAssetClass:
    """Tests for asset-class-aware execution rules."""

    def test_rejects_fractional_quantity_for_stocks(
        self, temp_data_dir, mock_security_service, empty_portfolio_state
    ):
        mock_security_service.force_update_price.return_value = 100.0

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        with pytest.raises(ValueError, match="whole numbers"):
            service.execute_trade(
                empty_portfolio_state,
                ticker="AAPL",
                action="BUY",
                quantity=1.5,
                reasoning="Invalid fractional stock trade",
                asset_class=AssetClass.STOCKS,
            )

    def test_allows_fractional_quantity_for_crypto(
        self, temp_data_dir, mock_security_service, empty_portfolio_state
    ):
        mock_security_service.force_update_price.return_value = 40000.0
        mock_security_service.lookup_ticker.return_value = MagicMock(
            ticker="BTC-USD",
            name="Bitcoin USD",
        )

        service = PortfolioService(
            portfolios_dir=temp_data_dir["portfolios"],
            state_dir=temp_data_dir["state"],
            security_service=mock_security_service,
        )

        new_state = service.execute_trade(
            empty_portfolio_state,
            ticker="BTC-USD",
            action="BUY",
            quantity=0.1,
            reasoning="Open BTC position",
            asset_class=AssetClass.CRYPTO,
        )

        assert len(new_state.holdings) == 1
        assert new_state.holdings[0].ticker == "BTC-USD"
        assert new_state.holdings[0].quantity == 0.1
