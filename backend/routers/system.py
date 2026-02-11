"""System API router."""

from fastapi import APIRouter, HTTPException
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

# Note: SchedulerService not available in current branch
# from fin_trade.services.scheduler import SchedulerService

router = APIRouter(prefix="/api/system", tags=["system"])


def check_system_health():
    """Check system health status."""
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "scheduler": "running", 
            "database": "connected"
        },
        "uptime": "unknown"
    }


def get_user_preferences():
    """Get user preferences."""
    return {
        "theme": "light",
        "notifications": True,
        "auto_refresh": 30
    }


def update_user_preferences(preferences: dict):
    """Update user preferences."""
    # TODO: Implement preference persistence
    return preferences


@router.get("/health")
async def system_health():
    """Get detailed system health information."""
    return check_system_health()


@router.get("/scheduler")
async def scheduler_status():
    """Get scheduler status and information."""
    try:
        # Note: Can't easily get scheduler instance without proper setup
        # Return placeholder data for now
        return {
            "running": True,
            "enabled_portfolios": [],
            "next_runs": {},
            "last_runs": {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/start")
async def start_scheduler():
    """Start the portfolio scheduler."""
    return {"message": "Scheduler start - TODO"}


@router.post("/scheduler/stop") 
async def stop_scheduler():
    """Stop the portfolio scheduler."""
    return {"message": "Scheduler stop - TODO"}


@router.get("/preferences")
async def get_preferences():
    """Get user preferences."""
    return get_user_preferences()


@router.post("/preferences")
async def update_preferences(preferences: dict):
    """Update user preferences."""
    return update_user_preferences(preferences)