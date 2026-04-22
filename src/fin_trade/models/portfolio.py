"""Portfolio-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal


class AssetClass(str, Enum):
    """Supported portfolio asset classes."""

    STOCKS = "stocks"
    CRYPTO = "crypto"


@dataclass
class Holding:
    """Represents a holding in a portfolio."""

    ticker: str
    name: str
    quantity: float
    avg_price: float
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    # Optional US/primary symbol to use for business-level fundamentals
    # (sector, analyst targets, earnings, insider trades) when the traded
    # listing has sparse yfinance data. Prices always come from `ticker`.
    fundamentals_ticker: str | None = None


@dataclass
class Trade:
    """Represents a trade execution."""

    timestamp: datetime
    ticker: str
    name: str
    action: Literal["BUY", "SELL"]
    quantity: float
    price: float
    reasoning: str
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    realized_pnl: float | None = None
    # Snapshot of the listing's native currency at trade time so historical
    # P/L conversion doesn't depend on re-fetching yfinance later.
    currency: str | None = None


@dataclass
class DebateConfig:
    """Configuration for debate agent mode."""

    rounds: int = 2  # Number of debate rounds
    include_neutral: bool = True  # Include neutral analyst


@dataclass
class PortfolioConfig:
    """Configuration for a portfolio loaded from YAML."""

    name: str
    strategy_prompt: str
    initial_amount: float
    num_initial_trades: int
    trades_per_run: int
    run_frequency: Literal["daily", "weekly", "monthly"]
    llm_provider: Literal["anthropic", "openai", "ollama"]
    llm_model: str
    llm_reasoning: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    asset_class: AssetClass = AssetClass.STOCKS
    agent_mode: Literal["simple", "langgraph", "debate"] = "langgraph"
    debate_config: DebateConfig | None = None
    # Currency used for display/prompts/UI. Native prices and avg_price are
    # stored untouched; conversion happens at read time via FxService.
    display_currency: str = "USD"


@dataclass
class PortfolioState:
    """Runtime state of a portfolio."""

    cash: float
    holdings: list[Holding] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    last_execution: datetime | None = None
    initial_investment: float | None = None  # Actual amount invested (set on first trades)
