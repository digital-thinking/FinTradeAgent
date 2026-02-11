"""Pydantic models for Agent API."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime


class AgentExecuteRequest(BaseModel):
    """Request model for agent execution."""
    portfolio_name: str
    user_context: Optional[str] = None


class TradeRecommendation(BaseModel):
    """Trade recommendation model."""
    action: str  # "buy", "sell" 
    symbol: str
    quantity: float
    price: Optional[float] = None
    reasoning: str


class AgentExecuteResponse(BaseModel):
    """Response model for agent execution."""
    success: bool
    recommendations: List[TradeRecommendation]
    execution_time_ms: int
    total_tokens: int
    error_message: Optional[str] = None


class ExecutionProgress(BaseModel):
    """Progress update during agent execution."""
    step: str
    status: str  # "running", "completed", "failed"
    message: str
    progress: float  # 0.0 to 1.0