"""Centralized prompt templates for LLM agents."""

from fin_trade.prompts.simple_agent import (
    SIMPLE_AGENT_PROMPT,
    RESEARCH_PROMPT,
    ANALYSIS_PROMPT,
    GENERATE_TRADES_PROMPT,
)
from fin_trade.prompts.debate_agent import (
    BULL_PROMPT,
    BEAR_PROMPT,
    NEUTRAL_PROMPT,
    DEBATE_PROMPT,
    MODERATOR_PROMPT,
)
from fin_trade.prompts.crypto_agent import CRYPTO_SYSTEM_PROMPT

__all__ = [
    # Simple agent prompts
    "SIMPLE_AGENT_PROMPT",
    "RESEARCH_PROMPT",
    "ANALYSIS_PROMPT",
    "GENERATE_TRADES_PROMPT",
    # Debate agent prompts
    "BULL_PROMPT",
    "BEAR_PROMPT",
    "NEUTRAL_PROMPT",
    "DEBATE_PROMPT",
    "MODERATOR_PROMPT",
    "CRYPTO_SYSTEM_PROMPT",
]
