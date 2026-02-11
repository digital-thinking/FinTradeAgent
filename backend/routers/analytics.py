"""Analytics API router."""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from backend.fin_trade.services import ExecutionLogService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Create a module-level service instance for test mocking
execution_log_service = ExecutionLogService()


@router.get("/execution-logs")
async def get_execution_logs(limit: int = 50):
    """Get execution history logs."""
    try:
        logs = execution_log_service.get_logs(limit=limit)
        
        return {
            "logs": [
                {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "portfolio_name": log.portfolio_name,
                    "agent_mode": log.agent_mode,
                    "model": log.model,
                    "duration_ms": log.duration_ms,
                    "success": log.success,
                    "num_trades": log.num_trades,
                    "error_message": log.error_message
                }
                for log in logs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard_data():
    """Get dashboard summary data."""
    try:
        # Get recent stats
        recent_logs = execution_log_service.get_logs(limit=10)
        
        return {
            "total_executions": len(recent_logs),
            "success_rate": sum(1 for log in recent_logs if log.success) / len(recent_logs) if recent_logs else 0,
            "avg_duration_ms": sum(log.duration_ms for log in recent_logs) / len(recent_logs) if recent_logs else 0,
            "recent_executions": len([log for log in recent_logs if log.success])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))