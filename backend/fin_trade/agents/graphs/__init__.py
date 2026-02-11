"""LangGraph graph definitions."""

from fin_trade.agents.graphs.debate_agent import build_debate_agent_graph
from fin_trade.agents.graphs.simple_agent import build_simple_agent_graph

__all__ = ["build_simple_agent_graph", "build_debate_agent_graph"]
