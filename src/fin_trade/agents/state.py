"""State schemas for LangGraph agent workflows."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from fin_trade.models import AgentRecommendation, PortfolioConfig, PortfolioState


class SimpleAgentState(TypedDict):
    """State for the simple single-agent workflow.

    This state flows through research -> analysis -> generate -> validate nodes.
    """

    # Input (provided at invocation)
    portfolio_config: PortfolioConfig
    portfolio_state: PortfolioState

    # Research results
    market_research: str  # Web search results about market conditions
    price_data: dict[str, float]  # ticker -> current price

    # Analysis
    analysis: str  # Strategy-specific analysis

    # Output
    messages: Annotated[list, add_messages]
    recommendations: AgentRecommendation | None

    # Control flow
    retry_count: int
    error: str | None

    # Metrics (populated by each node)
    _metrics_research: dict | None
    _metrics_analysis: dict | None
    _metrics_generate: dict | None
    _metrics_validate: dict | None
