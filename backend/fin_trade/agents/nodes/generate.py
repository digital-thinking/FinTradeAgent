"""Generate trades node - creates specific trade recommendations."""

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from backend.fin_trade.agents.state import SimpleAgentState
from backend.fin_trade.agents.tools.price_lookup import (
    extract_tickers_from_text,
    fetch_buy_candidate_data,
    format_buy_candidates_for_prompt,
)
from backend.fin_trade.models import AgentRecommendation, AssetClass, TradeRecommendation
from backend.fin_trade.prompts import GENERATE_TRADES_PROMPT
from backend.fin_trade.services.security import SecurityService

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
    buy_candidates_section = state.get("buy_candidates_section", "")
    unit_label = "units" if config.asset_class == AssetClass.CRYPTO else "shares"

    # Format holdings for context
    holdings_info = []
    for h in portfolio_state.holdings:
        current_price = price_data.get(h.ticker, h.avg_price)
        quantity = (
            f"{h.quantity:.8f}".rstrip("0").rstrip(".")
            if config.asset_class == AssetClass.CRYPTO
            else f"{int(h.quantity)}"
        )
        holdings_info.append(f"  - {h.ticker}: {quantity} {unit_label} @ ${current_price:.2f}")

    # Determine if this is initial portfolio setup
    is_initial = len(portfolio_state.holdings) == 0 and len(portfolio_state.trades) == 0

    if is_initial:
        trade_instruction = f"""This is a NEW PORTFOLIO. You must execute at least {config.num_initial_trades} initial trades
to establish positions. Use the full ${config.initial_amount:.2f} initial investment wisely."""
    else:
        trade_instruction = f"""Maximum {config.trades_per_run} trades allowed."""

    asset_class_rules = ""
    if config.asset_class == AssetClass.CRYPTO:
        asset_class_rules = (
            "\nASSET CLASS RULES:\n"
            "- Only recommend crypto tickers with -USD suffix.\n"
            "- Never recommend stocks or ETFs.\n"
            "- Fractional quantities are allowed and expected."
        )
    else:
        asset_class_rules = (
            "\nASSET CLASS RULES:\n"
            "- Only recommend stock tickers.\n"
            "- Crypto tickers like BTC-USD are not allowed.\n"
            "- Quantities must be whole numbers."
        )

    # Build user context section if provided
    user_context_section = ""
    if user_context:
        user_context_section = f"""
USER GUIDANCE (incorporate this into trade generation):
{user_context}

"""

    return GENERATE_TRADES_PROMPT.format(
        user_context_section=user_context_section,
        analysis=f"{analysis}{asset_class_rules}",
        cash=portfolio_state.cash,
        trade_instruction=trade_instruction,
        holdings_info="\n".join(holdings_info) if holdings_info else "  None (empty portfolio)",
        buy_candidates_section=buy_candidates_section,
    )


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
            quantity=float(t["quantity"]),
            reasoning=t["reasoning"],
            stop_loss_price=float(t["stop_loss_price"]) if t.get("stop_loss_price") else None,
            take_profit_price=float(t["take_profit_price"]) if t.get("take_profit_price") else None,
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


def _invoke_generate_ollama(prompt: str, model: str, base_url: str) -> LLMResponse:
    """Invoke Ollama for trade generation."""
    import openai

    normalized_url = base_url.rstrip("/")
    client = openai.OpenAI(
        base_url=f"{normalized_url}/v1",
        api_key="ollama",
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to connect to Ollama at {normalized_url}. "
            f"Ensure Ollama is running and model '{model}' is available."
        ) from e

    input_tokens = 0
    output_tokens = 0
    if response.usage:
        input_tokens = response.usage.prompt_tokens or 0
        output_tokens = response.usage.completion_tokens or 0

    text = response.choices[0].message.content or ""
    if not text:
        raise RuntimeError("Ollama returned an empty trade generation response")

    return LLMResponse(
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def generate_trades_node(state) -> dict:
    """Generate trades node: creates specific trade recommendations.

    Works with both SimpleAgentState and DebateAgentState.

    Extracts potential BUY candidate tickers from the analysis,
    fetches their current prices, and includes this in the prompt
    so the agent can calculate accurate trade quantities.

    Updates state with:
    - recommendations: Parsed AgentRecommendation (or None if parsing fails)
    - error: Error message if parsing fails
    - _metrics_generate: Metrics for this step
    """
    config = state["portfolio_config"]
    portfolio_state = state["portfolio_state"]

    # Extract potential BUY candidate tickers from analysis
    analysis = state.get("analysis") or state.get("moderator_analysis") or ""
    market_research = state.get("market_research", "")
    combined_text = f"{analysis}\n{market_research}"

    # Get existing holding tickers to exclude from BUY candidates
    holding_tickers = {h.ticker.upper() for h in portfolio_state.holdings}

    # Extract and filter tickers
    potential_tickers = extract_tickers_from_text(combined_text)
    buy_candidate_tickers = [t for t in potential_tickers if t not in holding_tickers]

    # Fetch BUY candidate data (prices, bid/ask) and format for prompt
    buy_candidates_section = ""
    if buy_candidate_tickers:
        security_service = SecurityService()
        candidates = fetch_buy_candidate_data(buy_candidate_tickers[:10], security_service)  # Limit to 10
        buy_candidates_section = format_buy_candidates_for_prompt(candidates)

    # Add buy_candidates_section to state for prompt building
    state_with_candidates = dict(state)
    state_with_candidates["buy_candidates_section"] = buy_candidates_section

    prompt = _build_generate_prompt(state_with_candidates)

    start_time = time.time()

    if config.llm_provider == "openai":
        response = _invoke_generate_openai(prompt, config.llm_model)
    elif config.llm_provider == "anthropic":
        response = _invoke_generate_anthropic(prompt, config.llm_model)
    elif config.llm_provider == "ollama":
        response = _invoke_generate_ollama(
            prompt,
            config.llm_model,
            config.ollama_base_url,
        )
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
            "_prompt_generate": prompt,
            "_metrics_generate": metrics,
        }
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return {
            "recommendations": None,
            "error": f"Failed to parse response: {e}. Response was: {response.text[:500]}",
            "_prompt_generate": prompt,
            "_metrics_generate": metrics,
        }
