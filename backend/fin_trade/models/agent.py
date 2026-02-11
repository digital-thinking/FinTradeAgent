"""Agent-related data models."""

from dataclasses import dataclass, field
from typing import Literal, Optional
from datetime import datetime


@dataclass
class TradeRecommendation:
    """A single trade recommendation from the agent."""

    ticker: str
    name: str
    action: Literal["BUY", "SELL"]
    quantity: float
    reasoning: str
    stop_loss_price: float | None = None  # Required for BUY orders
    take_profit_price: float | None = None  # Required for BUY orders


@dataclass
class ExecutionResult:
    """Result of an agent execution."""
    portfolio_name: str
    success: bool
    duration_ms: float
    trades_executed: int = 0
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    agent_mode: str = ""
    model: str = ""


@dataclass
class AgentRecommendation:
    """Complete recommendation response from the agent."""

    trades: list[TradeRecommendation] = field(default_factory=list)
    overall_reasoning: str = ""
