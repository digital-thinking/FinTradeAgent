"""API Integration Tests - Full request/response cycles and data flow."""

import pytest
import json
import asyncio
import websockets
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestAPIIntegration:
    """Test full request/response cycles between frontend and backend."""

    def test_portfolio_crud_workflow(self, integration_client, sample_portfolio_integration, temp_portfolio_dir, mock_external_services):
        """Test complete portfolio CRUD workflow through API layers."""
        portfolio_name = sample_portfolio_integration["name"]
        
        # Mock portfolio service path handling
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # 1. CREATE - Test portfolio creation
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 200
            assert "created successfully" in response.json()["message"]
            
            # 2. READ - Test portfolio retrieval
            response = integration_client.get(f"/api/portfolios/{portfolio_name}")
            assert response.status_code == 200
            data = response.json()
            assert data["config"]["name"] == portfolio_name
            assert data["config"]["initial_capital"] == 10000.0
            assert data["state"]["cash"] > 0  # Should have initial cash
            
            # 3. LIST - Test portfolio listing
            response = integration_client.get("/api/portfolios/")
            assert response.status_code == 200
            portfolios = response.json()
            assert len(portfolios) >= 1
            assert any(p["name"] == portfolio_name for p in portfolios)
            
            # 4. UPDATE - Test portfolio configuration update
            updated_config = sample_portfolio_integration.copy()
            updated_config["initial_capital"] = 15000.0
            updated_config["trades_per_run"] = 5
            
            response = integration_client.put(f"/api/portfolios/{portfolio_name}", json=updated_config)
            assert response.status_code == 200
            assert "updated successfully" in response.json()["message"]
            
            # Verify update
            response = integration_client.get(f"/api/portfolios/{portfolio_name}")
            assert response.status_code == 200
            data = response.json()
            assert data["config"]["trades_per_run"] == 5
            
            # 5. DELETE - Test portfolio deletion
            response = integration_client.delete(f"/api/portfolios/{portfolio_name}")
            assert response.status_code == 200
            assert "deleted successfully" in response.json()["message"]
            
            # Verify deletion
            response = integration_client.get(f"/api/portfolios/{portfolio_name}")
            assert response.status_code == 404

    def test_agent_execution_workflow(self, integration_client, sample_portfolio_integration, temp_portfolio_dir, mock_external_services):
        """Test complete agent execution workflow through API layers."""
        portfolio_name = sample_portfolio_integration["name"]
        
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # Setup: Create portfolio first
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 200
            
            # Mock agent service execution
            with patch("backend.services.agent_api.AgentAPIService.execute_agent") as mock_execute:
                from backend.models.agent import AgentExecuteResponse, TradeRecommendation
                
                mock_execute.return_value = AgentExecuteResponse(
                    success=True,
                    recommendations=[
                        TradeRecommendation(
                            action="buy",
                            symbol="AAPL",
                            quantity=10,
                            price=150.0,
                            reasoning="Strong fundamentals and growth prospects"
                        ),
                        TradeRecommendation(
                            action="buy", 
                            symbol="GOOGL",
                            quantity=2,
                            price=2500.0,
                            reasoning="Market leader in AI and cloud computing"
                        )
                    ],
                    execution_time_ms=2500,
                    total_tokens=350
                )
                
                # Execute agent
                execution_request = {
                    "user_context": "Focus on technology stocks with strong growth potential"
                }
                response = integration_client.post(f"/api/agents/{portfolio_name}/execute", json=execution_request)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["recommendations"]) == 2
                assert data["recommendations"][0]["symbol"] == "AAPL"
                assert data["execution_time_ms"] == 2500
                
                # Verify agent service was called correctly
                mock_execute.assert_called_once()
                call_args = mock_execute.call_args[0][0]
                assert call_args.portfolio_name == portfolio_name
                assert "technology stocks" in call_args.user_context

    def test_trade_management_workflow(self, integration_client, sample_portfolio_integration, temp_portfolio_dir, mock_external_services):
        """Test complete trade management workflow through API layers."""
        portfolio_name = sample_portfolio_integration["name"]
        
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # Setup: Create portfolio 
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 200
            
            # Mock trade service
            with patch("backend.routers.trades.get_pending_trades") as mock_pending:
                with patch("backend.routers.trades.apply_trade") as mock_apply:
                    with patch("backend.routers.trades.cancel_trade") as mock_cancel:
                        
                        # Mock pending trades
                        mock_pending.return_value = [
                            {
                                "id": "trade_1",
                                "portfolio": portfolio_name,
                                "action": "buy",
                                "symbol": "AAPL",
                                "quantity": 10,
                                "price": 150.0,
                                "reasoning": "Strong fundamentals",
                                "created_at": datetime.now().isoformat()
                            }
                        ]
                        
                        # 1. GET pending trades
                        response = integration_client.get("/api/trades/pending")
                        assert response.status_code == 200
                        trades = response.json()
                        assert len(trades) == 1
                        assert trades[0]["symbol"] == "AAPL"
                        
                        # 2. APPLY trade
                        mock_apply.return_value = {"success": True, "message": "Trade applied successfully"}
                        response = integration_client.post("/api/trades/trade_1/apply")
                        assert response.status_code == 200
                        assert response.json()["success"] is True
                        
                        # 3. CANCEL trade
                        mock_cancel.return_value = {"success": True, "message": "Trade cancelled"}
                        response = integration_client.delete("/api/trades/trade_1")
                        assert response.status_code == 200
                        assert response.json()["success"] is True

    def test_analytics_data_flow(self, integration_client, mock_external_services):
        """Test analytics API data flow through all layers."""
        # Mock analytics service
        with patch("backend.routers.analytics.execution_log_service") as mock_log:
            with patch("backend.routers.analytics.get_dashboard_data") as mock_dashboard:
                
                # Mock execution logs
                mock_log.get_recent_logs.return_value = [
                    {
                        "id": "exec_1",
                        "portfolio": "test_portfolio",
                        "timestamp": datetime.now().isoformat(),
                        "status": "completed",
                        "duration_ms": 5000,
                        "trades_generated": 3
                    }
                ]
                
                # Mock dashboard data
                mock_dashboard.return_value = {
                    "total_portfolios": 3,
                    "total_value": 75000.0,
                    "daily_pnl": 1250.0,
                    "active_trades": 2,
                    "recent_executions": 5
                }
                
                # Test execution logs endpoint
                response = integration_client.get("/api/analytics/execution-logs")
                assert response.status_code == 200
                logs = response.json()
                assert len(logs) == 1
                assert logs[0]["portfolio"] == "test_portfolio"
                
                # Test dashboard endpoint
                response = integration_client.get("/api/analytics/dashboard")
                assert response.status_code == 200
                data = response.json()
                assert data["total_portfolios"] == 3
                assert data["total_value"] == 75000.0

    def test_system_health_monitoring(self, integration_client):
        """Test system health monitoring through API layers."""
        # Mock system services
        with patch("backend.routers.system.check_system_health") as mock_health:
            with patch("backend.routers.system.get_scheduler_status") as mock_scheduler:
                
                # Mock system health
                mock_health.return_value = {
                    "status": "healthy",
                    "services": {
                        "database": "up",
                        "llm_providers": "up", 
                        "market_data": "up"
                    },
                    "uptime_seconds": 3600,
                    "memory_usage_mb": 512
                }
                
                # Mock scheduler status
                mock_scheduler.return_value = {
                    "enabled": True,
                    "running": True,
                    "next_run": datetime.now().isoformat(),
                    "active_jobs": 2
                }
                
                # Test health endpoint
                response = integration_client.get("/api/system/health")
                assert response.status_code == 200
                health = response.json()
                assert health["status"] == "healthy"
                assert "database" in health["services"]
                
                # Test scheduler endpoint
                response = integration_client.get("/api/system/scheduler")
                assert response.status_code == 200
                scheduler = response.json()
                assert scheduler["enabled"] is True
                assert scheduler["active_jobs"] == 2

    def test_error_handling_across_layers(self, integration_client, sample_portfolio_integration):
        """Test error handling propagation across system boundaries."""
        # Test 404 errors
        response = integration_client.get("/api/portfolios/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        
        # Test 400 validation errors
        invalid_portfolio = sample_portfolio_integration.copy()
        invalid_portfolio["initial_capital"] = -1000  # Invalid negative capital
        response = integration_client.post("/api/portfolios/", json=invalid_portfolio)
        assert response.status_code == 422  # Validation error
        
        # Test 500 server errors
        with patch("backend.services.portfolio_api.PortfolioAPIService.create_portfolio") as mock_create:
            mock_create.side_effect = Exception("Database connection failed")
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 500
            assert "Database connection failed" in response.json()["detail"]

    def test_concurrent_api_requests(self, integration_client, sample_portfolio_integration, temp_portfolio_dir):
        """Test concurrent API requests and data consistency."""
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        results = []
        errors = []
        
        def create_portfolio(portfolio_data):
            """Create portfolio in separate thread."""
            try:
                response = integration_client.post("/api/portfolios/", json=portfolio_data)
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple portfolios concurrently
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            portfolios = []
            for i in range(3):
                portfolio = sample_portfolio_integration.copy()
                portfolio["name"] = f"concurrent_portfolio_{i}"
                portfolios.append(portfolio)
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(create_portfolio, p) for p in portfolios]
                for future in futures:
                    future.result()  # Wait for completion
            
            # Verify results
            assert len(errors) == 0, f"Concurrent requests failed: {errors}"
            assert all(status == 200 for status in results), f"Some requests failed: {results}"
            
            # Verify all portfolios were created
            response = integration_client.get("/api/portfolios/")
            assert response.status_code == 200
            portfolio_names = [p["name"] for p in response.json()]
            for i in range(3):
                assert f"concurrent_portfolio_{i}" in portfolio_names


