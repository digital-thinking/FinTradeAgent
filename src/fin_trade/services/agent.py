"""Agent service for LLM-powered trading recommendations."""

import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from fin_trade.models import (
    AgentRecommendation,
    PortfolioConfig,
    PortfolioState,
    TradeRecommendation,
)
from fin_trade.services.security import SecurityService
from fin_trade.services.llm_provider import LLMProviderFactory
from fin_trade.prompts import SIMPLE_AGENT_PROMPT

# Load .env file from project root
# agent.py -> services -> fin_trade -> src -> project_root
_project_root = Path(__file__).parent.parent.parent.parent
_env_path = _project_root / ".env"
_logs_dir = _project_root / "data" / "logs"
load_dotenv(_env_path)


class AgentService:
    """Service for invoking LLM agents to get trading recommendations."""

    def __init__(self, security_service: SecurityService | None = None):
        self.security_service = security_service or SecurityService()
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
                current_price = self.security_service.get_price(h.ticker)
                gain = ((current_price - h.avg_price) / h.avg_price) * 100
                holdings_info.append(
                    f"  - {h.ticker} ({h.name}): "
                    f"{h.quantity} shares @ avg ${h.avg_price:.2f}, "
                    f"current ${current_price:.2f} ({gain:+.1f}%)"
                )
            except Exception:
                holdings_info.append(
                    f"  - {h.ticker} ({h.name}): {h.quantity} shares @ avg ${h.avg_price:.2f}"
                )

        trades_info = []
        for t in state.trades:
            trades_info.append(
                f"  - {t.timestamp.strftime('%Y-%m-%d')}: {t.action} {t.quantity} "
                f"{t.ticker} ({t.name}) @ ${t.price:.2f}"
            )

        return SIMPLE_AGENT_PROMPT.format(
            strategy_prompt=config.strategy_prompt,
            cash=state.cash,
            initial_amount=config.initial_amount,
            holdings_info="\n".join(holdings_info) if holdings_info else "  None",
            trades_info="\n".join(trades_info) if trades_info else "  None",
            trades_per_run=config.trades_per_run,
            num_initial_trades=config.num_initial_trades,
        )

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
                    ticker=t["ticker"],
                    name=t.get("name", t["ticker"]),  # Fallback to ticker if name missing
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

    def execute(
        self, config: PortfolioConfig, state: PortfolioState
    ) -> AgentRecommendation:
        """Execute the agent to get trading recommendations."""
        prompt = self._build_prompt(config, state)

        provider = LLMProviderFactory.get_provider(config.llm_provider)
        response = provider.generate(prompt, config.llm_model)

        # Save log for debugging
        self._save_log(
            portfolio_name=config.name,
            prompt=prompt,
            response=response,
            provider=config.llm_provider,
            model=config.llm_model,
        )

        return self._parse_response(response)
