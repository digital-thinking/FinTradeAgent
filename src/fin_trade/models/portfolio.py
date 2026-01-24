"""Portfolio-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class Holding:
    """Represents a stock holding in a portfolio."""

    isin: str
    ticker: str
    name: str
    quantity: int
    avg_price: float


@dataclass
class Trade:
    """Represents a trade execution."""

    timestamp: datetime
    isin: str
    ticker: str
    name: str
    action: Literal["BUY", "SELL"]
    quantity: int
    price: float
    reasoning: str


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
    llm_provider: Literal["anthropic", "openai"]
    llm_model: str
    agent_mode: Literal["simple", "langgraph", "debate"] = "langgraph"
    debate_config: DebateConfig | None = None


@dataclass
class PortfolioState:
    """Runtime state of a portfolio."""

    cash: float
    holdings: list[Holding] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    last_execution: datetime | None = None
    initial_investment: float | None = None  # Actual amount invested (set on first trades)
