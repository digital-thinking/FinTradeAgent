"""Debate nodes - multi-agent bull/bear/neutral debate system."""

import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from fin_trade.agents.state import DebateAgentState
from fin_trade.models import AssetClass
from fin_trade.prompts import (
    BULL_PROMPT,
    BEAR_PROMPT,
    NEUTRAL_PROMPT,
    DEBATE_PROMPT,
    MODERATOR_PROMPT,
)
from fin_trade.services.market_data import MarketDataService
from fin_trade.services.reflection import ReflectionService
from fin_trade.services.security import SecurityService
from fin_trade.services.stock_data import StockDataService

# Load environment variables
_project_root = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(_project_root / ".env")


@dataclass
class LLMResponse:
    """Response from an LLM call with metrics."""

    text: str
    input_tokens: int
    output_tokens: int


def _invoke_llm(
    prompt: str,
    provider: str,
    model: str,
    ollama_base_url: str = "http://localhost:11434",
) -> LLMResponse:
    """Invoke the LLM with the given prompt."""
    if provider == "openai":
        return _invoke_openai(prompt, model)
    if provider == "anthropic":
        return _invoke_anthropic(prompt, model)
    if provider == "ollama":
        return _invoke_ollama(prompt, model, ollama_base_url)
    raise ValueError(f"Unknown LLM provider: {provider}")


def _invoke_openai(prompt: str, model: str) -> LLMResponse:
    """Invoke OpenAI."""
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
        request_params["max_completion_tokens"] = 8192
    else:
        request_params["max_tokens"] = 4096

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


def _invoke_anthropic(prompt: str, model: str) -> LLMResponse:
    """Invoke Anthropic."""
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


def _invoke_ollama(prompt: str, model: str, base_url: str) -> LLMResponse:
    """Invoke Ollama."""
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
            max_tokens=4096,
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
        raise RuntimeError("Ollama returned an empty response")

    return LLMResponse(
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _format_holdings(state: DebateAgentState) -> str:
    """Format holdings with rich price context (history, RSI, volume, MAs, short interest)."""
    config = state["portfolio_config"]
    portfolio_state = state["portfolio_state"]
    unit_label = "units" if config.asset_class == AssetClass.CRYPTO else "shares"

    if not portfolio_state.holdings:
        return "None (empty portfolio)"

    try:
        # Pass SecurityService to use stored 52w range, MAs, short interest data
        security_service = SecurityService()
        stock_data_service = StockDataService()
        return stock_data_service.format_holdings_for_prompt(
            portfolio_state.holdings,
            security_service=security_service,
            asset_class=config.asset_class,
        )
    except Exception:
        # Fallback to basic format if price context fails
        price_data = state.get("price_data", {})
        lines = []
        for h in portfolio_state.holdings:
            current_price = price_data.get(h.ticker, h.avg_price)
            gain = ((current_price - h.avg_price) / h.avg_price) * 100 if h.avg_price > 0 else 0
            quantity = (
                f"{h.quantity:.8f}".rstrip("0").rstrip(".")
                if config.asset_class == AssetClass.CRYPTO
                else f"{int(h.quantity)}"
            )
            lines.append(
                f"  - {h.ticker} ({h.name}): {quantity} {unit_label} @ avg ${h.avg_price:.2f}, "
                f"current ${current_price:.2f} ({gain:+.1f}%)"
            )
        return "\n".join(lines)


def _get_market_data_context(state: DebateAgentState) -> str:
    """Get market data context for holdings."""
    config = state["portfolio_config"]
    portfolio_state = state["portfolio_state"]

    try:
        security_service = SecurityService()
        market_data_service = MarketDataService()
        return market_data_service.get_holdings_context(
            portfolio_state.holdings,
            config.asset_class,
            security_service=security_service,
        )
    except Exception:
        return "Market data temporarily unavailable."


def _get_asset_class_rules(asset_class: AssetClass) -> str:
    """Return additional rules to enforce asset-class-specific behavior."""
    if asset_class == AssetClass.CRYPTO:
        return (
            "ASSET CLASS RULES:\n"
            "- This is a CRYPTO portfolio. Recommend only crypto tickers with -USD suffix.\n"
            "- Never recommend stocks or ETFs.\n"
            "- Use fractional quantities where appropriate."
        )
    return "ASSET CLASS RULES:\n- This is a STOCK portfolio. Do not recommend crypto tickers."


def _get_reflection_context(state: DebateAgentState) -> str:
    """Get self-reflection context on past performance."""
    portfolio_state = state["portfolio_state"]

    try:
        reflection_service = ReflectionService()
        reflection = reflection_service.analyze_performance(portfolio_state)
        return reflection.to_context_string()
    except Exception:
        return "Performance reflection temporarily unavailable."


def bull_pitch_node(state) -> dict:
    """Bull agent pitch node."""
    config = state["portfolio_config"]
    start_time = time.time()

    prompt = BULL_PROMPT.format(
        strategy=f"{config.strategy_prompt}\n\n{_get_asset_class_rules(config.asset_class)}",
        research=state.get("market_research", "No research available"),
        market_data_context=_get_market_data_context(state),
        reflection_context=_get_reflection_context(state),
        holdings=_format_holdings(state),
        cash=state["portfolio_state"].cash,
    )

    response = _invoke_llm(
        prompt,
        config.llm_provider,
        config.llm_model,
        config.ollama_base_url,
    )
    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "bull_pitch": response.text,
        "_prompt_bull_pitch": prompt,
        "_metrics_bull_pitch": {
            "duration_ms": duration_ms,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        },
    }


