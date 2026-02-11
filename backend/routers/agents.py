"""Agent API router."""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import asyncio

from backend.models.agent import (
    AgentExecuteRequest,
    AgentExecuteResponse,
    ExecutionProgress
)
from backend.services.agent_api import AgentAPIService

router = APIRouter(prefix="/api/agents", tags=["agents"])
agent_service = AgentAPIService()

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


@router.post("/{portfolio_name}/execute", response_model=AgentExecuteResponse)
async def execute_agent(portfolio_name: str, request: AgentExecuteRequest):
    """Execute agent for portfolio (synchronous)."""
    request.portfolio_name = portfolio_name
    
    try:
        response = await agent_service.execute_agent(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{portfolio_name}")
async def websocket_endpoint(websocket: WebSocket, portfolio_name: str):
    """WebSocket endpoint for real-time agent execution updates."""
    await websocket.accept()
    connection_id = f"{portfolio_name}_{id(websocket)}"
    active_connections[connection_id] = websocket
    
    try:
        while True:
            # Wait for execution request
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            request = AgentExecuteRequest(
                portfolio_name=portfolio_name,
                user_context=request_data.get("user_context")
            )
            
            # Execute with progress callback
            async def progress_callback(progress: ExecutionProgress):
                await websocket.send_text(json.dumps({
                    "type": "progress",
                    "data": progress.dict()
                }))
            
            response = await agent_service.execute_agent(request, progress_callback)
            
            # Send final response
            await websocket.send_text(json.dumps({
                "type": "result", 
                "data": response.dict()
            }))
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {"error": str(e)}
            }))
        except:
            pass
    finally:
        if connection_id in active_connections:
            del active_connections[connection_id]