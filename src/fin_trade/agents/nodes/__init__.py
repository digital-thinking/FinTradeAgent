"""Graph nodes for the simple agent workflow."""

from fin_trade.agents.nodes.research import research_node
from fin_trade.agents.nodes.analysis import analysis_node
from fin_trade.agents.nodes.generate import generate_trades_node
from fin_trade.agents.nodes.validate import validate_node

__all__ = [
    "research_node",
    "analysis_node",
    "generate_trades_node",
    "validate_node",
]
