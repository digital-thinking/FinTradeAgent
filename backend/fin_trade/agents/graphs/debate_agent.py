"""LangGraph debate agent workflow with sequential bull/bear/neutral agents.

Note: Originally designed for parallel pitch execution, but LangGraph's parallel
fan-in doesn't reliably merge state from parallel branches. Using sequential
execution instead to ensure all pitches are available for debate rounds.
"""

from langgraph.graph import END, StateGraph

from backend.fin_trade.agents.nodes.debate import (
    bear_pitch_node,
    bull_pitch_node,
    debate_round_node,
    moderator_node,
    neutral_pitch_node,
    should_continue_debate,
)
from backend.fin_trade.agents.nodes.generate import generate_trades_node
from backend.fin_trade.agents.nodes.research import research_node
from backend.fin_trade.agents.nodes.validate import validate_node
from backend.fin_trade.agents.state import DebateAgentState


def should_retry(state: DebateAgentState) -> str:
    """Determine if we should retry trade generation."""
    if state.get("error") and state.get("retry_count", 0) < 3:
        return "retry"
    elif state.get("recommendations"):
        return "end"
    else:
        return "end"  # Give up after max retries


def build_debate_agent_graph() -> StateGraph:
    """Build the debate agent graph with sequential pitch execution.

    Flow:
    1. Research: Gather market data (shared by all agents)
    2. Sequential pitches: Bull -> Bear -> Neutral (ensures state is properly accumulated)
    3. Debate rounds: Agents respond to each other (configurable number of rounds)
    4. Moderator: Synthesize debate and make decision
    5. Generate: Create trade recommendations based on moderator's verdict
    6. Validate: Check constraints, retry if needed
    """
    graph = StateGraph(DebateAgentState)

    # Add nodes
    graph.add_node("research", research_node)
    graph.add_node("bull_pitch", bull_pitch_node)
    graph.add_node("bear_pitch", bear_pitch_node)
    graph.add_node("neutral_pitch", neutral_pitch_node)
    graph.add_node("debate_round", debate_round_node)
    graph.add_node("moderator", moderator_node)
    graph.add_node("generate", generate_trades_node)
    graph.add_node("validate", validate_node)

    # Set entry point
    graph.set_entry_point("research")

    # Sequential pitch execution to ensure proper state accumulation
    # (LangGraph parallel fan-in doesn't reliably merge state from parallel branches)
    graph.add_edge("research", "bull_pitch")
    graph.add_edge("bull_pitch", "bear_pitch")
    graph.add_edge("bear_pitch", "neutral_pitch")

    # After all pitches complete, move to debate
    graph.add_edge("neutral_pitch", "debate_round")

    # Conditional: continue debate or go to moderator
    graph.add_conditional_edges(
        "debate_round",
        should_continue_debate,
        {
            "debate": "debate_round",
            "moderator": "moderator",
        },
    )

    # Moderator to generate
    graph.add_edge("moderator", "generate")

    # Generate to validate
    graph.add_edge("generate", "validate")

    # Conditional: retry or end
    graph.add_conditional_edges(
        "validate",
        should_retry,
        {
            "retry": "generate",
            "end": END,
        },
    )

    return graph.compile()
