"""Tests for pending-trades apply behavior."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fin_trade.models import Holding, PortfolioConfig, PortfolioState, Trade
from fin_trade.pages import pending_trades as pending_trades_page


def _make_config() -> PortfolioConfig:
    return PortfolioConfig(
        name="Test Portfolio",
        strategy_prompt="Test strategy",
        initial_amount=10000.0,
        num_initial_trades=3,
        trades_per_run=2,
        run_frequency="weekly",
        llm_provider="openai",
        llm_model="gpt-4o",
    )


def _make_portfolio_service(config: PortfolioConfig, initial_state: PortfolioState) -> tuple[MagicMock, dict]:
    current_state = {"state": initial_state}
    portfolio_service = MagicMock()
    portfolio_service.list_portfolios.return_value = ["test_portfolio"]
    portfolio_service.load_portfolio.side_effect = lambda _: (config, current_state["state"])

    def execute_trade(state, ticker, action, quantity, reasoning, price, **kwargs):
        trade = Trade(
            timestamp=datetime.now(),
            ticker=ticker,
            name=f"{ticker} Inc.",
            action=action,
            quantity=quantity,
            price=price,
            reasoning=reasoning,
        )
        holdings = list(state.holdings)
        if action == "BUY":
            holdings.append(Holding(ticker=ticker, name=f"{ticker} Inc.", quantity=quantity, avg_price=price))
            cash = state.cash - (price * quantity)
        else:
            cash = state.cash + (price * quantity)

        return PortfolioState(
            cash=cash,
            holdings=holdings,
            trades=list(state.trades) + [trade],
            last_execution=datetime.now(),
            initial_investment=state.initial_investment,
        )

    portfolio_service.execute_trade.side_effect = execute_trade
    portfolio_service.save_state.side_effect = lambda _, state: current_state.__setitem__("state", state)
    return portfolio_service, current_state


def test_apply_pending_trades_sets_initial_investment_only_once():
    """Two initial batches should preserve the original initial investment."""
    config = _make_config()
    portfolio_service, current_state = _make_portfolio_service(
        config,
        PortfolioState(cash=10000.0),
    )
    security_service = MagicMock()
    security_service.get_price.side_effect = lambda ticker: {"AAPL": 100.0, "MSFT": 120.0}[ticker]
    log = SimpleNamespace(id=1, portfolio_name="Test Portfolio", executed_trades_json=None)
    log_service = MagicMock()
    st_mock = MagicMock()
    st_mock.session_state = {}

    with patch("fin_trade.pages.pending_trades.SecurityService", return_value=security_service), patch(
        "fin_trade.pages.pending_trades.PortfolioService",
        return_value=portfolio_service,
    ), patch("fin_trade.pages.pending_trades.st", st_mock):
        pending_trades_page._apply_pending_trades(
            log,
            [{"ticker": "AAPL", "action": "BUY", "quantity": 10, "reasoning": "Batch 1"}],
            [0],
            log_service,
            increase_cash_if_needed=True,
        )

        assert current_state["state"].initial_investment == 10000.0
        assert len(current_state["state"].trades) == 1

        pending_trades_page._apply_pending_trades(
            log,
            [{"ticker": "MSFT", "action": "BUY", "quantity": 5, "reasoning": "Batch 2"}],
            [0],
            log_service,
            increase_cash_if_needed=True,
        )

    assert current_state["state"].initial_investment == 10000.0
    assert len(current_state["state"].trades) == 2
    assert current_state["state"].cash == 8400.0


def test_apply_pending_trades_rejects_initial_batch_when_cash_is_insufficient():
    """Initial pending trades should fail visibly instead of auto-topping up cash."""
    config = _make_config()
    portfolio_service, current_state = _make_portfolio_service(
        config,
        PortfolioState(cash=1000.0),
    )
    security_service = MagicMock()
    security_service.get_price.return_value = 100.0
    log = SimpleNamespace(id=1, portfolio_name="Test Portfolio", executed_trades_json=None)
    log_service = MagicMock()
    st_mock = MagicMock()
    st_mock.session_state = {}

    with patch("fin_trade.pages.pending_trades.SecurityService", return_value=security_service), patch(
        "fin_trade.pages.pending_trades.PortfolioService",
        return_value=portfolio_service,
    ), patch("fin_trade.pages.pending_trades.st", st_mock):
        pending_trades_page._apply_pending_trades(
            log,
            [{"ticker": "AAPL", "action": "BUY", "quantity": 20, "reasoning": "Too large"}],
            [0],
            log_service,
            increase_cash_if_needed=True,
        )

    st_mock.error.assert_called_once()
    assert "Insufficient cash for initial trades" in st_mock.error.call_args[0][0]
    portfolio_service.execute_trade.assert_not_called()
    portfolio_service.save_state.assert_not_called()
    assert current_state["state"].cash == 1000.0
    assert current_state["state"].initial_investment is None
