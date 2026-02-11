"""Pydantic models for Portfolio API."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PortfolioConfigRequest(BaseModel):
    """Request model for portfolio configuration."""
    name: str
    initial_capital: float = Field(gt=0, description="Initial capital must be positive")
    llm_model: str
    asset_class: str = "stocks"
    agent_mode: str = "langgraph"
    run_frequency: str = "daily"
    scheduler_enabled: bool = False
    auto_apply_trades: bool = False
    ollama_base_url: Optional[str] = "http://localhost:11434"


class HoldingResponse(BaseModel):
    """Response model for portfolio holding."""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: Optional[float] = None


class PortfolioStateResponse(BaseModel):
    """Response model for portfolio state."""
    cash: float
    holdings: List[HoldingResponse]
    total_value: float
    last_updated: datetime


class PortfolioResponse(BaseModel):
    """Response model for complete portfolio."""
    config: PortfolioConfigRequest
    state: PortfolioStateResponse


class PortfolioSummary(BaseModel):
    """Summary model for portfolio list."""
    name: str
    total_value: float
    cash: float
    holdings_count: int
    last_updated: datetime
    scheduler_enabled: bool


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None