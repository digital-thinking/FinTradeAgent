"""API service wrapper for PortfolioService."""

import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Add src to path to import existing services
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from fin_trade.services import PortfolioService, SecurityService
from fin_trade.models import PortfolioConfig, PortfolioState
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
                    total_value=state.cash + sum(h.quantity * h.avg_cost for h in state.holdings),
                    cash=state.cash,
                    holdings_count=holdings_count,
                    last_updated=state.last_updated,
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
                    symbol=h.symbol,
                    quantity=h.quantity,
                    avg_cost=h.avg_cost,
                    current_price=None  # TODO: Get current price
                )
                for h in state.holdings
            ]
            
            # Convert state
            state_response = PortfolioStateResponse(
                cash=state.cash,
                holdings=holdings,
                total_value=state.cash + sum(h.quantity * h.avg_cost for h in state.holdings),
                last_updated=state.last_updated
            )
            
            # Convert config
            config_response = PortfolioConfigRequest(
                name=config.name,
                initial_capital=config.initial_capital,
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
            # Convert API request to internal config
            config = PortfolioConfig(
                name=config_request.name,
                initial_capital=config_request.initial_capital,
                llm_model=config_request.llm_model,
                # Convert other fields as needed
            )
            
            self.portfolio_service.create_portfolio(config)
            return True
        except Exception:
            return False
    
    def update_portfolio(self, name: str, config_request: PortfolioConfigRequest) -> bool:
        """Update portfolio configuration."""
        try:
            config, state = self.portfolio_service.load_portfolio(name)
            
            # Update config fields
            config.initial_capital = config_request.initial_capital
            config.llm_model = config_request.llm_model
            # Update other fields as needed
            
            self.portfolio_service.save_portfolio(config, state)
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