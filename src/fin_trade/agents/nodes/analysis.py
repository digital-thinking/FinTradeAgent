"""Analysis node - applies strategy logic to research findings."""

import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from fin_trade.agents.state import SimpleAgentState
from fin_trade.prompts import ANALYSIS_PROMPT

# Load environment variables
_project_root = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(_project_root / ".env")


@dataclass
class LLMResponse:
    """Response from an LLM call with metrics."""

    text: str
    input_tokens: int
    output_tokens: int


def _build_analysis_prompt(state: SimpleAgentState) -> str:
    """Build the prompt for the analysis phase."""
    config = state["portfolio_config"]
    portfolio_state = state["portfolio_state"]
    market_research = state.get("market_research", "No research available")
    price_data = state.get("price_data", {})
    user_context = state.get("user_context")

    # Format holdings info
    holdings_info = []
    for h in portfolio_state.holdings:
        current_price = price_data.get(h.ticker, h.avg_price)
        gain = ((current_price - h.avg_price) / h.avg_price) * 100 if h.avg_price > 0 else 0
        holdings_info.append(
            f"  - {h.ticker} ({h.name}): {h.quantity} shares @ avg ${h.avg_price:.2f}, "
            f"current ${current_price:.2f} ({gain:+.1f}%)"
        )

    # Build user context section if provided
    user_context_section = ""
    if user_context:
        user_context_section = f"""
USER GUIDANCE (from portfolio manager - incorporate this into your analysis):
{user_context}

"""

    return ANALYSIS_PROMPT.format(
        user_context_section=user_context_section,
        strategy_prompt=config.strategy_prompt,
        cash=portfolio_state.cash,
        initial_amount=config.initial_amount,
        holdings_info="\n".join(holdings_info) if holdings_info else "  None (empty portfolio)",
        market_research=market_research,
    )


def _invoke_analysis_openai(prompt: str, model: str) -> LLMResponse:
    """Invoke OpenAI for analysis (no web search needed)."""
    import openai

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = openai.OpenAI(api_key=api_key)

    uses_new_token_param = any(
        model.startswith(prefix) for prefix in ("gpt-5", "o1", "o3", "o4")
    )

    request_params = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    if uses_new_token_param:
        request_params["max_completion_tokens"] = 2048
    else:
        request_params["max_tokens"] = 2048

    response = client.chat.completions.create(**request_params)

    input_tokens = 0
    output_tokens = 0
    if response.usage:
        input_tokens = response.usage.prompt_tokens or 0
        output_tokens = response.usage.completion_tokens or 0

    return LLMResponse(
        text=response.choices[0].message.content or "",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _invoke_analysis_anthropic(prompt: str, model: str) -> LLMResponse:
    """Invoke Anthropic for analysis (no web search needed)."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    result_text = ""
    for block in message.content:
        if hasattr(block, "text"):
            result_text += block.text

    input_tokens = getattr(message.usage, "input_tokens", 0) or 0
    output_tokens = getattr(message.usage, "output_tokens", 0) or 0

    return LLMResponse(
        text=result_text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def analysis_node(state: SimpleAgentState) -> dict:
    """Analysis node: applies strategy logic to research findings.

    Updates state with:
    - analysis: Strategy-specific analysis of opportunities
    - _metrics_analysis: Metrics for this step
    """
    config = state["portfolio_config"]

    prompt = _build_analysis_prompt(state)

    start_time = time.time()

    if config.llm_provider == "openai":
        response = _invoke_analysis_openai(prompt, config.llm_model)
    elif config.llm_provider == "anthropic":
        response = _invoke_analysis_anthropic(prompt, config.llm_model)
    else:
        raise ValueError(f"Unknown LLM provider: {config.llm_provider}")

    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "analysis": response.text,
        "_prompt_analysis": prompt,
        "_metrics_analysis": {
            "duration_ms": duration_ms,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        },
    }