def bear_pitch_node(state) -> dict:
    """Bear agent pitch node."""
    config = state["portfolio_config"]
    start_time = time.time()

    prompt = BEAR_PROMPT.format(
        strategy=f"{config.strategy_prompt}\n\n{_get_asset_class_rules(config.asset_class)}",
        research=state.get("market_research", "No research available"),
        market_data_context=_get_market_data_context(state),
        reflection_context=_get_reflection_context(state),
        holdings=_format_holdings(state),
        cash=state["portfolio_state"].cash,
    )

    response = _invoke_llm(
        prompt,
        config.llm_provider,
        config.llm_model,
        config.ollama_base_url,
    )
    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "bear_pitch": response.text,
        "_prompt_bear_pitch": prompt,
        "_metrics_bear_pitch": {
            "duration_ms": duration_ms,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        },
    }


def neutral_pitch_node(state) -> dict:
    """Neutral analyst pitch node."""
    config = state["portfolio_config"]
    start_time = time.time()

    prompt = NEUTRAL_PROMPT.format(
        strategy=f"{config.strategy_prompt}\n\n{_get_asset_class_rules(config.asset_class)}",
        research=state.get("market_research", "No research available"),
        market_data_context=_get_market_data_context(state),
        reflection_context=_get_reflection_context(state),
        holdings=_format_holdings(state),
        cash=state["portfolio_state"].cash,
    )

    response = _invoke_llm(
        prompt,
        config.llm_provider,
        config.llm_model,
        config.ollama_base_url,
    )
    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "neutral_pitch": response.text,
        "_prompt_neutral_pitch": prompt,
        "_metrics_neutral_pitch": {
            "duration_ms": duration_ms,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        },
    }


