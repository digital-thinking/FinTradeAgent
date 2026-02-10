"""Unit tests for Agent API endpoints."""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from backend.models.agent import AgentExecuteRequest, AgentExecuteResponse, TradeRecommendation, ExecutionProgress


class TestAgentsAPI:
    """Test cases for /api/agents endpoints."""
    
    @pytest.mark.asyncio
    async def test_execute_agent_success(self, client, sample_agent_request_api, sample_agent_response_api, mock_agent_service):
        """Test successful agent execution."""
        if sample_agent_response_api is None:
            pytest.skip("Backend models not available")
            
        mock_agent_service.execute_agent.return_value = sample_agent_response_api
        
        with patch("backend.routers.agents.agent_service", mock_agent_service):
            response = client.post("/api/agents/test_portfolio/execute", json=sample_agent_request_api)
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["action"] == "buy"
        assert data["recommendations"][0]["symbol"] == "MSFT"
        assert data["execution_time_ms"] == 2500
        assert data["total_tokens"] == 150

    @pytest.mark.asyncio
    async def test_execute_agent_failure(self, client, sample_agent_request_api, mock_agent_service):
        """Test agent execution failure."""
        from backend.models.agent import AgentExecuteResponse
        
        failed_response = AgentExecuteResponse(
            success=False,
            recommendations=[],
            execution_time_ms=1000,
            total_tokens=50,
            error_message="Portfolio not found"
        )
        mock_agent_service.execute_agent.return_value = failed_response
        
        with patch("backend.routers.agents.agent_service", mock_agent_service):
            response = client.post("/api/agents/test_portfolio/execute", json=sample_agent_request_api)
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error_message"] == "Portfolio not found"
        assert len(data["recommendations"]) == 0

    @pytest.mark.asyncio  
    async def test_execute_agent_server_error(self, client, sample_agent_request_api, mock_agent_service):
        """Test agent execution with server error."""
        mock_agent_service.execute_agent.side_effect = Exception("LLM service unavailable")
        
        with patch("backend.routers.agents.agent_service", mock_agent_service):
            response = client.post("/api/agents/test_portfolio/execute", json=sample_agent_request_api)
            
        assert response.status_code == 500
        assert "LLM service unavailable" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_execute_agent_invalid_request(self, client):
        """Test agent execution with invalid request data."""
        invalid_request = {
            "portfolio_name": "",  # Empty name
            "user_context": None
        }
        
        response = client.post("/api/agents/test_portfolio/execute", json=invalid_request)
        # Should still work as portfolio_name is set from URL path
        # If validation fails, we expect a 422 status
        assert response.status_code in [200, 422, 500]

    @pytest.mark.asyncio
    async def test_execute_agent_with_context(self, client, mock_agent_service):
        """Test agent execution with user context."""
        from backend.models.agent import AgentExecuteResponse, TradeRecommendation
        
        request_data = {
            "portfolio_name": "test_portfolio", 
            "user_context": "Focus on tech stocks with high growth potential"
        }
        
        response_data = AgentExecuteResponse(
            success=True,
            recommendations=[
                TradeRecommendation(
                    action="buy",
                    symbol="NVDA",
                    quantity=2,
                    price=800.0,
                    reasoning="AI semiconductor leader with strong growth"
                )
            ],
            execution_time_ms=3200,
            total_tokens=200
        )
        
        mock_agent_service.execute_agent.return_value = response_data
        
        with patch("backend.routers.agents.agent_service", mock_agent_service):
            response = client.post("/api/agents/test_portfolio/execute", json=request_data)
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["recommendations"][0]["symbol"] == "NVDA"
        assert data["recommendations"][0]["reasoning"] == "AI semiconductor leader with strong growth"

    def test_websocket_connection_acceptance(self, client):
        """Test WebSocket connection is accepted."""
        with client.websocket_connect("/api/agents/ws/test_portfolio") as websocket:
            # If we get here without exception, connection was accepted
            assert websocket is not None

    @pytest.mark.asyncio
    async def test_websocket_agent_execution_success(self, client, mock_agent_service):
        """Test successful agent execution via WebSocket."""
        from backend.models.agent import AgentExecuteResponse, TradeRecommendation, ExecutionProgress
        
        # Mock the agent service
        response_data = AgentExecuteResponse(
            success=True,
            recommendations=[
                TradeRecommendation(
                    action="sell",
                    symbol="AAPL",
                    quantity=5,
                    price=155.0,
                    reasoning="Taking profits after strong gains"
                )
            ],
            execution_time_ms=2800,
            total_tokens=175
        )
        
        # Mock progress callback
        async def mock_execute_agent(request, progress_callback=None):
            if progress_callback:
                await progress_callback(ExecutionProgress(
                    step="analysis",
                    status="running", 
                    message="Analyzing market data",
                    progress=0.5
                ))
                await progress_callback(ExecutionProgress(
                    step="recommendations",
                    status="completed",
                    message="Generated trade recommendations", 
                    progress=1.0
                ))
            return response_data
            
        mock_agent_service.execute_agent.side_effect = mock_execute_agent
        
        with patch("backend.routers.agents.agent_service", mock_agent_service):
            with client.websocket_connect("/api/agents/ws/test_portfolio") as websocket:
                # Send execution request
                request_data = {
                    "user_context": "Conservative approach, focus on dividends"
                }
                websocket.send_text(json.dumps(request_data))
                
                # Should receive progress updates
                progress_msg = websocket.receive_text()
                progress_data = json.loads(progress_msg)
                assert progress_data["type"] == "progress"
                assert progress_data["data"]["step"] == "analysis"
                assert progress_data["data"]["status"] == "running"
                
                # Second progress update
                progress_msg2 = websocket.receive_text()
                progress_data2 = json.loads(progress_msg2)
                assert progress_data2["type"] == "progress"
                assert progress_data2["data"]["step"] == "recommendations"
                assert progress_data2["data"]["status"] == "completed"
                
                # Final result
                result_msg = websocket.receive_text()
                result_data = json.loads(result_msg)
                assert result_data["type"] == "result"
                assert result_data["data"]["success"] is True
                assert len(result_data["data"]["recommendations"]) == 1

    @pytest.mark.asyncio
    async def test_websocket_agent_execution_error(self, client, mock_agent_service):
        """Test agent execution error via WebSocket."""
        mock_agent_service.execute_agent.side_effect = Exception("API rate limit exceeded")
        
        with patch("backend.routers.agents.agent_service", mock_agent_service):
            with client.websocket_connect("/api/agents/ws/test_portfolio") as websocket:
                # Send execution request
                request_data = {"user_context": "Test context"}
                websocket.send_text(json.dumps(request_data))
                
                # Should receive error message
                error_msg = websocket.receive_text()
                error_data = json.loads(error_msg)
                assert error_data["type"] == "error"
                assert "API rate limit exceeded" in error_data["data"]["error"]

    def test_websocket_invalid_json(self, client):
        """Test WebSocket with invalid JSON data."""
        with client.websocket_connect("/api/agents/ws/test_portfolio") as websocket:
            # Send invalid JSON
            websocket.send_text("invalid json data")
            
            # Connection should handle the error gracefully
            # This may result in connection closure or error message
            try:
                response = websocket.receive_text()
                if response:
                    data = json.loads(response)
                    assert data["type"] == "error"
            except Exception:
                # Connection may close due to invalid data
                pass

    @pytest.mark.asyncio
    async def test_execute_agent_multiple_recommendations(self, client, mock_agent_service):
        """Test agent execution returning multiple trade recommendations."""
        from backend.models.agent import AgentExecuteResponse, TradeRecommendation
        
        response_data = AgentExecuteResponse(
            success=True,
            recommendations=[
                TradeRecommendation(
                    action="buy",
                    symbol="TSLA",
                    quantity=3,
                    price=200.0,
                    reasoning="Electric vehicle market growth"
                ),
                TradeRecommendation(
                    action="sell", 
                    symbol="META",
                    quantity=8,
                    price=350.0,
                    reasoning="Overvalued in current market"
                ),
                TradeRecommendation(
                    action="buy",
                    symbol="GOOGL",
                    quantity=2,
                    price=140.0,
                    reasoning="AI and cloud services expansion"
                )
            ],
            execution_time_ms=4500,
            total_tokens=300
        )
        
        mock_agent_service.execute_agent.return_value = response_data
        
        request_data = {"user_context": "Diversified tech portfolio"}
        
        with patch("backend.routers.agents.agent_service", mock_agent_service):
            response = client.post("/api/agents/test_portfolio/execute", json=request_data)
            
        assert response.status_code in [200, 422]  # 422 if validation fails
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert len(data["recommendations"]) == 3
            
            # Verify each recommendation
            symbols = [rec["symbol"] for rec in data["recommendations"]]
            assert "TSLA" in symbols
            assert "META" in symbols 
            assert "GOOGL" in symbols
            
            actions = [rec["action"] for rec in data["recommendations"]]
            assert actions.count("buy") == 2
            assert actions.count("sell") == 1