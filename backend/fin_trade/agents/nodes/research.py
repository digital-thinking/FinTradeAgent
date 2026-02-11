"""Research node - gathers market data via web search."""

import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from fin_trade.agents.state import SimpleAgentState
from fin_trade.agents.tools.price_lookup import get_stock_prices
from fin_trade.models import AssetClass
from fin_trade.services.security import SecurityService
from fin_trade.prompts import RESEARCH_PROMPT

# Load environment variables
_project_root = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(_project_root / ".env")


@dataclass
class LLMResponse:
    """Response from an LLM call with metrics."""

    text: str
    input_tokens: int
    output_tokens: int


def _build_research_prompt(state) -> str:
    """Build the prompt for the research phase."""
    config = state["portfolio_config"]
    portfolio_state = state["portfolio_state"]

    # Get current holdings tickers for price lookup
    holdings_tickers = [h.ticker for h in portfolio_state.holdings]
    holdings_info = ", ".join(holdings_tickers) if holdings_tickers else "None"

    if config.asset_class == AssetClass.CRYPTO:
        return f"""You are a crypto market research assistant.

STRATEGY:
{config.strategy_prompt}

CURRENT HOLDINGS:
{holdings_info}

RESEARCH TASK:
1. Gather current crypto market conditions and macro signals.
2. Find actionable, recent catalysts for major crypto assets.
3. Focus on REAL crypto tickers in Yahoo format (BTC-USD, ETH-USD, SOL-USD).
4. Do not include stocks or ETFs.
5. Prioritize concise insights useful for immediate trading decisions.
"""

    return RESEARCH_PROMPT.format(
        strategy_prompt=config.strategy_prompt,
        holdings_info=holdings_info,
    )


def _build_local_research_prompt(state, price_data: dict[str, float]) -> str:
    """Build a local-only research prompt for providers without web search."""
    config = state["portfolio_config"]
    portfolio_state = state["portfolio_state"]

    if portfolio_state.holdings:
        holdings_lines = []
        for holding in portfolio_state.holdings:
            price = price_data.get(holding.ticker, holding.avg_price)
            holdings_lines.append(
                f"- {holding.ticker}: qty={holding.quantity}, avg=${holding.avg_price:.2f}, "
                f"latest=${price:.2f}"
            )
        holdings_context = "\n".join(holdings_lines)
    else:
        holdings_context = "None"

    return f"""You are a market research assistant running in local mode without web search.

STRATEGY:
{config.strategy_prompt}

CURRENT HOLDINGS AND CACHED PRICES:
{holdings_context}

RESEARCH RULES:
1. Use only the portfolio context and cached prices provided above.
2. Do not claim to have accessed live web/news/search data.
3. Focus on risk, momentum, and position management guidance from available data.
4. If data is insufficient, explicitly state uncertainty and what is missing.
"""


def _invoke_research_openai(prompt: str, model: str) -> LLMResponse:
    """Invoke OpenAI with web search for research."""
    import openai

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = openai.OpenAI(api_key=api_key)

    # Map to search-enabled models
    search_models = {
        "gpt-4o": "gpt-4o-search-preview",
        "gpt-4o-mini": "gpt-4o-mini-search-preview",
        "gpt-5": "gpt-5-search-api",
        "gpt-5-mini": "gpt-5-mini-search-api",
        "gpt-5.1": "gpt-5-search-api",
        "gpt-5.2": "gpt-5-search-api",
    }
    actual_model = search_models.get(model, model)

    uses_new_token_param = any(
        actual_model.startswith(prefix) for prefix in ("gpt-5", "o1", "o3", "o4")
    )

    request_params = {
        "model": actual_model,
        "messages": [{"role": "user", "content": prompt}],
    }

    if uses_new_token_param:
        request_params["max_completion_tokens"] = 2048
    else:
        request_params["max_tokens"] = 2048

    if "search" in actual_model:
        request_params["web_search_options"] = {"search_context_size": "low"}

    response = client.chat.completions.create(**request_params)

    # Extract token usage (may be None for some models)
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


def _invoke_research_anthropic(prompt: str, model: str) -> LLMResponse:
    """Invoke Anthropic with web search for research."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=model,
        max_tokens=2048,
        extra_headers={"anthropic-beta": "web-search-2025-03-05"},
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 5,
            }
        ],
        messages=[{"role": "user", "content": prompt}],
    )

    result_text = ""
    for block in message.content:
        if hasattr(block, "text"):
            result_text += block.text

    # Extract token usage
    input_tokens = getattr(message.usage, "input_tokens", 0) or 0
    output_tokens = getattr(message.usage, "output_tokens", 0) or 0

    return LLMResponse(
        text=result_text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _invoke_research_ollama(prompt: str, model: str, base_url: str) -> LLMResponse:
    """Invoke Ollama without web search."""
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
        raise RuntimeError("Ollama returned an empty research response")

    return LLMResponse(
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def research_node(state) -> dict:
    """Research node: gathers market data via web search.

    Works with both SimpleAgentState and DebateAgentState.

    Updates state with:
    - market_research: Summary of web search findings
    - price_data: Current prices for holdings
    - _metrics_research: Metrics for this step
    """
    config = state["portfolio_config"]
    portfolio_state = state["portfolio_state"]

    # Get current prices for holdings
    holdings_tickers = [h.ticker for h in portfolio_state.holdings]
    security_service = SecurityService()
    price_data = get_stock_prices(holdings_tickers, security_service)

    supports_web_search = config.llm_provider in {"openai", "anthropic"}
    research_warning = None

    if supports_web_search:
        prompt = _build_research_prompt(state)
    else:
        prompt = _build_local_research_prompt(state, price_data)
        research_warning = (
            "Web search is unavailable for Ollama. "
            "Research is limited to holdings and cached price context."
        )

    start_time = time.time()

    if config.llm_provider == "openai":
        response = _invoke_research_openai(prompt, config.llm_model)
    elif config.llm_provider == "anthropic":
        response = _invoke_research_anthropic(prompt, config.llm_model)
    elif config.llm_provider == "ollama":
        response = _invoke_research_ollama(
            prompt,
            config.llm_model,
            config.ollama_base_url,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {config.llm_provider}")

    duration_ms = int((time.time() - start_time) * 1000)

    result = {
        "market_research": response.text,
        "price_data": price_data,
        "_prompt_research": prompt,
        "_metrics_research": {
            "duration_ms": duration_ms,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        },
    }

    if research_warning:
        result["research_warning"] = research_warning

    return result
