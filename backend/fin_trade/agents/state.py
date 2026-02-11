"""State schemas for LangGraph agent workflows."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from backend.fin_trade.models import AgentRecommendation, PortfolioConfig, PortfolioState


class SimpleAgentState(TypedDict):
    """State for the simple single-agent workflow.

    This state flows through research -> analysis -> generate -> validate nodes.
    """

    # Input (provided at invocation)
    portfolio_config: PortfolioConfig
    portfolio_state: PortfolioState

    # User feedback (optional guidance from user before execution)
    user_context: str | None

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

    # Prompts (for logging/debugging)
    _prompt_research: str | None
    _prompt_analysis: str | None
    _prompt_generate: str | None


class DebateMessage(TypedDict):
    """A single message in the debate history."""

    agent: str  # "bull", "bear", "neutral"
    message: str
    round: int


class DebateAgentState(TypedDict):
    """State for the multi-agent debate workflow.

    Flow: research -> parallel(bull_pitch, bear_pitch, neutral_pitch) ->
          debate_rounds -> moderator -> generate -> validate
    """

    # Input (provided at invocation)
    portfolio_config: PortfolioConfig
    portfolio_state: PortfolioState

    # User feedback (optional guidance from user before execution)
    user_context: str | None

    # Shared research (from research node)
    market_research: str
    price_data: dict[str, float]

    # Agent pitches (round 0)
    bull_pitch: str
    bear_pitch: str
    neutral_pitch: str

    # Debate rounds
    debate_history: list[DebateMessage]
    current_round: int
    max_rounds: int

    # Moderator
    moderator_analysis: str
    final_verdict: str  # Summary of decision with reasoning

    # Output
    messages: Annotated[list, add_messages]
    recommendations: AgentRecommendation | None

    # Control flow
    retry_count: int
    error: str | None

    # Metrics (populated by each node)
    _metrics_research: dict | None
    _metrics_bull_pitch: dict | None
    _metrics_bear_pitch: dict | None
    _metrics_neutral_pitch: dict | None
    _metrics_debate: dict | None
    _metrics_moderator: dict | None
    _metrics_generate: dict | None
    _metrics_validate: dict | None

    # Prompts (for logging/debugging)
    _prompt_research: str | None
    _prompt_bull_pitch: str | None
    _prompt_bear_pitch: str | None
    _prompt_neutral_pitch: str | None
    _prompt_debate: str | None
    _prompt_moderator: str | None
    _prompt_generate: str | None
