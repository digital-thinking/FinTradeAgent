"""API service wrapper for AgentService."""

import sys
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import asyncio
import time

from backend.fin_trade.services.portfolio import PortfolioService
from backend.fin_trade.services.agent import AgentService
from backend.fin_trade.services.security import SecurityService
from backend.fin_trade.agents.service import DebateAgentService, LangGraphAgentService
from backend.models.agent import (
    AgentExecuteRequest,
    AgentExecuteResponse,
    TradeRecommendation,
    ExecutionProgress
)


class AgentAPIService:
    """API wrapper for agent execution services."""
    
    def __init__(self):
        self.security_service = SecurityService()
        self.portfolio_service = PortfolioService(security_service=self.security_service)
        self.agent_service = AgentService(security_service=self.security_service)
    
    async def execute_agent(
        self, 
        request: AgentExecuteRequest,
        progress_callback: Optional[callable] = None
    ) -> AgentExecuteResponse:
        """Execute agent for portfolio."""
        start_time = time.time()
        
        try:
            # Load portfolio
            config, state = self.portfolio_service.load_portfolio(request.portfolio_name)
            
            if progress_callback:
                await progress_callback(ExecutionProgress(
                    step="initialize",
                    status="running", 
                    message="Loading portfolio configuration",
                    progress=0.1
                ))
            
            # Execute based on agent mode
            if config.agent_mode == "simple":
                recommendation = self.agent_service.execute(config, state)
                metrics = None
            elif config.agent_mode == "debate":
                if progress_callback:
                    await progress_callback(ExecutionProgress(
                        step="debate",
                        status="running",
                        message="Starting debate agent execution",
                        progress=0.3
                    ))
                
                debate_agent = DebateAgentService(security_service=self.security_service)
                recommendation, metrics = debate_agent.execute(config, state)
            elif config.agent_mode == "langgraph":
                if progress_callback:
                    await progress_callback(ExecutionProgress(
                        step="langgraph", 
                        status="running",
                        message="Starting LangGraph agent execution",
                        progress=0.3
                    ))
                
                langgraph_agent = LangGraphAgentService(security_service=self.security_service)
                recommendation, metrics = langgraph_agent.execute(config, state)
            else:
                raise ValueError(f"Unknown agent mode: {config.agent_mode}")
            
            if progress_callback:
                await progress_callback(ExecutionProgress(
                    step="complete",
                    status="completed",
                    message="Agent execution completed",
                    progress=1.0
                ))
            
            # Convert recommendations
            trades = []
            if recommendation and recommendation.trades:
                for trade in recommendation.trades:
                    trades.append(TradeRecommendation(
                        action=trade.action,
                        symbol=trade.ticker,
                        quantity=trade.quantity,
                        price=None,
                        reasoning=trade.reasoning or ""
                    ))
            
            execution_time = int((time.time() - start_time) * 1000)
            total_tokens = metrics.total_tokens if metrics else 0
            
            return AgentExecuteResponse(
                success=True,
                recommendations=trades,
                execution_time_ms=execution_time,
                total_tokens=total_tokens
            )
            
        except Exception as e:
            if progress_callback:
                await progress_callback(ExecutionProgress(
                    step="error",
                    status="failed",
                    message=f"Execution failed: {str(e)}",
                    progress=0.0
                ))
            
            execution_time = int((time.time() - start_time) * 1000)
            return AgentExecuteResponse(
                success=False,
                recommendations=[],
                execution_time_ms=execution_time,
                total_tokens=0,
                error_message=str(e)
            )