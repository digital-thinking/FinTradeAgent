"""Trades API router."""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("/pending")
async def get_pending_trades():
    """Get all pending trades."""
    # Return mock pending trades for testing
    mock_trades = [
        {
            "id": "trade_001",
            "portfolio": "test_portfolio",
            "ticker": "AAPL",
            "symbol": "AAPL",
            "action": "buy",
            "quantity": 10,
            "price": 150.0,
            "reasoning": "Strong quarterly results expected",
            "status": "pending",
            "created_at": datetime.now().isoformat()
        },
        {
            "id": "trade_002",
            "portfolio": "test_portfolio", 
            "ticker": "GOOGL",
            "symbol": "GOOGL",
            "action": "sell",
            "quantity": 5,
            "price": 2800.0,
            "reasoning": "Taking profits after recent gains",
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
    ]
    return mock_trades


@router.post("/{trade_id}/apply")
async def apply_trade(trade_id: str):
    """Apply a pending trade."""
    # TODO: Implement trade application logic  
    return {
        "success": True, 
        "message": f"Trade {trade_id} applied successfully",
        "trade_id": trade_id
    }


@router.delete("/{trade_id}")
async def cancel_trade(trade_id: str):
    """Cancel a pending trade."""
    # TODO: Implement trade cancellation logic
    return {
        "success": True,
        "message": f"Trade {trade_id} cancelled successfully",
        "trade_id": trade_id
    }