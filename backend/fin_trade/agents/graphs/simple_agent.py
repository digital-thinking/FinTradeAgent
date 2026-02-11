"""Simple agent graph - single LLM workflow with research, analysis, and trade generation."""

from langgraph.graph import END, StateGraph

from backend.fin_trade.agents.nodes import (
    analysis_node,
    generate_trades_node,
    research_node,
    validate_node,
)
from backend.fin_trade.agents.state import SimpleAgentState

MAX_RETRIES = 3


def should_retry(state: SimpleAgentState) -> str:
    """Determine whether to retry trade generation or end the workflow.

    Returns:
        "retry" if validation failed and retries remain
        "end" if validation passed or max retries reached
    """
    error = state.get("error")
    retry_count = state.get("retry_count", 0)
    recommendations = state.get("recommendations")

    if error and retry_count < MAX_RETRIES:
        return "retry"
    elif recommendations is not None:
        return "end"
    else:
        # Max retries reached or other failure
        return "end"


def build_simple_agent_graph() -> StateGraph:
    """Build the simple agent workflow graph.

    Flow:
        START -> research -> analysis -> generate -> validate -> END
                                            ^           |
                                            |   (retry) |
                                            +-----------+

    Returns:
        Compiled LangGraph StateGraph
    """
    graph = StateGraph(SimpleAgentState)

    # Add nodes
    graph.add_node("research", research_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("generate", generate_trades_node)
    graph.add_node("validate", validate_node)

    # Define edges
    graph.set_entry_point("research")
    graph.add_edge("research", "analysis")
    graph.add_edge("analysis", "generate")
    graph.add_edge("generate", "validate")

    # Conditional edge from validate: retry or end
    graph.add_conditional_edges(
        "validate",
        should_retry,
        {
            "retry": "generate",  # Loop back to generate on validation failure
            "end": END,
        },
    )

    return graph.compile()
