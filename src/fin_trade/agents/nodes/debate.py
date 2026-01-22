"""Debate nodes - multi-agent bull/bear/neutral debate system."""

import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from fin_trade.agents.state import DebateAgentState

# Load environment variables
_project_root = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(_project_root / ".env")


@dataclass
class LLMResponse:
    """Response from an LLM call with metrics."""

    text: str
    input_tokens: int
    output_tokens: int


BULL_PROMPT = """You are the BULL on an investment committee. Your job is to find compelling
reasons to BUY. Focus on:
- Growth potential and TAM expansion
- Competitive advantages and moats
- Positive catalysts on the horizon
- Undervaluation relative to peers
- Management execution and vision

Be aggressive but not reckless. Back claims with data from the research provided.
You must advocate for the long position.

STRATEGY CONTEXT:
{strategy}

MARKET RESEARCH:
{research}

CURRENT HOLDINGS:
{holdings}

CASH AVAILABLE: ${cash:.2f}

Provide your BULL CASE analysis. Be specific about which stocks to BUY and why.
Focus on opportunities that match the strategy."""


BEAR_PROMPT = """You are the BEAR on an investment committee. Your job is to find reasons
NOT to buy or to SELL. Focus on:
- Valuation concerns and downside risk
- Competitive threats and disruption risk
- Accounting red flags or aggressive assumptions
- Macro headwinds and sector rotation
- Management credibility issues

Be thorough but not paranoid. Back concerns with specific evidence from the research.
Your job is to stress-test every idea.

STRATEGY CONTEXT:
{strategy}

MARKET RESEARCH:
{research}

CURRENT HOLDINGS:
{holdings}

CASH AVAILABLE: ${cash:.2f}

Provide your BEAR CASE analysis. Identify risks in current holdings and reasons
to avoid or reduce positions. Be specific about concerns."""


NEUTRAL_PROMPT = """You are the NEUTRAL ANALYST on an investment committee. Your job is to
provide balanced, objective analysis. Focus on:
- Fair value estimation using multiple methods
- Risk/reward asymmetry assessment
- Position sizing considerations
- Time horizon alignment with strategy
- Key metrics to monitor

Don't pick sides. Present the facts and tradeoffs clearly.

STRATEGY CONTEXT:
{strategy}

MARKET RESEARCH:
{research}

CURRENT HOLDINGS:
{holdings}

CASH AVAILABLE: ${cash:.2f}

Provide your NEUTRAL analysis. Assess fair values, risk/reward, and appropriate
position sizes. Be objective and data-driven."""


DEBATE_PROMPT = """You are the {agent_role} in round {round_num} of the investment committee debate.

PREVIOUS STATEMENTS:
{previous_statements}

Respond to the other committee members' arguments. You may:
- Rebut specific points you disagree with
- Reinforce your position with additional evidence
- Acknowledge valid points from others while maintaining your stance

Keep your response focused and under 300 words. Stay in character as the {agent_role}."""


MODERATOR_PROMPT = """You are the CIO moderating this investment committee debate.

STRATEGY BEING FOLLOWED:
{strategy}

BULL CASE:
{bull_pitch}

BEAR CASE:
{bear_pitch}

NEUTRAL ANALYSIS:
{neutral_pitch}

DEBATE TRANSCRIPT:
{debate_history}

PORTFOLIO STATE:
- Cash Available: ${cash:.2f}
- Current Holdings: {holdings}

Synthesize the debate and make a final decision. Consider:
1. Which arguments are most compelling and why?
2. What's the risk/reward asymmetry?
3. How does this fit the portfolio strategy?
4. What position size is appropriate given conviction level?

Deliver a clear verdict with specific reasoning. Your analysis should conclude with
concrete BUY/SELL/HOLD recommendations for specific tickers mentioned in the debate."""


def _invoke_llm(prompt: str, provider: str, model: str) -> LLMResponse:
    """Invoke the LLM with the given prompt."""
    if provider == "openai":
        return _invoke_openai(prompt, model)
    elif provider == "anthropic":
        return _invoke_anthropic(prompt, model)
    else:
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


def _format_holdings(state: DebateAgentState) -> str:
    """Format holdings for prompt."""
    portfolio_state = state["portfolio_state"]
    price_data = state.get("price_data", {})

    if not portfolio_state.holdings:
        return "None (empty portfolio)"

    lines = []
    for h in portfolio_state.holdings:
        current_price = price_data.get(h.ticker, h.avg_price)
        gain = ((current_price - h.avg_price) / h.avg_price) * 100 if h.avg_price > 0 else 0
        lines.append(
            f"  - {h.ticker} ({h.name}): {h.quantity} shares @ avg ${h.avg_price:.2f}, "
            f"current ${current_price:.2f} ({gain:+.1f}%)"
        )
    return "\n".join(lines)


def bull_pitch_node(state) -> dict:
    """Bull agent pitch node."""
    config = state["portfolio_config"]
    start_time = time.time()

    prompt = BULL_PROMPT.format(
        strategy=config.strategy_prompt,
        research=state.get("market_research", "No research available"),
        holdings=_format_holdings(state),
        cash=state["portfolio_state"].cash,
    )

    response = _invoke_llm(prompt, config.llm_provider, config.llm_model)
    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "bull_pitch": response.text,
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
        strategy=config.strategy_prompt,
        research=state.get("market_research", "No research available"),
        holdings=_format_holdings(state),
        cash=state["portfolio_state"].cash,
    )

    response = _invoke_llm(prompt, config.llm_provider, config.llm_model)
    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "bear_pitch": response.text,
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
        strategy=config.strategy_prompt,
        research=state.get("market_research", "No research available"),
        holdings=_format_holdings(state),
        cash=state["portfolio_state"].cash,
    )

    response = _invoke_llm(prompt, config.llm_provider, config.llm_model)
    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "neutral_pitch": response.text,
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
    bull_response = _invoke_llm(bull_prompt, config.llm_provider, config.llm_model)
    new_messages.append({"agent": "bull", "message": bull_response.text, "round": current_round})
    total_input_tokens += bull_response.input_tokens
    total_output_tokens += bull_response.output_tokens

    # Bear rebuttal
    bear_prompt = DEBATE_PROMPT.format(
        agent_role="BEAR",
        round_num=current_round,
        previous_statements=previous_statements,
    )
    bear_response = _invoke_llm(bear_prompt, config.llm_provider, config.llm_model)
    new_messages.append({"agent": "bear", "message": bear_response.text, "round": current_round})
    total_input_tokens += bear_response.input_tokens
    total_output_tokens += bear_response.output_tokens

    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "debate_history": debate_history + new_messages,
        "current_round": current_round + 1,
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

    prompt = MODERATOR_PROMPT.format(
        strategy=config.strategy_prompt,
        bull_pitch=state.get("bull_pitch", "No pitch"),
        bear_pitch=state.get("bear_pitch", "No pitch"),
        neutral_pitch=state.get("neutral_pitch", "No analysis"),
        debate_history=debate_transcript or "No debate rounds",
        cash=state["portfolio_state"].cash,
        holdings=_format_holdings(state),
    )

    response = _invoke_llm(prompt, config.llm_provider, config.llm_model)
    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "moderator_analysis": response.text,
        "final_verdict": response.text,  # The full analysis serves as the verdict
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
