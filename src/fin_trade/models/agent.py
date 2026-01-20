"""Agent-related data models."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TradeRecommendation:
    """A single trade recommendation from the agent."""

    isin: str
    action: Literal["BUY", "SELL"]
    quantity: int
    reasoning: str


@dataclass
class AgentRecommendation:
    """Complete recommendation response from the agent."""

    trades: list[TradeRecommendation] = field(default_factory=list)
    overall_reasoning: str = ""
