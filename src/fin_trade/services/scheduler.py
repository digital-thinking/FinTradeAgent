"""Background scheduler for automated portfolio executions."""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from apscheduler.schedulers.background import BackgroundScheduler

from fin_trade.agents.service import DebateAgentService, LangGraphAgentService
from fin_trade.models import AgentRecommendation, PortfolioConfig, PortfolioState
from fin_trade.services.agent import AgentService
from fin_trade.services.execution_log import ExecutionLogService
from fin_trade.services.portfolio import PortfolioService
from fin_trade.services.security import SecurityService

logger = logging.getLogger(__name__)


@dataclass
class ScheduledPortfolio:
    """Summary of a scheduled portfolio."""

    name: str
    display_name: str
    frequency: Literal["daily", "weekly", "monthly"]
    enabled: bool
    next_run: datetime | None
    last_run: datetime | None


class SchedulerService:
    """Singleton scheduler for automated portfolio executions."""

    _instance: "SchedulerService | None" = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        portfolio_service: PortfolioService | None = None,
        agent_service: AgentService | None = None,
        execution_log_service: ExecutionLogService | None = None,
        security_service: SecurityService | None = None,
        scheduler: BackgroundScheduler | None = None,
        state_path: Path | None = None,
    ) -> None:
        if self._initialized:
            return

        self.portfolio_service = portfolio_service or PortfolioService()
        self.security_service = security_service or SecurityService()
        self.agent_service = agent_service or AgentService(security_service=self.security_service)
        self.execution_log_service = execution_log_service or ExecutionLogService()
        self._scheduler = scheduler or BackgroundScheduler(
            daemon=True,
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            },
        )

        self._state_path = state_path or Path("data/state/scheduler.json")
        self._state_lock = threading.Lock()
        self._run_lock = threading.Lock()
        self._portfolio_locks: dict[str, threading.Lock] = {}

        self._enabled_portfolios: set[str] = set()
        self._last_run_times: dict[str, datetime] = {}

        self._load_state()
        self._initialized = True

    @classmethod
    def reset_instance_for_tests(cls) -> None:
        """Reset singleton instance for tests."""
        with cls._instance_lock:
            if cls._instance is not None:
                try:
                    if cls._instance._scheduler.running:
                        cls._instance._scheduler.shutdown(wait=False)
                except Exception:
                    pass
            cls._instance = None

    def start(self) -> None:
        """Start the background scheduler."""
        self._sync_enabled_from_configs()
        self._schedule_enabled_portfolios()
        if not self._scheduler.running:
            self._scheduler.start()

    def stop(self) -> None:
        """Stop the background scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "running": self._scheduler.running,
            "jobs": len(self._scheduler.get_jobs()),
            "enabled": len(self._enabled_portfolios),
        }

    def enable_portfolio(self, name: str) -> None:
        """Enable scheduling for a portfolio."""
        config, _ = self.portfolio_service.load_portfolio(name)
        config.scheduler_enabled = True
        self.portfolio_service.save_config(config, filename=name)

        with self._state_lock:
            self._enabled_portfolios.add(name)
            self._save_state_locked()

        self._schedule_portfolio(name, config)

    def disable_portfolio(self, name: str) -> None:
        """Disable scheduling for a portfolio."""
        config, _ = self.portfolio_service.load_portfolio(name)
        config.scheduler_enabled = False
        self.portfolio_service.save_config(config, filename=name)

        with self._state_lock:
            self._enabled_portfolios.discard(name)
            self._save_state_locked()

        job_id = self._job_id(name)
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

    def get_scheduled_portfolios(self) -> list[ScheduledPortfolio]:
        """Get scheduled portfolios with next/last run times."""
        scheduled: list[ScheduledPortfolio] = []

        for name in sorted(self._enabled_portfolios):
            try:
                config, _ = self.portfolio_service.load_portfolio(name)
            except Exception as exc:
                logger.error("Failed to load portfolio %s: %s", name, exc)
                continue

            job = self._scheduler.get_job(self._job_id(name))
            scheduled.append(
                ScheduledPortfolio(
                    name=name,
                    display_name=config.name,
                    frequency=config.run_frequency,
                    enabled=True,
                    next_run=job.next_run_time if job else None,
                    last_run=self._last_run_times.get(name),
                )
            )

        return scheduled

    def run_portfolio_now(self, name: str) -> bool:
        """Run a portfolio immediately."""
        return self._execute_portfolio(name)

    def _load_state(self) -> None:
        if not self._state_path.exists():
            return

        try:
            with open(self._state_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            enabled = data.get("enabled_portfolios", [])
            self._enabled_portfolios = set(enabled)

            last_run_times = {}
            for name, ts in data.get("last_run_times", {}).items():
                try:
                    last_run_times[name] = datetime.fromisoformat(ts)
                except Exception:
                    continue
            self._last_run_times = last_run_times
        except Exception as exc:
            logger.error("Failed to load scheduler state: %s", exc)

    def _save_state_locked(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "enabled_portfolios": sorted(self._enabled_portfolios),
            "last_run_times": {
                name: ts.isoformat() for name, ts in self._last_run_times.items()
            },
        }
        with open(self._state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _sync_enabled_from_configs(self) -> None:
        """Sync enabled portfolios from config if no state exists."""
        if self._state_path.exists():
            return

        for name in self.portfolio_service.list_portfolios():
            try:
                config, _ = self.portfolio_service.load_portfolio(name)
            except Exception:
                continue
            if config.scheduler_enabled:
                self._enabled_portfolios.add(name)

        with self._state_lock:
            self._save_state_locked()

    def _schedule_enabled_portfolios(self) -> None:
        for name in sorted(self._enabled_portfolios):
            try:
                config, _ = self.portfolio_service.load_portfolio(name)
            except Exception as exc:
                logger.error("Failed to load portfolio %s: %s", name, exc)
                continue
            self._schedule_portfolio(name, config)

    def _schedule_portfolio(self, name: str, config: PortfolioConfig) -> None:
        interval = self._frequency_interval(config.run_frequency)
        now = datetime.now()
        last_run = self._last_run_times.get(name)
        if last_run is None:
            next_run = now
        else:
            next_run = last_run + interval
            if next_run < now:
                next_run = now

        self._scheduler.add_job(
            self._execute_portfolio,
            "interval",
            id=self._job_id(name),
            kwargs={"name": name},
            days=interval.days,
            seconds=interval.seconds,
            next_run_time=next_run,
            replace_existing=True,
        )

    def _execute_portfolio(self, name: str) -> bool:
        lock = self._get_portfolio_lock(name)
        if not lock.acquire(blocking=False):
            logger.info("Portfolio %s already running; skipping", name)
            return False

        try:
            return self._execute_portfolio_locked(name)
        finally:
            lock.release()

    def _execute_portfolio_locked(self, name: str) -> bool:
        try:
            config, state = self.portfolio_service.load_portfolio(name)
        except Exception as exc:
            logger.error("Failed to load portfolio %s: %s", name, exc)
            return False

        start_time = time.time()
        recommendation: AgentRecommendation | None = None
        metrics = None

        try:
            if config.agent_mode == "debate":
                debate_agent = DebateAgentService(security_service=self.security_service)
                recommendation, metrics = debate_agent.execute(config, state)
            elif config.agent_mode == "langgraph":
                langgraph_agent = LangGraphAgentService(security_service=self.security_service)
                recommendation, metrics = langgraph_agent.execute(config, state)
            else:
                recommendation = self.agent_service.execute(config, state)
        except Exception as exc:
            logger.exception("Scheduler execution failed for %s: %s", name, exc)
            if config.agent_mode == "simple":
                duration_ms = int((time.time() - start_time) * 1000)
                self.execution_log_service.log_execution(
                    portfolio_name=config.name,
                    agent_mode="simple",
                    model=config.llm_model,
                    duration_ms=duration_ms,
                    input_tokens=0,
                    output_tokens=0,
                    num_trades=0,
                    success=False,
                    error_message=str(exc),
                    step_details={},
                    recommendations=None,
                )
            return False

        run_time = datetime.now()
        state.last_execution = run_time

        log_id = None
        if config.agent_mode in {"debate", "langgraph"}:
            log_id = self._get_latest_log_id(config.name)
        else:
            duration_ms = int((time.time() - start_time) * 1000)
            recommendations_list = self._recommendations_to_list(recommendation)
            log_id = self.execution_log_service.log_execution(
                portfolio_name=config.name,
                agent_mode="simple",
                model=config.llm_model,
                duration_ms=duration_ms,
                input_tokens=0,
                output_tokens=0,
                num_trades=len(recommendation.trades) if recommendation else 0,
                success=True,
                error_message=None,
                step_details={},
                recommendations=recommendations_list,
            )

        if recommendation and recommendation.trades:
            if config.auto_apply_trades:
                executed_indices = self._apply_recommendations(
                    config,
                    state,
                    recommendation,
                    name,
                )
                if log_id is not None and executed_indices:
                    self.execution_log_service.mark_trades_executed(
                        log_id, executed_indices
                    )
            else:
                self.portfolio_service.save_state(name, state)
        else:
            self.portfolio_service.save_state(name, state)

        with self._state_lock:
            self._last_run_times[name] = run_time
            self._save_state_locked()

        return True

    def _apply_recommendations(
        self,
        config: PortfolioConfig,
        state: PortfolioState,
        recommendation: AgentRecommendation,
        name: str,
    ) -> list[int]:
        executed_indices: list[int] = []

        indexed_trades = list(enumerate(recommendation.trades))
        indexed_trades.sort(key=lambda item: 0 if item[1].action == "SELL" else 1)

        for index, trade in indexed_trades:
            try:
                state = self.portfolio_service.execute_trade(
                    state,
                    trade.ticker,
                    trade.action,
                    trade.quantity,
                    trade.reasoning,
                    stop_loss_price=trade.stop_loss_price,
                    take_profit_price=trade.take_profit_price,
                    asset_class=config.asset_class,
                )
                executed_indices.append(index)
            except Exception as exc:
                logger.error(
                    "Failed to apply trade %s for %s: %s",
                    trade.ticker,
                    name,
                    exc,
                )

        self.portfolio_service.save_state(name, state)
        return executed_indices

    def _get_latest_log_id(self, portfolio_name: str) -> int | None:
        logs = self.execution_log_service.get_logs(portfolio_name=portfolio_name, limit=1)
        if not logs:
            return None
        return logs[0].id

    @staticmethod
    def _recommendations_to_list(
        recommendation: AgentRecommendation | None,
    ) -> list[dict] | None:
        if not recommendation:
            return None
        return [
            {
                "ticker": trade.ticker,
                "name": trade.name,
                "action": trade.action,
                "quantity": trade.quantity,
                "reasoning": trade.reasoning,
            }
            for trade in recommendation.trades
        ]

    def _get_portfolio_lock(self, name: str) -> threading.Lock:
        with self._run_lock:
            if name not in self._portfolio_locks:
                self._portfolio_locks[name] = threading.Lock()
            return self._portfolio_locks[name]

    @staticmethod
    def _frequency_interval(frequency: str) -> timedelta:
        mapping = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": timedelta(days=30),
        }
        return mapping.get(frequency, timedelta(weeks=1))

    @staticmethod
    def _job_id(name: str) -> str:
        return f"portfolio:{name}"
