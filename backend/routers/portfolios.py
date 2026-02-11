"""Portfolio API router."""

from typing import List
from fastapi import APIRouter, HTTPException
from backend.models.portfolio import (
    PortfolioConfigRequest,
    PortfolioResponse,
    PortfolioSummary,
    ErrorResponse
)
from backend.services.portfolio_api import PortfolioAPIService

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])
portfolio_service = PortfolioAPIService()


@router.get("/", response_model=List[PortfolioSummary])
async def list_portfolios():
    """List all portfolios with summary information."""
    try:
        return portfolio_service.list_portfolios()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}", response_model=PortfolioResponse)
async def get_portfolio(name: str):
    """Get portfolio details by name."""
    portfolio = portfolio_service.get_portfolio(name)
    if not portfolio:
        raise HTTPException(status_code=404, detail=f"Portfolio '{name}' not found")
    return portfolio


@router.post("/", response_model=dict)
async def create_portfolio(config: PortfolioConfigRequest):
    """Create a new portfolio."""
    try:
        success = portfolio_service.create_portfolio(config)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to create portfolio")
        return {"message": f"Portfolio '{config.name}' created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{name}", response_model=dict)
async def update_portfolio(name: str, config: PortfolioConfigRequest):
    """Update portfolio configuration."""
    try:
        success = portfolio_service.update_portfolio(name, config)
        if not success:
            raise HTTPException(status_code=404, detail=f"Portfolio '{name}' not found")
        return {"message": f"Portfolio '{name}' updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}", response_model=dict)
async def delete_portfolio(name: str):
    """Delete a portfolio."""
    try:
        success = portfolio_service.delete_portfolio(name)
        if not success:
            raise HTTPException(status_code=404, detail=f"Portfolio '{name}' not found")
        return {"message": f"Portfolio '{name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))