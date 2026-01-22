"""Generate trades node - creates specific trade recommendations."""

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from fin_trade.agents.state import SimpleAgentState
from fin_trade.models import AgentRecommendation, TradeRecommendation

# Load environment variables
_project_root = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(_project_root / ".env")


@dataclass
class LLMResponse:
    """Response from an LLM call with metrics."""

    text: str
    input_tokens: int
    output_tokens: int


def _build_generate_prompt(state) -> str:
    """Build the prompt for generating trade recommendations.

    Works with both SimpleAgentState (has 'analysis') and
    DebateAgentState (has 'moderator_analysis').
    """
    config = state["portfolio_config"]
    portfolio_state = state["portfolio_state"]
    # Support both simple agent (analysis) and debate agent (moderator_analysis)
    analysis = state.get("analysis") or state.get("moderator_analysis") or "No analysis available"
    price_data = state.get("price_data", {})
    user_context = state.get("user_context")

    # Format holdings for context
    holdings_info = []
    for h in portfolio_state.holdings:
        current_price = price_data.get(h.ticker, h.avg_price)
        holdings_info.append(f"  - {h.ticker}: {h.quantity} shares @ ${current_price:.2f}")

    # Determine if this is initial portfolio setup
    is_initial = len(portfolio_state.holdings) == 0 and len(portfolio_state.trades) == 0

    if is_initial:
        trade_instruction = f"""This is a NEW PORTFOLIO. You must execute at least {config.num_initial_trades} initial trades
to establish positions. Use the full ${config.initial_amount:.2f} initial investment wisely."""
    else:
        trade_instruction = f"""Maximum {config.trades_per_run} trades allowed."""

    # Build user context section if provided
    user_context_section = ""
    if user_context:
        user_context_section = f"""
USER GUIDANCE (incorporate this into trade generation):
{user_context}

"""

    return f"""Convert the analysis into specific trade recommendations in JSON format.
{user_context_section}

ANALYSIS TO CONVERT:
{analysis}

CONSTRAINTS:
- Cash Available: ${portfolio_state.cash:.2f}
- {trade_instruction}
- Can only SELL stocks currently owned
- Can only BUY with available cash

CURRENT HOLDINGS:
{chr(10).join(holdings_info) if holdings_info else "  None (empty portfolio)"}

OUTPUT FORMAT - Return ONLY valid JSON:
{{
  "trades": [
    {{"ticker": "AAPL", "name": "Apple Inc.", "action": "BUY", "quantity": 10, "reasoning": "Brief reasoning"}}
  ],
  "overall_reasoning": "Brief summary of the trading thesis"
}}

CRITICAL RULES (MUST FOLLOW):
- You MUST generate trades based on the analysis above - do NOT return empty trades
- If analysis says SELL, generate SELL trades. If analysis says BUY, generate BUY trades.
- Use REAL ticker symbols exactly as mentioned in the analysis
- Calculate quantity: For BUY, use floor(cash_to_allocate / estimated_price)
- Keep reasoning brief (1-2 sentences per trade)
- Do NOT ask questions, request clarification, or express doubt
- Do NOT refuse to generate trades - the analysis IS your authoritative source
- Do NOT say you need verification or live data - use the analysis directly
- If the analysis recommends selling due to tight spreads, GENERATE THE SELL ORDER
- Return valid JSON only - no explanatory text before or after"""


def _parse_json_response(response_text: str) -> AgentRecommendation:
    """Parse the LLM response into an AgentRecommendation."""
    text = response_text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    data = json.loads(text)

    trades = [
        TradeRecommendation(
            ticker=t["ticker"].upper(),
            name=t.get("name", t["ticker"]),
            action=t["action"].upper(),
            quantity=int(t["quantity"]),
            reasoning=t["reasoning"],
        )
        for t in data.get("trades", [])
    ]

    return AgentRecommendation(
        trades=trades,
        overall_reasoning=data.get("overall_reasoning", ""),
    )


def _invoke_generate_openai(prompt: str, model: str) -> LLMResponse:
    """Invoke OpenAI for trade generation."""
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


def _invoke_generate_anthropic(prompt: str, model: str) -> LLMResponse:
    """Invoke Anthropic for trade generation."""
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


def generate_trades_node(state) -> dict:
    """Generate trades node: creates specific trade recommendations.

    Works with both SimpleAgentState and DebateAgentState.

    Updates state with:
    - recommendations: Parsed AgentRecommendation (or None if parsing fails)
    - error: Error message if parsing fails
    - _metrics_generate: Metrics for this step
    """
    config = state["portfolio_config"]

    prompt = _build_generate_prompt(state)

    start_time = time.time()

    if config.llm_provider == "openai":
        response = _invoke_generate_openai(prompt, config.llm_model)
    elif config.llm_provider == "anthropic":
        response = _invoke_generate_anthropic(prompt, config.llm_model)
    else:
        raise ValueError(f"Unknown LLM provider: {config.llm_provider}")

    duration_ms = int((time.time() - start_time) * 1000)

    metrics = {
        "duration_ms": duration_ms,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
    }

    try:
        recommendations = _parse_json_response(response.text)
        return {
            "recommendations": recommendations,
            "error": None,
            "_metrics_generate": metrics,
        }
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return {
            "recommendations": None,
            "error": f"Failed to parse response: {e}. Response was: {response.text[:500]}",
            "_metrics_generate": metrics,
        }
