"""Tests for SchedulerService."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

from fin_trade.models import AgentRecommendation, TradeRecommendation
from fin_trade.services.portfolio import PortfolioService
from fin_trade.services.scheduler import SchedulerService


def _write_portfolio_config(
    path: Path,
    *,
    name: str = "Test Portfolio",
    run_frequency: str = "daily",
    scheduler_enabled: bool = False,
    auto_apply_trades: bool = False,
    agent_mode: str = "simple",
) -> None:
    content = f"""name: {name}
strategy_prompt: Test strategy
initial_amount: 10000.0
num_initial_trades: 2
trades_per_run: 1
run_frequency: {run_frequency}
llm_provider: openai
llm_model: gpt-4o
agent_mode: {agent_mode}
scheduler_enabled: {str(scheduler_enabled).lower()}
auto_apply_trades: {str(auto_apply_trades).lower()}
"""
    path.write_text(content)


@pytest.fixture
def scheduler_fixture(temp_data_dir, mock_security_service):
    SchedulerService.reset_instance_for_tests()

    portfolio_service = PortfolioService(
        portfolios_dir=temp_data_dir["portfolios"],
        state_dir=temp_data_dir["state"],
        security_service=mock_security_service,
    )
    agent_service = MagicMock()
    execution_log_service = MagicMock()
    execution_log_service.log_execution.return_value = 1

    scheduler = SchedulerService(
        portfolio_service=portfolio_service,
        agent_service=agent_service,
        execution_log_service=execution_log_service,
        security_service=mock_security_service,
        scheduler=BackgroundScheduler(daemon=True),
        state_path=temp_data_dir["state"] / "scheduler.json",
    )

    yield scheduler, portfolio_service, agent_service, execution_log_service

    scheduler.stop()
    SchedulerService.reset_instance_for_tests()


def test_scheduler_start_stop(scheduler_fixture, temp_data_dir):
    scheduler, _, _, _ = scheduler_fixture
    config_path = temp_data_dir["portfolios"] / "test_portfolio.yaml"
    _write_portfolio_config(config_path, scheduler_enabled=True)

    scheduler.start()
    status = scheduler.get_status()
    assert status["running"] is True
    assert status["jobs"] == 1

    scheduler.stop()
    status = scheduler.get_status()
    assert status["running"] is False


def test_enable_disable_portfolio(scheduler_fixture, temp_data_dir):
    scheduler, portfolio_service, _, _ = scheduler_fixture
    config_path = temp_data_dir["portfolios"] / "test_portfolio.yaml"
    _write_portfolio_config(config_path, scheduler_enabled=False)

    scheduler.start()

    scheduler.enable_portfolio("test_portfolio")
    config, _ = portfolio_service.load_portfolio("test_portfolio")
    assert config.scheduler_enabled is True
    assert scheduler.get_status()["enabled"] == 1
    assert scheduler._scheduler.get_job("portfolio:test_portfolio") is not None

    scheduler.disable_portfolio("test_portfolio")
    config, _ = portfolio_service.load_portfolio("test_portfolio")
    assert config.scheduler_enabled is False
    assert scheduler.get_status()["enabled"] == 0
    assert scheduler._scheduler.get_job("portfolio:test_portfolio") is None


def test_schedule_respects_frequency(scheduler_fixture, temp_data_dir):
    scheduler, _, _, _ = scheduler_fixture
    config_path = temp_data_dir["portfolios"] / "test_portfolio.yaml"
    _write_portfolio_config(config_path, scheduler_enabled=True, run_frequency="weekly")

    scheduler.start()

    job = scheduler._scheduler.get_job("portfolio:test_portfolio")
    assert job is not None
    assert job.trigger.interval == timedelta(weeks=1)


def test_auto_apply_executes_trades(scheduler_fixture, temp_data_dir):
    scheduler, portfolio_service, agent_service, execution_log_service = scheduler_fixture
    config_path = temp_data_dir["portfolios"] / "test_portfolio.yaml"
    _write_portfolio_config(config_path, scheduler_enabled=True, auto_apply_trades=True)

    recommendation = AgentRecommendation(
        trades=[
            TradeRecommendation(
                ticker="AAPL",
                name="Apple Inc.",
                action="BUY",
                quantity=1,
                reasoning="Test trade",
            )
        ],
        overall_reasoning="Test reasoning",
    )
    agent_service.execute.return_value = recommendation

    success = scheduler.run_portfolio_now("test_portfolio")
    assert success is True

    _, state = portfolio_service.load_portfolio("test_portfolio")
    assert len(state.holdings) == 1
    assert len(state.trades) == 1

    execution_log_service.mark_trades_executed.assert_called_once_with(1, [0])


def test_queue_mode_creates_pending(scheduler_fixture, temp_data_dir):
    scheduler, portfolio_service, agent_service, execution_log_service = scheduler_fixture
    config_path = temp_data_dir["portfolios"] / "test_portfolio.yaml"
    _write_portfolio_config(config_path, scheduler_enabled=True, auto_apply_trades=False)

    recommendation = AgentRecommendation(
        trades=[
            TradeRecommendation(
                ticker="AAPL",
                name="Apple Inc.",
                action="BUY",
                quantity=1,
                reasoning="Test trade",
            )
        ],
        overall_reasoning="Test reasoning",
    )
    agent_service.execute.return_value = recommendation

    success = scheduler.run_portfolio_now("test_portfolio")
    assert success is True

    _, state = portfolio_service.load_portfolio("test_portfolio")
    assert state.holdings == []
    assert state.trades == []
    assert state.last_execution is not None

    execution_log_service.mark_trades_executed.assert_not_called()


def test_error_handling(scheduler_fixture, temp_data_dir):
    scheduler, _, agent_service, execution_log_service = scheduler_fixture
    config_path = temp_data_dir["portfolios"] / "test_portfolio.yaml"
    _write_portfolio_config(config_path, scheduler_enabled=True)

    agent_service.execute.side_effect = RuntimeError("boom")

    success = scheduler.run_portfolio_now("test_portfolio")
    assert success is False

    execution_log_service.log_execution.assert_called_once()
    args, kwargs = execution_log_service.log_execution.call_args
    assert kwargs["success"] is False


def test_state_persistence(scheduler_fixture, temp_data_dir):
    scheduler, _, agent_service, _ = scheduler_fixture
    config_path = temp_data_dir["portfolios"] / "test_portfolio.yaml"
    _write_portfolio_config(config_path, scheduler_enabled=True)

    agent_service.execute.side_effect = None
    agent_service.execute.return_value = AgentRecommendation(trades=[], overall_reasoning="")

    scheduler.start()
    result = scheduler.run_portfolio_now("test_portfolio")
    assert result is True, "run_portfolio_now should succeed"

    state_path = temp_data_dir["state"] / "scheduler.json"
    assert state_path.exists()
    assert state_path.stat().st_size > 0, "scheduler.json should not be empty"

    data = json.loads(state_path.read_text())
    assert "test_portfolio" in data["enabled_portfolios"]
    assert "test_portfolio" in data["last_run_times"]

    scheduler.stop()
    SchedulerService.reset_instance_for_tests()

    reloaded = SchedulerService(
        portfolio_service=scheduler.portfolio_service,
        agent_service=scheduler.agent_service,
        execution_log_service=scheduler.execution_log_service,
        security_service=scheduler.security_service,
        scheduler=BackgroundScheduler(daemon=True),
        state_path=state_path,
    )
    assert "test_portfolio" in reloaded._enabled_portfolios
    assert "test_portfolio" in reloaded._last_run_times
