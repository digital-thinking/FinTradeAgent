"""Portfolio management service."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import yaml

from fin_trade.models import (
    Holding,
    PortfolioConfig,
    PortfolioState,
    Trade,
)
from fin_trade.services.stock_data import StockDataService


class PortfolioService:
    """Service for managing portfolio configurations and state."""

    def __init__(
        self,
        portfolios_dir: Path | None = None,
        state_dir: Path | None = None,
        stock_service: StockDataService | None = None,
    ):
        if portfolios_dir is None:
            portfolios_dir = Path("data/portfolios")
        if state_dir is None:
            state_dir = Path("data/state")

        self.portfolios_dir = portfolios_dir
        self.state_dir = state_dir
        self.stock_service = stock_service or StockDataService()

        self.portfolios_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def list_portfolios(self) -> list[str]:
        """List all available portfolio names."""
        portfolios = []
        for path in self.portfolios_dir.glob("*.yaml"):
            portfolios.append(path.stem)
        return sorted(portfolios)

    def _load_config(self, name: str) -> PortfolioConfig:
        """Load portfolio configuration from YAML."""
        config_path = self.portfolios_dir / f"{name}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Portfolio config not found: {name}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return PortfolioConfig(
            name=data["name"],
            strategy_prompt=data["strategy_prompt"],
            initial_amount=float(data["initial_amount"]),
            num_initial_trades=int(data["num_initial_trades"]),
            trades_per_run=int(data["trades_per_run"]),
            run_frequency=data["run_frequency"],
            llm_provider=data["llm_provider"],
            llm_model=data["llm_model"],
        )

    @staticmethod
    def _to_naive_datetime(dt: datetime) -> datetime:
        """Convert a datetime to naive (no timezone) for consistent comparisons."""
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt

    def _load_state(self, name: str, initial_amount: float) -> PortfolioState:
        """Load portfolio state from JSON, or create new if not exists."""
        state_path = self.state_dir / f"{name}.json"

        if not state_path.exists():
            return PortfolioState(cash=initial_amount)

        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        holdings = [
            Holding(
                isin=h["isin"],
                quantity=int(h["quantity"]),
                avg_price=float(h["avg_price"]),
            )
            for h in data.get("holdings", [])
        ]

        trades = [
            Trade(
                timestamp=self._to_naive_datetime(datetime.fromisoformat(t["timestamp"])),
                isin=t["isin"],
                action=t["action"],
                quantity=int(t["quantity"]),
                price=float(t["price"]),
                reasoning=t["reasoning"],
            )
            for t in data.get("trades", [])
        ]

        last_execution = None
        if data.get("last_execution"):
            last_execution = self._to_naive_datetime(datetime.fromisoformat(data["last_execution"]))

        return PortfolioState(
            cash=float(data["cash"]),
            holdings=holdings,
            trades=trades,
            last_execution=last_execution,
        )

    def load_portfolio(self, name: str) -> tuple[PortfolioConfig, PortfolioState]:
        """Load a portfolio's config and state."""
        config = self._load_config(name)
        state = self._load_state(name, config.initial_amount)
        return config, state

    def save_state(self, name: str, state: PortfolioState) -> None:
        """Save portfolio state to JSON."""
        state_path = self.state_dir / f"{name}.json"

        data = {
            "cash": state.cash,
            "holdings": [
                {
                    "isin": h.isin,
                    "quantity": h.quantity,
                    "avg_price": h.avg_price,
                }
                for h in state.holdings
            ],
            "trades": [
                {
                    "timestamp": t.timestamp.isoformat(),
                    "isin": t.isin,
                    "action": t.action,
                    "quantity": t.quantity,
                    "price": t.price,
                    "reasoning": t.reasoning,
                }
                for t in state.trades
            ],
            "last_execution": (
                state.last_execution.isoformat() if state.last_execution else None
            ),
        }

        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def calculate_value(self, state: PortfolioState) -> float:
        """Calculate total portfolio value (cash + holdings)."""
        total = state.cash
        for holding in state.holdings:
            try:
                price = self.stock_service.get_price(holding.isin)
                total += price * holding.quantity
            except Exception:
                total += holding.avg_price * holding.quantity
        return total

    def calculate_gain(
        self, config: PortfolioConfig, state: PortfolioState
    ) -> tuple[float, float]:
        """Calculate absolute and percentage gain/loss."""
        current_value = self.calculate_value(state)
        initial = config.initial_amount
        absolute_gain = current_value - initial
        percentage_gain = (absolute_gain / initial) * 100 if initial > 0 else 0
        return absolute_gain, percentage_gain

    def is_execution_overdue(
        self, config: PortfolioConfig, state: PortfolioState
    ) -> bool:
        """Check if the portfolio needs to be executed based on schedule."""
        if state.last_execution is None:
            return True

        now = datetime.now()
        last = state.last_execution

        frequency_deltas: dict[Literal["daily", "weekly", "monthly"], timedelta] = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": timedelta(days=30),
        }

        delta = frequency_deltas.get(config.run_frequency, timedelta(weeks=1))
        return now - last >= delta

    def execute_trade(
        self,
        state: PortfolioState,
        isin: str,
        action: Literal["BUY", "SELL"],
        quantity: int,
        reasoning: str,
    ) -> PortfolioState:
        """Execute a trade and return updated state."""
        price = self.stock_service.get_price(isin)
        cost = price * quantity

        holdings = list(state.holdings)
        trades = list(state.trades)
        cash = state.cash

        if action == "BUY":
            if cost > cash:
                raise ValueError(f"Insufficient cash: need {cost}, have {cash}")

            cash -= cost
            existing = next((h for h in holdings if h.isin == isin), None)
            if existing:
                total_qty = existing.quantity + quantity
                avg_price = (
                    (existing.avg_price * existing.quantity) + (price * quantity)
                ) / total_qty
                holdings = [h for h in holdings if h.isin != isin]
                holdings.append(Holding(isin=isin, quantity=total_qty, avg_price=avg_price))
            else:
                holdings.append(Holding(isin=isin, quantity=quantity, avg_price=price))

        elif action == "SELL":
            existing = next((h for h in holdings if h.isin == isin), None)
            if not existing or existing.quantity < quantity:
                raise ValueError(
                    f"Insufficient holdings: need {quantity}, have {existing.quantity if existing else 0}"
                )

            cash += cost
            new_qty = existing.quantity - quantity
            holdings = [h for h in holdings if h.isin != isin]
            if new_qty > 0:
                holdings.append(
                    Holding(isin=isin, quantity=new_qty, avg_price=existing.avg_price)
                )

        trade = Trade(
            timestamp=datetime.now(),
            isin=isin,
            action=action,
            quantity=quantity,
            price=price,
            reasoning=reasoning,
        )
        trades.append(trade)

        return PortfolioState(
            cash=cash,
            holdings=holdings,
            trades=trades,
            last_execution=datetime.now(),
        )
