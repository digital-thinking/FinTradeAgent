"""Graph nodes for agent workflows."""

from fin_trade.agents.nodes.analysis import analysis_node
from fin_trade.agents.nodes.debate import (
    bear_pitch_node,
    bull_pitch_node,
    debate_round_node,
    moderator_node,
    neutral_pitch_node,
    should_continue_debate,
)
from fin_trade.agents.nodes.generate import generate_trades_node
from fin_trade.agents.nodes.research import research_node
from fin_trade.agents.nodes.validate import validate_node

__all__ = [
    # Simple agent nodes
    "research_node",
    "analysis_node",
    "generate_trades_node",
    "validate_node",
    # Debate agent nodes
    "bull_pitch_node",
    "bear_pitch_node",
    "neutral_pitch_node",
    "debate_round_node",
    "moderator_node",
    "should_continue_debate",
]
