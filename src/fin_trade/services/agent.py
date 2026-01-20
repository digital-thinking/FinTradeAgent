"""Agent service for LLM-powered trading recommendations."""

import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from fin_trade.models import (
    AgentRecommendation,
    PortfolioConfig,
    PortfolioState,
    TradeRecommendation,
)
from fin_trade.services.stock_data import StockDataService

# Load .env file from project root
# agent.py -> services -> fin_trade -> src -> project_root
_project_root = Path(__file__).parent.parent.parent.parent
_env_path = _project_root / ".env"
_logs_dir = _project_root / "data" / "logs"
load_dotenv(_env_path)


class AgentService:
    """Service for invoking LLM agents to get trading recommendations."""

    def __init__(self, stock_service: StockDataService | None = None):
        self.stock_service = stock_service or StockDataService()
        # Reload .env to ensure keys are available
        load_dotenv(_env_path)
        # Ensure logs directory exists
        _logs_dir.mkdir(parents=True, exist_ok=True)

    def _save_log(
        self,
        portfolio_name: str,
        prompt: str,
        response: str,
        provider: str,
        model: str,
    ) -> None:
        """Save prompt and response to log file for debugging."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = _logs_dir / f"{portfolio_name}_{timestamp}.log"

        log_content = f"""================================================================================
AGENT LOG - {datetime.now().isoformat()}
================================================================================
Portfolio: {portfolio_name}
Provider: {provider}
Model: {model}

================================================================================
PROMPT
================================================================================
{prompt}

================================================================================
RESPONSE
================================================================================
{response}
"""
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(log_content)

    def _build_prompt(
        self, config: PortfolioConfig, state: PortfolioState
    ) -> str:
        """Build the prompt for the LLM with portfolio context."""
        holdings_info = []
        for h in state.holdings:
            try:
                ticker = self.stock_service.get_ticker(h.isin)
                current_price = self.stock_service.get_price(h.isin)
                gain = ((current_price - h.avg_price) / h.avg_price) * 100
                holdings_info.append(
                    f"  - {ticker} (ISIN: {h.isin}): "
                    f"{h.quantity} shares @ avg ${h.avg_price:.2f}, "
                    f"current ${current_price:.2f} ({gain:+.1f}%)"
                )
            except Exception:
                holdings_info.append(
                    f"  - ISIN {h.isin}: {h.quantity} shares @ avg ${h.avg_price:.2f}"
                )

        recent_trades = state.trades[-10:] if state.trades else []
        trades_info = []
        for t in recent_trades:
            try:
                ticker = self.stock_service.get_ticker(t.isin)
            except Exception:
                ticker = t.isin
            trades_info.append(
                f"  - {t.timestamp.strftime('%Y-%m-%d')}: {t.action} {t.quantity} "
                f"{ticker} @ ${t.price:.2f} - {t.reasoning[:50]}..."
            )

        prompt = f"""You are a portfolio management agent. Your strategy:

{config.strategy_prompt}

CURRENT PORTFOLIO STATE:
- Cash Available: ${state.cash:.2f}
- Initial Investment: ${config.initial_amount:.2f}

CURRENT HOLDINGS:
{chr(10).join(holdings_info) if holdings_info else "  None"}

RECENT TRADES:
{chr(10).join(trades_info) if trades_info else "  None"}

CONSTRAINTS:
- Maximum {config.trades_per_run} trades per execution
- You can only SELL stocks you currently own
- You can only BUY with available cash
- Each trade must include reasoning

STOCK IDENTIFICATION:
- You may trade ANY publicly listed stock
- Use the stock's ISIN (International Securities Identification Number) 
- The system will resolve tickers to proper identifiers automatically

Please analyze the current portfolio and market conditions based on your strategy, then provide your trading recommendations.

RESPOND WITH VALID JSON ONLY in this exact format:
{{
  "trades": [
    {{"isin": "US02079K3059", "action": "BUY", "quantity": 5, "reasoning": "Your reasoning here..."}}
  ],
  "overall_reasoning": "Your overall market analysis and strategy explanation..."
}}

If you recommend no trades, return an empty trades array with your reasoning for holding."""

        return prompt

    def _parse_response(self, response_text: str) -> AgentRecommendation:
        """Parse the LLM response into an AgentRecommendation."""
        try:
            text = response_text.strip()
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
                    isin=t["isin"],
                    action=t["action"],
                    quantity=int(t["quantity"]),
                    reasoning=t["reasoning"],
                )
                for t in data.get("trades", [])
            ]

            return AgentRecommendation(
                trades=trades,
                overall_reasoning=data.get("overall_reasoning", ""),
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}") from e

    def _invoke_anthropic(self, prompt: str, model: str) -> str:
        """Invoke Anthropic's API."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed")

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def _invoke_openai(self, prompt: str, model: str) -> str:
        """Invoke OpenAI's API."""
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed")

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set. Add it to your .env file.")

        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )
        return response.choices[0].message.content

    def execute(
        self, config: PortfolioConfig, state: PortfolioState
    ) -> AgentRecommendation:
        """Execute the agent to get trading recommendations."""
        prompt = self._build_prompt(config, state)

        if config.llm_provider == "anthropic":
            response = self._invoke_anthropic(prompt, config.llm_model)
        elif config.llm_provider == "openai":
            response = self._invoke_openai(prompt, config.llm_model)
        else:
            raise ValueError(f"Unknown LLM provider: {config.llm_provider}")

        # Save log for debugging
        self._save_log(
            portfolio_name=config.name,
            prompt=prompt,
            response=response,
            provider=config.llm_provider,
            model=config.llm_model,
        )

        return self._parse_response(response)