class TestWebSocketIntegration:
    """Test WebSocket real-time communication end-to-end."""

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(self, integration_client, sample_portfolio_integration, temp_portfolio_dir, mock_external_services):
        """Test WebSocket connection, execution, and disconnection."""
        portfolio_name = sample_portfolio_integration["name"]
        
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # Setup: Create portfolio first
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 200
            
            # Mock WebSocket agent execution
            with patch("backend.services.agent_api.AgentAPIService.execute_agent") as mock_execute:
                async def mock_agent_execution(request, progress_callback=None):
                    """Mock agent execution with progress updates."""
                    from backend.models.agent import AgentExecuteResponse, TradeRecommendation, ExecutionProgress
                    
                    if progress_callback:
                        await progress_callback(ExecutionProgress(
                            step="initializing",
                            progress=0.1,
                            message="Setting up agent execution"
                        ))
                        
                        await asyncio.sleep(0.1)
                        
                        await progress_callback(ExecutionProgress(
                            step="analyzing", 
                            progress=0.5,
                            message="Analyzing market data"
                        ))
                        
                        await asyncio.sleep(0.1)
                        
                        await progress_callback(ExecutionProgress(
                            step="generating",
                            progress=0.9,
                            message="Generating recommendations"
                        ))
                    
                    return AgentExecuteResponse(
                        success=True,
                        recommendations=[
                            TradeRecommendation(
                                action="buy",
                                symbol="AAPL",
                                quantity=5,
                                price=150.0,
                                reasoning="WebSocket integration test"
                            )
                        ],
                        execution_time_ms=1000
                    )
                
                mock_execute.side_effect = mock_agent_execution
                
                # Connect to WebSocket endpoint
                with integration_client.websocket_connect(f"/api/agents/ws/{portfolio_name}") as websocket:
                    # Send execution request
                    request_data = {
                        "user_context": "WebSocket integration test execution"
                    }
                    websocket.send_text(json.dumps(request_data))
                    
                    # Receive progress updates
                    messages = []
                    while True:
                        try:
                            message = websocket.receive_text()
                            data = json.loads(message)
                            messages.append(data)
                            
                            if data["type"] == "result":
                                break
                        except:
                            break
                    
                    # Verify messages received
                    assert len(messages) >= 4  # At least 3 progress + 1 result
                    
                    progress_messages = [m for m in messages if m["type"] == "progress"]
                    result_messages = [m for m in messages if m["type"] == "result"]
                    
                    assert len(progress_messages) >= 3
                    assert len(result_messages) == 1
                    
                    # Verify progress sequence
                    assert progress_messages[0]["data"]["step"] == "initializing"
                    assert progress_messages[1]["data"]["step"] == "analyzing"
                    assert progress_messages[2]["data"]["step"] == "generating"
                    
                    # Verify final result
                    result = result_messages[0]["data"]
                    assert result["success"] is True
                    assert len(result["recommendations"]) == 1
                    assert result["recommendations"][0]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, integration_client, sample_portfolio_integration, temp_portfolio_dir):
        """Test WebSocket error handling and recovery."""
        portfolio_name = sample_portfolio_integration["name"]
        
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # Setup: Create portfolio first
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 200
            
            # Mock agent execution that fails
            with patch("backend.services.agent_api.AgentAPIService.execute_agent") as mock_execute:
                mock_execute.side_effect = Exception("Agent execution failed")
                
                # Connect and send request
                with integration_client.websocket_connect(f"/api/agents/ws/{portfolio_name}") as websocket:
                    request_data = {"user_context": "Test error handling"}
                    websocket.send_text(json.dumps(request_data))
                    
                    # Should receive error message
                    message = websocket.receive_text()
                    data = json.loads(message)
                    
                    assert data["type"] == "error"
                    assert "Agent execution failed" in data["data"]["error"]

    @pytest.mark.asyncio 
    async def test_multiple_websocket_connections(self, integration_client, sample_portfolio_integration, temp_portfolio_dir, mock_external_services):
        """Test multiple concurrent WebSocket connections."""
        portfolio_name = sample_portfolio_integration["name"]
        
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # Setup: Create portfolio first
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 200
            
            # Mock successful agent execution
            with patch("backend.services.agent_api.AgentAPIService.execute_agent") as mock_execute:
                from backend.models.agent import AgentExecuteResponse, TradeRecommendation
                
                mock_execute.return_value = AgentExecuteResponse(
                    success=True,
                    recommendations=[],
                    execution_time_ms=500
                )
                
                # Connect multiple WebSockets simultaneously
                connections = []
                for i in range(3):
                    conn = integration_client.websocket_connect(f"/api/agents/ws/{portfolio_name}")
                    connections.append(conn)
                
                try:
                    # Send requests from all connections
                    for i, websocket in enumerate(connections):
                        with websocket:
                            request_data = {"user_context": f"Connection {i} test"}
                            websocket.send_text(json.dumps(request_data))
                            
                            # Verify response
                            message = websocket.receive_text()
                            data = json.loads(message)
                            assert data["type"] == "result"
                            assert data["data"]["success"] is True
                
                finally:
                    # Clean up connections
                    for websocket in connections:
                        try:
                            websocket.close()
                        except:
                            pass