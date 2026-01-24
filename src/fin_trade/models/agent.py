"""Agent-related data models."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TradeRecommendation:
    """A single trade recommendation from the agent."""

    ticker: str
    name: str
    action: Literal["BUY", "SELL"]
    quantity: int
    reasoning: str
    stop_loss_price: float | None = None  # Required for BUY orders
    take_profit_price: float | None = None  # Required for BUY orders


@dataclass
class AgentRecommendation:
    """Complete recommendation response from the agent."""

    trades: list[TradeRecommendation] = field(default_factory=list)
    overall_reasoning: str = ""
