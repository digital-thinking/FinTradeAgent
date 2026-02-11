"""API service wrapper for PortfolioService."""

import sys
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

from backend.fin_trade.services.portfolio import PortfolioService
from backend.fin_trade.services.security import SecurityService
from backend.fin_trade.models import PortfolioConfig, PortfolioState
from backend.models.portfolio import (
    PortfolioConfigRequest,
    PortfolioResponse,
    PortfolioSummary,
    HoldingResponse,
    PortfolioStateResponse
)


class PortfolioAPIService:
    """API wrapper for PortfolioService."""
    
    def __init__(self):
        self.security_service = SecurityService()
        self.portfolio_service = PortfolioService(security_service=self.security_service)
    
    def list_portfolios(self) -> List[PortfolioSummary]:
        """List all portfolios with summary info."""
        portfolios = []
        
        for portfolio_name in self.portfolio_service.list_portfolios():
            try:
                config, state = self.portfolio_service.load_portfolio(portfolio_name)
                
                # Convert holdings to count
                holdings_count = len(state.holdings)
                
                summary = PortfolioSummary(
                    name=portfolio_name,
                    total_value=state.cash + sum(h.quantity * h.avg_price for h in state.holdings),
                    cash=state.cash,
                    holdings_count=holdings_count,
                    last_updated=state.last_execution,
                    scheduler_enabled=getattr(config, 'scheduler_enabled', False)
                )
                portfolios.append(summary)
            except Exception:
                # Skip corrupted portfolios
                continue
                
        return portfolios
    
    def get_portfolio(self, name: str) -> Optional[PortfolioResponse]:
        """Get portfolio by name."""
        try:
            config, state = self.portfolio_service.load_portfolio(name)
            
            # Convert holdings
            holdings = [
                HoldingResponse(
                    symbol=h.ticker,
                    quantity=h.quantity,
                    avg_cost=h.avg_price,
                    current_price=None  # TODO: Get current price
                )
                for h in state.holdings
            ]

            # Convert state
            state_response = PortfolioStateResponse(
                cash=state.cash,
                holdings=holdings,
                total_value=state.cash + sum(h.quantity * h.avg_price for h in state.holdings),
                last_updated=state.last_execution
            )
            
            # Convert config
            config_response = PortfolioConfigRequest(
                name=config.name,
                initial_capital=config.initial_amount,
                llm_model=config.llm_model,
                asset_class=config.asset_class.value,
                agent_mode=config.agent_mode,
                run_frequency=config.run_frequency,
                scheduler_enabled=getattr(config, 'scheduler_enabled', False),
                auto_apply_trades=getattr(config, 'auto_apply_trades', False),
                ollama_base_url=getattr(config, 'ollama_base_url', 'http://localhost:11434')
            )
            
            return PortfolioResponse(
                config=config_response,
                state=state_response
            )
        except Exception:
            return None
    
    def create_portfolio(self, config_request: PortfolioConfigRequest) -> bool:
        """Create new portfolio."""
        try:
            # Write YAML config file
            config_data = {
                "name": config_request.name,
                "strategy_prompt": "You are a portfolio manager. Recommend trades based on market analysis.",
                "initial_amount": config_request.initial_capital,
                "num_initial_trades": 5,
                "trades_per_run": 3,
                "run_frequency": config_request.run_frequency,
                "llm_provider": "openai",
                "llm_model": config_request.llm_model,
                "asset_class": config_request.asset_class,
                "agent_mode": config_request.agent_mode,
                "ollama_base_url": config_request.ollama_base_url or "http://localhost:11434",
            }

            config_path = self.portfolio_service.portfolios_dir / f"{config_request.name}.yaml"
            if config_path.exists():
                raise ValueError(f"Portfolio already exists: {config_request.name}")

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

            # Initialize state
            initial_state = PortfolioState(cash=config_request.initial_capital)
            self.portfolio_service.save_state(config_request.name, initial_state)
            return True
        except Exception:
            return False
    
    def update_portfolio(self, name: str, config_request: PortfolioConfigRequest) -> bool:
        """Update portfolio configuration."""
        try:
            config, state = self.portfolio_service.load_portfolio(name)

            # Update config fields
            config.initial_amount = config_request.initial_capital
            config.llm_model = config_request.llm_model

            # Write updated config YAML
            config_path = self.portfolio_service.portfolios_dir / f"{name}.yaml"
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            config_data["initial_amount"] = config_request.initial_capital
            config_data["llm_model"] = config_request.llm_model
            config_data["run_frequency"] = config_request.run_frequency
            config_data["agent_mode"] = config_request.agent_mode
            config_data["asset_class"] = config_request.asset_class

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

            self.portfolio_service.save_state(name, state)
            return True
        except Exception:
            return False
    
    def delete_portfolio(self, name: str) -> bool:
        """Delete portfolio."""
        try:
            self.portfolio_service.delete_portfolio(name)
            return True
        except Exception:
            return False