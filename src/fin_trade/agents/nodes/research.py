"""Research node - gathers market data via web search."""

import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from fin_trade.agents.state import SimpleAgentState
from fin_trade.agents.tools.price_lookup import get_stock_prices
from fin_trade.services.security import SecurityService

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

    return f"""You are a market research assistant. Your task is to gather current market information
relevant to the following investment strategy:

STRATEGY:
{config.strategy_prompt}

CURRENT HOLDINGS:
{holdings_info}

RESEARCH TASK:
1. Search for current market conditions and relevant news
2. Look up information about sectors or stocks relevant to this strategy
3. Find any recent developments that could impact trading decisions
4. Focus on actionable, current information (not general market education)

Provide a concise summary of your findings organized by:
- Overall market conditions
- Sector-specific news (if relevant to strategy)
- Individual stock news (for current holdings and potential opportunities)
- Key risks or catalysts to watch

Keep the summary focused and relevant to the strategy. No fluff."""


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
        request_params["web_search_options"] = {"search_context_size": "medium"}

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

    # Build and execute research prompt
    prompt = _build_research_prompt(state)

    start_time = time.time()

    if config.llm_provider == "openai":
        response = _invoke_research_openai(prompt, config.llm_model)
    elif config.llm_provider == "anthropic":
        response = _invoke_research_anthropic(prompt, config.llm_model)
    else:
        raise ValueError(f"Unknown LLM provider: {config.llm_provider}")

    duration_ms = int((time.time() - start_time) * 1000)

    # Get current prices for holdings
    holdings_tickers = [h.ticker for h in portfolio_state.holdings]
    security_service = SecurityService()
    price_data = get_stock_prices(holdings_tickers, security_service)

    return {
        "market_research": response.text,
        "price_data": price_data,
        "_metrics_research": {
            "duration_ms": duration_ms,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        },
    }