def debate_round_node(state) -> dict:
    """Execute one round of debate between agents."""
    config = state["portfolio_config"]
    current_round = state.get("current_round", 1)
    max_rounds = state.get("max_rounds", 2)

    start_time = time.time()
    total_input_tokens = 0
    total_output_tokens = 0

    # Get previous statements for context
    debate_history = state.get("debate_history", [])
    if current_round == 1:
        # First round - use initial pitches
        bull_pitch = state.get('bull_pitch') or 'No pitch provided'
        bear_pitch = state.get('bear_pitch') or 'No pitch provided'
        neutral_pitch = state.get('neutral_pitch') or 'No analysis provided'

        previous_statements = f"""BULL's initial pitch:
{bull_pitch}

BEAR's initial pitch:
{bear_pitch}

NEUTRAL's initial analysis:
{neutral_pitch}"""
    else:
        # Subsequent rounds - use debate history
        prev_round = [m for m in debate_history if m["round"] == current_round - 1]
        previous_statements = "\n\n".join(
            f"{m['agent'].upper()}: {m['message']}" for m in prev_round
        )

    new_messages = []

    # Bull rebuttal
    bull_prompt = DEBATE_PROMPT.format(
        agent_role="BULL",
        round_num=current_round,
        previous_statements=previous_statements,
    )
    bull_response = _invoke_llm(
        bull_prompt,
        config.llm_provider,
        config.llm_model,
        config.ollama_base_url,
    )
    new_messages.append({"agent": "bull", "message": bull_response.text, "round": current_round})
    total_input_tokens += bull_response.input_tokens
    total_output_tokens += bull_response.output_tokens

    # Bear rebuttal
    bear_prompt = DEBATE_PROMPT.format(
        agent_role="BEAR",
        round_num=current_round,
        previous_statements=previous_statements,
    )
    bear_response = _invoke_llm(
        bear_prompt,
        config.llm_provider,
        config.llm_model,
        config.ollama_base_url,
    )
    new_messages.append({"agent": "bear", "message": bear_response.text, "round": current_round})
    total_input_tokens += bear_response.input_tokens
    total_output_tokens += bear_response.output_tokens

    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "debate_history": debate_history + new_messages,
        "current_round": current_round + 1,
        "_prompt_debate": f"BULL prompt:\n{bull_prompt}\n\nBEAR prompt:\n{bear_prompt}",
        "_metrics_debate": {
            "duration_ms": duration_ms,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
        },
    }


def moderator_node(state: DebateAgentState) -> dict:
    """Moderator synthesizes debate and provides verdict."""
    config = state["portfolio_config"]
    start_time = time.time()

    # Format debate history
    debate_history = state.get("debate_history", [])
    debate_transcript = ""
    for msg in debate_history:
        debate_transcript += f"\n[Round {msg['round']}] {msg['agent'].upper()}: {msg['message']}\n"

    # Build user context section if provided
    user_context = state.get("user_context")
    user_context_section = ""
    if user_context:
        user_context_section = f"""
PORTFOLIO MANAGER GUIDANCE (incorporate this into your decision):
{user_context}
"""

    prompt = MODERATOR_PROMPT.format(
        strategy=f"{config.strategy_prompt}\n\n{_get_asset_class_rules(config.asset_class)}",
        user_context_section=user_context_section,
        reflection_context=_get_reflection_context(state),
        bull_pitch=state.get("bull_pitch", "No pitch"),
        bear_pitch=state.get("bear_pitch", "No pitch"),
        neutral_pitch=state.get("neutral_pitch", "No analysis"),
        debate_history=debate_transcript or "No debate rounds",
        cash=state["portfolio_state"].cash,
        holdings=_format_holdings(state),
    )

    response = _invoke_llm(
        prompt,
        config.llm_provider,
        config.llm_model,
        config.ollama_base_url,
    )
    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "moderator_analysis": response.text,
        "final_verdict": response.text,  # The full analysis serves as the verdict
        "_prompt_moderator": prompt,
        "_metrics_moderator": {
            "duration_ms": duration_ms,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        },
    }


def should_continue_debate(state: DebateAgentState) -> str:
    """Determine if debate should continue or move to moderator."""
    current_round = state.get("current_round", 1)
    max_rounds = state.get("max_rounds", 2)

    if current_round <= max_rounds:
        return "debate"
    return "moderator"
