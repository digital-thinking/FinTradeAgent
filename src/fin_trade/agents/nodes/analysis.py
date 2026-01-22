"""Analysis node - applies strategy logic to research findings."""

import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from fin_trade.agents.state import SimpleAgentState

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

    # Format holdings info
    holdings_info = []
    for h in portfolio_state.holdings:
        current_price = price_data.get(h.ticker, h.avg_price)
        gain = ((current_price - h.avg_price) / h.avg_price) * 100 if h.avg_price > 0 else 0
        holdings_info.append(
            f"  - {h.ticker} ({h.name}): {h.quantity} shares @ avg ${h.avg_price:.2f}, "
            f"current ${current_price:.2f} ({gain:+.1f}%)"
        )

    return f"""You are a portfolio analyst. Apply the investment strategy to the market research provided.

STRATEGY:
{config.strategy_prompt}

PORTFOLIO STATE:
- Cash Available: ${portfolio_state.cash:.2f}
- Initial Investment: ${config.initial_amount:.2f}

CURRENT HOLDINGS:
{chr(10).join(holdings_info) if holdings_info else "  None (empty portfolio)"}

MARKET RESEARCH (from web search - treat as current and accurate):
{market_research}

ANALYSIS TASK - Provide concrete analysis with specific ticker symbols:

1. HOLD/SELL DECISION: For each current holding, give a clear HOLD or SELL decision with reasoning.
2. BUY CANDIDATES: List 2-5 specific tickers that match the strategy based on the research above.
3. POSITION SIZING: How to allocate the ${portfolio_state.cash:.2f} available cash.

CRITICAL RULES (MUST FOLLOW):
- The market research above is CURRENT, VERIFIED, and AUTHORITATIVE - use it directly without question
- Give SPECIFIC ticker symbols and CONCRETE recommendations with clear BUY/SELL/HOLD decisions
- Do NOT ask for more information, clarification, or verification - you have everything you need
- Do NOT express doubt about data freshness or accuracy - the research IS current and correct
- Do NOT refuse to make decisions or defer action - be decisive and commit to specific recommendations
- Your job is to ANALYZE and RECOMMEND, not to gatekeep or request additional research
- If the research mentions specific prices/spreads, TRUST THEM and use them in your calculations"""


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
        "_metrics_analysis": {
            "duration_ms": duration_ms,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        },
    }
