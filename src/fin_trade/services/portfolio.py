"""Portfolio management service."""

import json
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import yaml

from fin_trade.models import (
    AssetClass,
    DebateConfig,
    Holding,
    PortfolioConfig,
    PortfolioState,
    Trade,
)
from fin_trade.services.security import SecurityService


class PortfolioService:
    """Service for managing portfolio configurations and state."""

    def __init__(
        self,
        portfolios_dir: Path | None = None,
        state_dir: Path | None = None,
        security_service: SecurityService | None = None,
    ):
        if portfolios_dir is None:
            portfolios_dir = Path("data/portfolios")
        if state_dir is None:
            state_dir = Path("data/state")

        self.portfolios_dir = portfolios_dir
        self.state_dir = state_dir
        self.security_service = security_service or SecurityService()

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

        # Load debate config if present
        debate_config = None
        if data.get("debate_config"):
            dc = data["debate_config"]
            debate_config = DebateConfig(
                rounds=dc.get("rounds", 2),
                include_neutral=dc.get("include_neutral", True),
            )

        return PortfolioConfig(
            name=data["name"],
            strategy_prompt=data["strategy_prompt"],
            initial_amount=float(data["initial_amount"]),
            num_initial_trades=int(data["num_initial_trades"]),
            trades_per_run=int(data["trades_per_run"]),
            run_frequency=data["run_frequency"],
            llm_provider=data["llm_provider"],
            llm_model=data["llm_model"],
            ollama_base_url=data.get("ollama_base_url", "http://localhost:11434"),
            asset_class=AssetClass(data.get("asset_class", AssetClass.STOCKS.value)),
            agent_mode=data.get("agent_mode", "langgraph"),
            debate_config=debate_config,
            scheduler_enabled=bool(data.get("scheduler_enabled", False)),
            auto_apply_trades=bool(data.get("auto_apply_trades", False)),
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

        # Handle empty or corrupt state files gracefully
        if state_path.stat().st_size == 0:
            return PortfolioState(cash=initial_amount)

        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        holdings = [
            Holding(
                ticker=h.get("ticker", h.get("isin", "UNKNOWN")),
                name=h.get("name", h.get("ticker", "Unknown")),
                quantity=float(h["quantity"]),
                avg_price=float(h["avg_price"]),
                stop_loss_price=h.get("stop_loss_price"),
                take_profit_price=h.get("take_profit_price"),
            )
            for h in data.get("holdings", [])
        ]

        trades = [
            Trade(
                timestamp=self._to_naive_datetime(datetime.fromisoformat(t["timestamp"])),
                ticker=t.get("ticker", t.get("isin", "UNKNOWN")),
                name=t.get("name", t.get("ticker", "Unknown")),
                action=t["action"],
                quantity=float(t["quantity"]),
                price=float(t["price"]),
                reasoning=t["reasoning"],
                stop_loss_price=t.get("stop_loss_price"),
                take_profit_price=t.get("take_profit_price"),
            )
            for t in data.get("trades", [])
        ]

        last_execution = None
        if data.get("last_execution"):
            last_execution = self._to_naive_datetime(datetime.fromisoformat(data["last_execution"]))

        # Calculate initial_investment from trade history if not recorded
        initial_investment = data.get("initial_investment")
        if initial_investment is None and trades:
            # Reverse trades to find initial cash
            reconstructed_cash = float(data["cash"])
            for trade in trades:
                if trade.action == "BUY":
                    reconstructed_cash += trade.price * trade.quantity
                else:  # SELL
                    reconstructed_cash -= trade.price * trade.quantity
            initial_investment = reconstructed_cash

        return PortfolioState(
            cash=float(data["cash"]),
            holdings=holdings,
            trades=trades,
            last_execution=last_execution,
            initial_investment=initial_investment,
        )

    def load_portfolio(self, name: str) -> tuple[PortfolioConfig, PortfolioState]:
        """Load a portfolio's config and state."""
        config = self._load_config(name)
        state = self._load_state(name, config.initial_amount)
        return config, state

    def save_config(self, config: PortfolioConfig, filename: str | None = None) -> None:
        """Save portfolio configuration to YAML."""
        target_name = filename or config.name
        config_path = self.portfolios_dir / f"{target_name}.yaml"

        data = {
            "name": config.name,
            "strategy_prompt": config.strategy_prompt,
            "initial_amount": float(config.initial_amount),
            "num_initial_trades": int(config.num_initial_trades),
            "trades_per_run": int(config.trades_per_run),
            "run_frequency": config.run_frequency,
            "llm_provider": config.llm_provider,
            "llm_model": config.llm_model,
            "ollama_base_url": config.ollama_base_url,
            "asset_class": config.asset_class.value,
            "agent_mode": config.agent_mode,
            "scheduler_enabled": bool(config.scheduler_enabled),
            "auto_apply_trades": bool(config.auto_apply_trades),
        }

        if config.debate_config:
            data["debate_config"] = {
                "rounds": config.debate_config.rounds,
                "include_neutral": config.debate_config.include_neutral,
            }

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def save_state(self, name: str, state: PortfolioState) -> None:
        """Save portfolio state to JSON."""
        state_path = self.state_dir / f"{name}.json"

        data = {
            "cash": state.cash,
            "holdings": [
                {
                    "ticker": h.ticker,
                    "name": h.name,
                    "quantity": h.quantity,
                    "avg_price": h.avg_price,
                    "stop_loss_price": h.stop_loss_price,
                    "take_profit_price": h.take_profit_price,
                }
                for h in state.holdings
            ],
            "trades": [
                {
                    "timestamp": t.timestamp.isoformat(),
                    "ticker": t.ticker,
                    "name": t.name,
                    "action": t.action,
                    "quantity": t.quantity,
                    "price": t.price,
                    "reasoning": t.reasoning,
                    "stop_loss_price": t.stop_loss_price,
                    "take_profit_price": t.take_profit_price,
                }
                for t in state.trades
            ],
            "last_execution": (
                state.last_execution.isoformat() if state.last_execution else None
            ),
            "initial_investment": state.initial_investment,
        }

        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def calculate_value(self, state: PortfolioState) -> float:
        """Calculate total portfolio value (cash + holdings)."""
        total = float(state.cash)
        for holding in state.holdings:
            price = self.security_service.get_price(holding.ticker)
            total += float(price) * holding.quantity
        return total

    def calculate_gain(
        self, config: PortfolioConfig, state: PortfolioState
    ) -> tuple[float, float]:
        """Calculate absolute and percentage gain/loss."""
        current_value = self.calculate_value(state)
        # Use actual initial investment if recorded, otherwise fall back to config
        initial = float(state.initial_investment or config.initial_amount)
        absolute_gain = current_value - initial
        percentage_gain = (absolute_gain / initial) * 100 if initial > 0 else 0.0
        return float(absolute_gain), float(percentage_gain)

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
        ticker: str,
        action: Literal["BUY", "SELL"],
        quantity: float,
        reasoning: str,
        stop_loss_price: float | None = None,
        take_profit_price: float | None = None,
        asset_class: AssetClass = AssetClass.STOCKS,
    ) -> PortfolioState:
        """Execute a trade and return updated state."""
        quantity = float(quantity)
        if quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}. Must be greater than 0.")
        if asset_class == AssetClass.STOCKS and not quantity.is_integer():
            raise ValueError(f"Stock quantities must be whole numbers, got {quantity}.")

        self.security_service.validate_ticker_for_asset_class(ticker, asset_class)

        # Lookup security info from ticker
        security = self.security_service.lookup_ticker(ticker)
        # Force update price when executing trades to ensure fresh data
        price = self.security_service.force_update_price(ticker)
        cost = price * quantity

        holdings = list(state.holdings)
        trades = list(state.trades)
        cash = state.cash

        if action == "BUY":
            if cost > cash:
                raise ValueError(f"Insufficient cash: need {cost}, have {cash}")

            cash -= cost
            existing = next((h for h in holdings if h.ticker == ticker), None)
            if existing:
                total_qty = existing.quantity + quantity
                avg_price = (
                    (existing.avg_price * existing.quantity) + (price * quantity)
                ) / total_qty
                holdings = [h for h in holdings if h.ticker != ticker]
                # Use new SL/TP if provided, otherwise keep existing
                holdings.append(Holding(
                    ticker=security.ticker,
                    name=security.name,
                    quantity=total_qty,
                    avg_price=avg_price,
                    stop_loss_price=stop_loss_price or existing.stop_loss_price,
                    take_profit_price=take_profit_price or existing.take_profit_price,
                ))
            else:
                holdings.append(Holding(
                    ticker=security.ticker,
                    name=security.name,
                    quantity=quantity,
                    avg_price=price,
                    stop_loss_price=stop_loss_price,
                    take_profit_price=take_profit_price,
                ))

        elif action == "SELL":
            existing = next((h for h in holdings if h.ticker == ticker), None)
            if not existing or existing.quantity < quantity:
                raise ValueError(
                    f"Insufficient holdings: need {quantity}, have {existing.quantity if existing else 0}"
                )

            cash += cost
            new_qty = existing.quantity - quantity
            holdings = [h for h in holdings if h.ticker != ticker]
            if new_qty > 0:
                holdings.append(Holding(
                    ticker=existing.ticker,
                    name=existing.name,
                    quantity=new_qty,
                    avg_price=existing.avg_price,
                    stop_loss_price=existing.stop_loss_price,
                    take_profit_price=existing.take_profit_price,
                ))

        trade = Trade(
            timestamp=datetime.now(),
            ticker=security.ticker,
            name=security.name,
            action=action,
            quantity=quantity,
            price=price,
            reasoning=reasoning,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
        )
        trades.append(trade)

        return PortfolioState(
            cash=cash,
            holdings=holdings,
            trades=trades,
            last_execution=datetime.now(),
            initial_investment=state.initial_investment,
        )

    def _validate_portfolio_name(self, name: str) -> None:
        """Validate portfolio name for filesystem safety.

        Raises:
            ValueError: If name is invalid or contains forbidden characters.
        """
        if not name or not name.strip():
            raise ValueError("Portfolio name cannot be empty")

        # Check for invalid filename characters
        invalid_chars = r'[<>:"/\\|?*]'
        if re.search(invalid_chars, name):
            raise ValueError(
                f"Portfolio name contains invalid characters. "
                f"Avoid: < > : \" / \\ | ? *"
            )

        # Check for reserved names (Windows)
        reserved = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
                    "LPT1", "LPT2", "LPT3", "LPT4"}
        if name.upper() in reserved:
            raise ValueError(f"'{name}' is a reserved name and cannot be used")

    def clone_portfolio(
        self, source_name: str, new_name: str, include_state: bool = False
    ) -> PortfolioConfig:
        """Clone a portfolio configuration.

        Args:
            source_name: Name of the portfolio to clone.
            new_name: Name for the new portfolio.
            include_state: If True, also copy the state JSON. If False, new
                portfolio starts fresh (no state file).

        Returns:
            The cloned PortfolioConfig.

        Raises:
            FileNotFoundError: If source portfolio doesn't exist.
            ValueError: If new_name already exists or contains invalid characters.
        """
        # Validate new name
        self._validate_portfolio_name(new_name)

        # Check source exists
        source_config_path = self.portfolios_dir / f"{source_name}.yaml"
        if not source_config_path.exists():
            raise FileNotFoundError(f"Source portfolio not found: {source_name}")

        # Check new name doesn't exist
        new_config_path = self.portfolios_dir / f"{new_name}.yaml"
        if new_config_path.exists():
            raise ValueError(f"Portfolio already exists: {new_name}")

        # Load and modify config
        with open(source_config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Update the name in the config
        config_data["name"] = new_name

        # Write new config file
        with open(new_config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        # Copy state if requested
        if include_state:
            source_state_path = self.state_dir / f"{source_name}.json"
            if source_state_path.exists():
                new_state_path = self.state_dir / f"{new_name}.json"
                shutil.copy2(source_state_path, new_state_path)

        return self._load_config(new_name)

    def reset_portfolio(self, name: str, archive: bool = True) -> None:
        """Reset portfolio to initial state.

        Args:
            name: Name of the portfolio to reset.
            archive: If True, move current state to data/state/archive/ before reset.

        Raises:
            FileNotFoundError: If portfolio config doesn't exist.
        """
        # Verify config exists
        config = self._load_config(name)

        state_path = self.state_dir / f"{name}.json"

        # Archive existing state if requested and state file exists
        if archive and state_path.exists():
            archive_dir = self.state_dir / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = archive_dir / f"{name}_{timestamp}.json"
            shutil.move(str(state_path), str(archive_path))
        elif state_path.exists():
            # Delete without archiving
            state_path.unlink()

        # Create fresh state with initial amount from config
        fresh_state = PortfolioState(
            cash=config.initial_amount,
            holdings=[],
            trades=[],
            last_execution=None,
            initial_investment=None,
        )
        self.save_state(name, fresh_state)

    def delete_portfolio(self, name: str, archive_state: bool = True) -> None:
        """Delete a portfolio configuration and optionally archive its state.

        Args:
            name: Name of the portfolio to delete.
            archive_state: If True, archive state before deleting. If False,
                delete both config and state.

        Raises:
            FileNotFoundError: If portfolio config doesn't exist.
        """
        config_path = self.portfolios_dir / f"{name}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Portfolio not found: {name}")

        state_path = self.state_dir / f"{name}.json"

        # Archive state if requested
        if archive_state and state_path.exists():
            archive_dir = self.state_dir / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = archive_dir / f"{name}_{timestamp}.json"
            shutil.move(str(state_path), str(archive_path))
        elif state_path.exists():
            state_path.unlink()

        # Delete config
        config_path.unlink()
