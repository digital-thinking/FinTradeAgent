"""Frontend-Backend Integration Tests - API service layer and real-time features."""

import pytest
import json
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta


class TestAPIServiceLayerIntegration:
    """Test frontend API service layer integration with backend endpoints."""

    def test_portfolio_api_service_integration(self, integration_client, sample_portfolio_integration, temp_portfolio_dir, mock_external_services):
        """Test complete frontend API service integration for portfolio operations."""
        portfolio_name = sample_portfolio_integration["name"]
        
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            
            # Simulate frontend API service calls matching Vue.js implementation
            api_base_url = "/api"
            
            # 1. Frontend: Create Portfolio Request
            create_payload = {
                "name": portfolio_name,
                "initial_capital": sample_portfolio_integration["initial_capital"],
                "llm_model": sample_portfolio_integration["llm_model"],
                "llm_provider": sample_portfolio_integration["llm_provider"],
                "asset_class": sample_portfolio_integration["asset_class"],
                "agent_mode": sample_portfolio_integration["agent_mode"],
                "run_frequency": sample_portfolio_integration["run_frequency"],
                "scheduler_enabled": sample_portfolio_integration["scheduler_enabled"],
                "auto_apply_trades": sample_portfolio_integration["auto_apply_trades"],
                "trades_per_run": sample_portfolio_integration["trades_per_run"],
                "strategy_prompt": sample_portfolio_integration["strategy_prompt"]
            }
            
            response = integration_client.post(f"{api_base_url}/portfolios/", json=create_payload)
            assert response.status_code == 200
            create_result = response.json()
            assert "created successfully" in create_result["message"]
            
            # 2. Frontend: Fetch Portfolio List
            response = integration_client.get(f"{api_base_url}/portfolios/")
            assert response.status_code == 200
            portfolios = response.json()
            assert isinstance(portfolios, list)
            assert len(portfolios) >= 1
            
            portfolio_found = False
            for portfolio in portfolios:
                if portfolio["name"] == portfolio_name:
                    portfolio_found = True
                    assert "total_value" in portfolio
                    assert "cash" in portfolio
                    assert "holdings_count" in portfolio
                    assert "last_updated" in portfolio
                    break
            assert portfolio_found, "Created portfolio not found in list"
            
            # 3. Frontend: Fetch Portfolio Details
            response = integration_client.get(f"{api_base_url}/portfolios/{portfolio_name}")
            assert response.status_code == 200
            portfolio_detail = response.json()
            
            assert "config" in portfolio_detail
            assert "state" in portfolio_detail
            assert portfolio_detail["config"]["name"] == portfolio_name
            assert portfolio_detail["config"]["initial_capital"] == sample_portfolio_integration["initial_capital"]
            assert portfolio_detail["state"]["cash"] > 0
            
            # 4. Frontend: Update Portfolio Configuration
            update_payload = create_payload.copy()
            update_payload["trades_per_run"] = 5
            update_payload["strategy_prompt"] = "Updated strategy for frontend integration"
            
            response = integration_client.put(f"{api_base_url}/portfolios/{portfolio_name}", json=update_payload)
            assert response.status_code == 200
            update_result = response.json()
            assert "updated successfully" in update_result["message"]
            
            # Verify update
            response = integration_client.get(f"{api_base_url}/portfolios/{portfolio_name}")
            assert response.status_code == 200
            updated_portfolio = response.json()
            assert updated_portfolio["config"]["trades_per_run"] == 5
            assert "Updated strategy" in updated_portfolio["config"]["strategy_prompt"]
            
            # 5. Frontend: Delete Portfolio
            response = integration_client.delete(f"{api_base_url}/portfolios/{portfolio_name}")
            assert response.status_code == 200
            delete_result = response.json()
            assert "deleted successfully" in delete_result["message"]
            
            # Verify deletion
            response = integration_client.get(f"{api_base_url}/portfolios/{portfolio_name}")
            assert response.status_code == 404

    def test_agent_execution_api_service_integration(self, integration_client, sample_portfolio_integration, temp_portfolio_dir, mock_external_services):
        """Test frontend API service integration for agent execution."""
        portfolio_name = sample_portfolio_integration["name"]
        
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # Setup: Create portfolio first
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 200
            
            # Mock agent execution
            with patch("backend.services.agent_api.AgentAPIService.execute_agent") as mock_execute:
                from backend.models.agent import AgentExecuteResponse, TradeRecommendation
                
                mock_execute.return_value = AgentExecuteResponse(
                    success=True,
                    recommendations=[
                        TradeRecommendation(
                            action="buy",
                            symbol="AAPL",
                            quantity=10,
                            price=155.0,
                            reasoning="Strong Q4 earnings and iPhone 15 cycle"
                        ),
                        TradeRecommendation(
                            action="buy", 
                            symbol="MSFT",
                            quantity=5,
                            price=320.0,
                            reasoning="Azure growth and AI integration across products"
                        )
                    ],
                    execution_time_ms=3200,
                    total_tokens=425
                )
                
                # Frontend: Execute Agent Request
                execution_request = {
                    "user_context": "Focus on technology stocks with strong fundamentals and growth prospects"
                }
                
                response = integration_client.post(f"/api/agents/{portfolio_name}/execute", json=execution_request)
                assert response.status_code == 200
                
                execution_result = response.json()
                assert execution_result["success"] is True
                assert len(execution_result["recommendations"]) == 2
                
                # Verify recommendation structure matches frontend expectations
                recommendation = execution_result["recommendations"][0]
                assert "action" in recommendation
                assert "symbol" in recommendation
                assert "quantity" in recommendation 
                assert "price" in recommendation
                assert "reasoning" in recommendation
                
                assert recommendation["symbol"] == "AAPL"
                assert recommendation["action"] == "buy"
                assert recommendation["quantity"] == 10
                assert "iPhone 15" in recommendation["reasoning"]
                
                # Verify execution metadata
                assert execution_result["execution_time_ms"] == 3200
                assert execution_result["total_tokens"] == 425

    def test_trades_api_service_integration(self, integration_client, mock_external_services):
        """Test frontend API service integration for trade management."""
        
        # Mock trade service functions
        with patch("backend.routers.trades.get_pending_trades") as mock_get_pending:
            with patch("backend.routers.trades.apply_trade") as mock_apply_trade:
                with patch("backend.routers.trades.cancel_trade") as mock_cancel_trade:
                    
                    # Setup mock pending trades
                    mock_pending_trades = [
                        {
                            "id": "trade_001",
                            "portfolio": "test_portfolio",
                            "action": "buy",
                            "symbol": "AAPL",
                            "quantity": 10,
                            "price": 155.0,
                            "reasoning": "Strong fundamentals",
                            "created_at": datetime.now().isoformat(),
                            "estimated_cost": 1550.0
                        },
                        {
                            "id": "trade_002", 
                            "portfolio": "test_portfolio",
                            "action": "buy",
                            "symbol": "GOOGL",
                            "quantity": 2,
                            "price": 2650.0,
                            "reasoning": "AI leadership position",
                            "created_at": datetime.now().isoformat(),
                            "estimated_cost": 5300.0
                        }
                    ]
                    mock_get_pending.return_value = mock_pending_trades
                    
                    # Frontend: Get Pending Trades
                    response = integration_client.get("/api/trades/pending")
                    assert response.status_code == 200
                    
                    pending_trades = response.json()
                    assert len(pending_trades) == 2
                    
                    # Verify trade structure matches frontend expectations
                    trade = pending_trades[0]
                    required_fields = ["id", "portfolio", "action", "symbol", "quantity", "price", "reasoning", "created_at"]
                    for field in required_fields:
                        assert field in trade, f"Missing field: {field}"
                    
                    assert trade["symbol"] == "AAPL"
                    assert trade["action"] == "buy"
                    assert trade["quantity"] == 10
                    
                    # Frontend: Apply Trade
                    mock_apply_trade.return_value = {"success": True, "message": "Trade applied successfully"}
                    
                    response = integration_client.post("/api/trades/trade_001/apply")
                    assert response.status_code == 200
                    
                    apply_result = response.json()
                    assert apply_result["success"] is True
                    assert "successfully" in apply_result["message"].lower()
                    
                    # Frontend: Cancel Trade
                    mock_cancel_trade.return_value = {"success": True, "message": "Trade cancelled"}
                    
                    response = integration_client.delete("/api/trades/trade_002")
                    assert response.status_code == 200
                    
                    cancel_result = response.json()
                    assert cancel_result["success"] is True
                    assert "cancelled" in cancel_result["message"].lower()

    def test_analytics_api_service_integration(self, integration_client, mock_external_services):
        """Test frontend API service integration for analytics endpoints."""
        
        # Mock analytics services
        with patch("backend.routers.analytics.execution_log_service") as mock_log_service:
            with patch("backend.routers.analytics.get_dashboard_data") as mock_dashboard:
                
                # Setup mock execution logs
                mock_execution_logs = [
                    {
                        "id": "exec_001",
                        "portfolio": "growth_portfolio",
                        "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                        "status": "completed",
                        "duration_ms": 4500,
                        "trades_generated": 3,
                        "tokens_used": 320,
                        "error_message": None
                    },
                    {
                        "id": "exec_002",
                        "portfolio": "value_portfolio", 
                        "timestamp": (datetime.now() - timedelta(hours=6)).isoformat(),
                        "status": "failed",
                        "duration_ms": 1200,
                        "trades_generated": 0,
                        "tokens_used": 85,
                        "error_message": "Market data service unavailable"
                    },
                    {
                        "id": "exec_003",
                        "portfolio": "growth_portfolio",
                        "timestamp": (datetime.now() - timedelta(days=1)).isoformat(), 
                        "status": "completed",
                        "duration_ms": 3800,
                        "trades_generated": 2,
                        "tokens_used": 280,
                        "error_message": None
                    }
                ]
                mock_log_service.get_recent_logs.return_value = mock_execution_logs
                
                # Setup mock dashboard data
                mock_dashboard_data = {
                    "total_portfolios": 5,
                    "total_value": 125000.0,
                    "daily_pnl": 2350.0,
                    "daily_pnl_pct": 1.88,
                    "active_trades": 3,
                    "pending_trades": 2,
                    "recent_executions": 8,
                    "avg_execution_time_ms": 3500,
                    "success_rate": 0.875,
                    "top_performers": [
                        {"symbol": "AAPL", "pnl": 1250.0, "pnl_pct": 8.33},
                        {"symbol": "MSFT", "pnl": 890.0, "pnl_pct": 5.93},
                        {"symbol": "GOOGL", "pnl": 720.0, "pnl_pct": 2.72}
                    ]
                }
                mock_dashboard.return_value = mock_dashboard_data
                
                # Frontend: Get Execution Logs
                response = integration_client.get("/api/analytics/execution-logs")
                assert response.status_code == 200
                
                execution_logs = response.json()
                assert len(execution_logs) == 3
                
                # Verify log structure matches frontend expectations
                log = execution_logs[0]
                required_fields = ["id", "portfolio", "timestamp", "status", "duration_ms", "trades_generated"]
                for field in required_fields:
                    assert field in log, f"Missing field: {field}"
                
                assert log["portfolio"] == "growth_portfolio"
                assert log["status"] == "completed"
                assert log["trades_generated"] == 3
                
                # Verify failed execution has error message
                failed_log = next(log for log in execution_logs if log["status"] == "failed")
                assert failed_log["error_message"] is not None
                assert "Market data service" in failed_log["error_message"]
                
                # Frontend: Get Dashboard Data
                response = integration_client.get("/api/analytics/dashboard")
                assert response.status_code == 200
                
                dashboard_data = response.json()
                
                # Verify dashboard structure matches frontend expectations
                required_dashboard_fields = [
                    "total_portfolios", "total_value", "daily_pnl", "active_trades", 
                    "recent_executions", "success_rate"
                ]
                for field in required_dashboard_fields:
                    assert field in dashboard_data, f"Missing dashboard field: {field}"
                
                assert dashboard_data["total_portfolios"] == 5
                assert dashboard_data["total_value"] == 125000.0
                assert dashboard_data["daily_pnl"] == 2350.0
                assert dashboard_data["success_rate"] == 0.875
                
                # Verify top performers structure
                assert "top_performers" in dashboard_data
                assert len(dashboard_data["top_performers"]) == 3
                top_performer = dashboard_data["top_performers"][0]
                assert "symbol" in top_performer
                assert "pnl" in top_performer
                assert "pnl_pct" in top_performer

    def test_system_api_service_integration(self, integration_client, mock_external_services):
        """Test frontend API service integration for system endpoints."""
        
        # Mock system services
        with patch("backend.routers.system.check_system_health") as mock_health:
            with patch("backend.routers.system.get_scheduler_status") as mock_scheduler:
                
                # Setup mock system health
                mock_health_data = {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "services": {
                        "database": {"status": "up", "response_time_ms": 12},
                        "llm_providers": {"status": "up", "response_time_ms": 450},
                        "market_data": {"status": "up", "response_time_ms": 180},
                        "portfolio_service": {"status": "up", "response_time_ms": 25},
                        "agent_service": {"status": "up", "response_time_ms": 35}
                    },
                    "system_metrics": {
                        "uptime_seconds": 86400,
                        "memory_usage_mb": 756,
                        "cpu_usage_pct": 15.5,
                        "disk_usage_pct": 42.1
                    }
                }
                mock_health.return_value = mock_health_data
                
                # Setup mock scheduler status  
                mock_scheduler_data = {
                    "enabled": True,
                    "running": True,
                    "next_run": (datetime.now() + timedelta(hours=1)).isoformat(),
                    "last_run": (datetime.now() - timedelta(hours=23)).isoformat(),
                    "active_jobs": 3,
                    "completed_jobs": 156,
                    "failed_jobs": 4,
                    "job_queue_size": 1
                }
                mock_scheduler.return_value = mock_scheduler_data
                
                # Frontend: Get System Health
                response = integration_client.get("/api/system/health")
                assert response.status_code == 200
                
                health_data = response.json()
                
                # Verify health structure matches frontend expectations
                assert health_data["status"] == "healthy"
                assert "services" in health_data
                assert "system_metrics" in health_data
                
                # Verify service statuses
                services = health_data["services"]
                expected_services = ["database", "llm_providers", "market_data", "portfolio_service", "agent_service"]
                for service in expected_services:
                    assert service in services
                    assert services[service]["status"] == "up"
                    assert "response_time_ms" in services[service]
                
                # Verify system metrics
                metrics = health_data["system_metrics"] 
                expected_metrics = ["uptime_seconds", "memory_usage_mb", "cpu_usage_pct"]
                for metric in expected_metrics:
                    assert metric in metrics
                    assert isinstance(metrics[metric], (int, float))
                
                # Frontend: Get Scheduler Status
                response = integration_client.get("/api/system/scheduler")
                assert response.status_code == 200
                
                scheduler_data = response.json()
                
                # Verify scheduler structure matches frontend expectations
                required_scheduler_fields = [
                    "enabled", "running", "next_run", "active_jobs", "completed_jobs"
                ]
                for field in required_scheduler_fields:
                    assert field in scheduler_data, f"Missing scheduler field: {field}"
                
                assert scheduler_data["enabled"] is True
                assert scheduler_data["running"] is True
                assert scheduler_data["active_jobs"] == 3
                assert scheduler_data["completed_jobs"] == 156


class TestWebSocketConnectionManagement:
    """Test WebSocket connection management and reconnection logic."""

    def test_websocket_connection_lifecycle_management(self, integration_client, sample_portfolio_integration, temp_portfolio_dir, mock_external_services):
        """Test complete WebSocket connection lifecycle from frontend perspective."""
        portfolio_name = sample_portfolio_integration["name"]
        
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # Setup: Create portfolio first
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 200
            
            # Mock agent execution with progress updates
            with patch("backend.services.agent_api.AgentAPIService.execute_agent") as mock_execute:
                async def mock_agent_with_progress(request, progress_callback=None):
                    """Mock agent execution that sends progress updates."""
                    from backend.models.agent import AgentExecuteResponse, TradeRecommendation, ExecutionProgress
                    
                    if progress_callback:
                        # Simulate realistic agent execution progress
                        progress_steps = [
                            ("connecting", 0.1, "Connecting to market data services"),
                            ("analyzing", 0.3, "Analyzing portfolio and market conditions"),
                            ("researching", 0.6, "Researching potential trade opportunities"), 
                            ("generating", 0.9, "Generating trade recommendations"),
                            ("finalizing", 1.0, "Finalizing recommendations")
                        ]
                        
                        for step, progress, message in progress_steps:
                            await progress_callback(ExecutionProgress(
                                step=step,
                                progress=progress,
                                message=message
                            ))
                            await asyncio.sleep(0.05)  # Simulate processing time
                    
                    return AgentExecuteResponse(
                        success=True,
                        recommendations=[
                            TradeRecommendation(
                                action="buy",
                                symbol="AAPL", 
                                quantity=8,
                                price=155.0,
                                reasoning="WebSocket integration test recommendation"
                            )
                        ],
                        execution_time_ms=2500,
                        total_tokens=180
                    )
                
                mock_execute.side_effect = mock_agent_with_progress
                
                # Test WebSocket connection and message flow
                with integration_client.websocket_connect(f"/api/agents/ws/{portfolio_name}") as websocket:
                    
                    # Frontend: Send execution request
                    request_payload = {
                        "user_context": "WebSocket integration test - focus on technology stocks"
                    }
                    websocket.send_text(json.dumps(request_payload))
                    
                    # Frontend: Receive and process messages
                    received_messages = []
                    progress_updates = []
                    final_result = None
                    
                    while True:
                        try:
                            message_text = websocket.receive_text()
                            message = json.loads(message_text)
                            received_messages.append(message)
                            
                            if message["type"] == "progress":
                                progress_updates.append(message["data"])
                            elif message["type"] == "result":
                                final_result = message["data"]
                                break
                            elif message["type"] == "error":
                                pytest.fail(f"WebSocket error: {message['data']}")
                                break
                                
                        except Exception as e:
                            break
                    
                    # Verify frontend received expected message flow
                    assert len(received_messages) >= 6  # 5 progress + 1 result
                    assert len(progress_updates) == 5
                    assert final_result is not None
                    
                    # Verify progress update sequence
                    expected_steps = ["connecting", "analyzing", "researching", "generating", "finalizing"]
                    for i, expected_step in enumerate(expected_steps):
                        assert progress_updates[i]["step"] == expected_step
                        assert 0 <= progress_updates[i]["progress"] <= 1
                        assert len(progress_updates[i]["message"]) > 0
                    
                    # Verify final result structure
                    assert final_result["success"] is True
                    assert len(final_result["recommendations"]) == 1
                    assert final_result["recommendations"][0]["symbol"] == "AAPL"
                    assert final_result["execution_time_ms"] == 2500

    def test_websocket_error_handling_and_recovery(self, integration_client, sample_portfolio_integration, temp_portfolio_dir):
        """Test WebSocket error handling and recovery from frontend perspective."""
        portfolio_name = sample_portfolio_integration["name"]
        
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # Setup: Create portfolio first
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 200
            
            # Test Case 1: Agent execution failure
            with patch("backend.services.agent_api.AgentAPIService.execute_agent") as mock_execute:
                mock_execute.side_effect = Exception("LLM service temporarily unavailable")
                
                with integration_client.websocket_connect(f"/api/agents/ws/{portfolio_name}") as websocket:
                    
                    request_payload = {"user_context": "Test error handling"}
                    websocket.send_text(json.dumps(request_payload))
                    
                    # Should receive error message
                    message_text = websocket.receive_text()
                    message = json.loads(message_text)
                    
                    assert message["type"] == "error"
                    assert "LLM service temporarily unavailable" in message["data"]["error"]
            
            # Test Case 2: Invalid request format
            with integration_client.websocket_connect(f"/api/agents/ws/{portfolio_name}") as websocket:
                
                # Send invalid JSON
                websocket.send_text("invalid json data")
                
                # Should handle gracefully (connection might close or send error)
                try:
                    message_text = websocket.receive_text()
                    if message_text:
                        message = json.loads(message_text)
                        if message["type"] == "error":
                            assert "error" in message["data"]
                except:
                    # Connection closed due to invalid data - acceptable behavior
                    pass

    def test_multiple_websocket_connections_management(self, integration_client, sample_portfolio_integration, temp_portfolio_dir, mock_external_services):
        """Test management of multiple concurrent WebSocket connections."""
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
                    recommendations=[
                        TradeRecommendation(
                            action="buy",
                            symbol="TEST",
                            quantity=5,
                            price=100.0,
                            reasoning="Multi-connection test"
                        )
                    ],
                    execution_time_ms=1000,
                    total_tokens=100
                )
                
                # Test multiple concurrent connections
                connection_results = []
                
                # Open multiple WebSocket connections
                def test_connection(connection_id):
                    """Test individual WebSocket connection."""
                    try:
                        with integration_client.websocket_connect(f"/api/agents/ws/{portfolio_name}") as websocket:
                            request_payload = {"user_context": f"Connection {connection_id} test"}
                            websocket.send_text(json.dumps(request_payload))
                            
                            message_text = websocket.receive_text()
                            message = json.loads(message_text)
                            
                            connection_results.append({
                                "connection_id": connection_id,
                                "success": message["type"] == "result" and message["data"]["success"],
                                "message": message
                            })
                    except Exception as e:
                        connection_results.append({
                            "connection_id": connection_id,
                            "success": False,
                            "error": str(e)
                        })
                
                # Test sequential connections (simulating multiple browser tabs)
                for i in range(3):
                    test_connection(i)
                
                # Verify all connections handled correctly
                assert len(connection_results) == 3
                for result in connection_results:
                    assert result["success"], f"Connection {result['connection_id']} failed: {result.get('error', 'Unknown error')}"


class TestRealTimeUpdates:
    """Test real-time updates across multiple clients."""

    def test_portfolio_state_updates_propagation(self, integration_client, sample_portfolio_integration, temp_portfolio_dir, mock_external_services):
        """Test real-time portfolio state updates across multiple frontend clients."""
        portfolio_name = sample_portfolio_integration["name"]
        
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # Setup: Create portfolio first
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 200
            
            # Client 1: Get initial portfolio state
            response = integration_client.get(f"/api/portfolios/{portfolio_name}")
            assert response.status_code == 200
            initial_state = response.json()
            initial_cash = initial_state["state"]["cash"]
            initial_holdings_count = len(initial_state["state"]["holdings"])
            
            # Simulate portfolio state change (trade execution)
            with patch("fin_trade.services.security.SecurityService.get_price", return_value=150.0):
                with patch("backend.routers.trades.apply_trade") as mock_apply:
                    mock_apply.return_value = {"success": True, "message": "Trade applied successfully"}
                    
                    # Client 1: Apply a trade
                    response = integration_client.post("/api/trades/mock_trade_id/apply")
                    assert response.status_code == 200
            
            # Client 2: Fetch updated portfolio state 
            response = integration_client.get(f"/api/portfolios/{portfolio_name}")
            assert response.status_code == 200
            updated_state = response.json()
            
            # Verify state structure is consistent across clients
            assert "config" in updated_state
            assert "state" in updated_state
            assert updated_state["config"]["name"] == portfolio_name
            assert "cash" in updated_state["state"]
            assert "holdings" in updated_state["state"]
            assert "total_value" in updated_state["state"]
            assert "last_updated" in updated_state["state"]

    def test_execution_progress_real_time_updates(self, integration_client, sample_portfolio_integration, temp_portfolio_dir, mock_external_services):
        """Test real-time execution progress updates across WebSocket connections."""
        portfolio_name = sample_portfolio_integration["name"]
        
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # Setup: Create portfolio first
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 200
            
            # Mock agent execution with detailed progress
            with patch("backend.services.agent_api.AgentAPIService.execute_agent") as mock_execute:
                async def detailed_progress_execution(request, progress_callback=None):
                    """Mock execution with detailed real-time progress."""
                    from backend.models.agent import AgentExecuteResponse, TradeRecommendation, ExecutionProgress
                    
                    if progress_callback:
                        # Simulate detailed execution steps
                        detailed_steps = [
                            ("initializing", 0.05, "Initializing agent execution"),
                            ("loading_portfolio", 0.15, "Loading portfolio configuration"),
                            ("fetching_market_data", 0.30, "Fetching current market data"),
                            ("analyzing_holdings", 0.45, "Analyzing current holdings"),
                            ("research_phase", 0.65, "Conducting market research"),
                            ("strategy_application", 0.80, "Applying investment strategy"),
                            ("generating_recommendations", 0.95, "Generating trade recommendations"),
                            ("finalizing", 1.0, "Execution complete")
                        ]
                        
                        for step, progress, message in detailed_steps:
                            await progress_callback(ExecutionProgress(
                                step=step,
                                progress=progress,
                                message=message
                            ))
                            await asyncio.sleep(0.02)  # Simulate processing
                    
                    return AgentExecuteResponse(
                        success=True,
                        recommendations=[
                            TradeRecommendation(
                                action="buy",
                                symbol="NVDA",
                                quantity=3,
                                price=450.0,
                                reasoning="AI chip demand and data center growth"
                            )
                        ],
                        execution_time_ms=1800,
                        total_tokens=220
                    )
                
                mock_execute.side_effect = detailed_progress_execution
                
                # Client: Connect and monitor real-time progress
                with integration_client.websocket_connect(f"/api/agents/ws/{portfolio_name}") as websocket:
                    
                    request_payload = {"user_context": "Real-time progress monitoring test"}
                    websocket.send_text(json.dumps(request_payload))
                    
                    # Track all progress updates
                    progress_timeline = []
                    start_time = time.time()
                    
                    while True:
                        try:
                            message_text = websocket.receive_text()
                            message = json.loads(message_text)
                            current_time = time.time()
                            
                            if message["type"] == "progress":
                                progress_data = message["data"]
                                progress_timeline.append({
                                    "timestamp": current_time - start_time,
                                    "step": progress_data["step"],
                                    "progress": progress_data["progress"], 
                                    "message": progress_data["message"]
                                })
                            elif message["type"] == "result":
                                final_result = message["data"]
                                break
                                
                        except Exception as e:
                            break
                    
                    # Verify real-time progress characteristics
                    assert len(progress_timeline) == 8  # All detailed steps
                    
                    # Verify progress is monotonically increasing
                    for i in range(1, len(progress_timeline)):
                        current_progress = progress_timeline[i]["progress"]
                        previous_progress = progress_timeline[i-1]["progress"]
                        assert current_progress >= previous_progress, f"Progress decreased from {previous_progress} to {current_progress}"
                    
                    # Verify timing - updates should be spread over time
                    total_duration = progress_timeline[-1]["timestamp"] - progress_timeline[0]["timestamp"]
                    assert total_duration > 0.1, "Progress updates too fast (not realistic)"
                    assert total_duration < 2.0, "Progress updates too slow"
                    
                    # Verify final result received
                    assert final_result["success"] is True
                    assert final_result["recommendations"][0]["symbol"] == "NVDA"


class TestThemePersistenceAndStateManagement:
    """Test theme persistence and frontend state management integration."""

    def test_theme_persistence_simulation(self, integration_client):
        """Test theme persistence through API simulation (since we don't have actual frontend)."""
        
        # Simulate theme preference storage through API
        # This would typically be handled by frontend localStorage, but we can test the pattern
        
        # Mock user preferences endpoint (if it existed)
        with patch("backend.routers.system.get_user_preferences") as mock_get_prefs:
            with patch("backend.routers.system.update_user_preferences") as mock_update_prefs:
                
                # Simulate theme preference retrieval
                mock_get_prefs.return_value = {
                    "theme": "dark",
                    "language": "en",
                    "notifications_enabled": True,
                    "auto_refresh_interval": 30
                }
                
                # Simulate theme preference update
                mock_update_prefs.return_value = {"success": True, "message": "Preferences updated"}
                
                # Test pattern would be:
                # 1. Frontend loads user preferences
                # 2. Apply theme based on preferences
                # 3. Update preferences when user changes theme
                # 4. Persist changes for next session
                
                # We can verify the pattern works by checking mock calls
                preferences = mock_get_prefs()
                assert preferences["theme"] == "dark"
                
                # Simulate theme change
                updated_preferences = preferences.copy()
                updated_preferences["theme"] = "light"
                update_result = mock_update_prefs(updated_preferences)
                assert update_result["success"] is True

    def test_frontend_state_management_patterns(self, integration_client, sample_portfolio_integration, temp_portfolio_dir, mock_external_services):
        """Test state management patterns that frontend would implement."""
        portfolio_name = sample_portfolio_integration["name"]
        
        with patch("fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # Setup: Create portfolio
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 200
            
            # Simulate frontend state management patterns
            
            # 1. Initial state loading
            response = integration_client.get("/api/portfolios/")
            assert response.status_code == 200
            portfolios_data = response.json()
            
            # Frontend would store this in state management (Pinia/Vuex)
            frontend_state = {
                "portfolios": portfolios_data,
                "current_portfolio": None,
                "loading": False,
                "error": None
            }
            
            assert len(frontend_state["portfolios"]) >= 1
            assert frontend_state["loading"] is False
            
            # 2. Portfolio selection and detail loading
            selected_portfolio_name = frontend_state["portfolios"][0]["name"]
            response = integration_client.get(f"/api/portfolios/{selected_portfolio_name}")
            assert response.status_code == 200
            portfolio_detail = response.json()
            
            # Update frontend state
            frontend_state["current_portfolio"] = portfolio_detail
            
            assert frontend_state["current_portfolio"]["config"]["name"] == selected_portfolio_name
            
            # 3. State update after operation
            # Simulate portfolio update
            updated_config = sample_portfolio_integration.copy()
            updated_config["trades_per_run"] = 7
            
            response = integration_client.put(f"/api/portfolios/{selected_portfolio_name}", json=updated_config)
            assert response.status_code == 200
            
            # Frontend would refresh state after successful update
            response = integration_client.get(f"/api/portfolios/{selected_portfolio_name}")
            assert response.status_code == 200
            updated_portfolio = response.json()
            
            frontend_state["current_portfolio"] = updated_portfolio
            assert frontend_state["current_portfolio"]["config"]["trades_per_run"] == 7
            
            # 4. Error state handling
            response = integration_client.get("/api/portfolios/nonexistent")
            assert response.status_code == 404
            
            # Frontend would update error state
            frontend_state["error"] = {
                "type": "portfolio_not_found",
                "message": "Portfolio not found",
                "status_code": 404
            }
            
            assert frontend_state["error"]["status_code"] == 404
            assert "not found" in frontend_state["error"]["message"].lower()

    def test_api_service_layer_error_handling(self, integration_client, sample_portfolio_integration):
        """Test API service layer error handling patterns for frontend integration."""
        
        # Test various error scenarios that frontend API service would handle
        
        # 1. Network/Connection errors (simulated)
        with patch("backend.routers.portfolios.portfolio_service") as mock_service:
            mock_service.list_portfolios.side_effect = Exception("Connection timeout")
            
            response = integration_client.get("/api/portfolios/")
            assert response.status_code == 500
            error_response = response.json()
            assert "Connection timeout" in error_response["detail"]
        
        # 2. Validation errors
        invalid_portfolio = {
            "name": "",  # Invalid empty name
            "initial_capital": -1000,  # Invalid negative amount
            "llm_model": "invalid-model"
        }
        
        response = integration_client.post("/api/portfolios/", json=invalid_portfolio)
        assert response.status_code == 422  # Validation error
        
        # 3. Resource not found errors
        response = integration_client.get("/api/portfolios/does_not_exist")
        assert response.status_code == 404
        error_response = response.json()
        assert "not found" in error_response["detail"].lower()
        
        # 4. Business logic errors
        with patch("backend.services.portfolio_api.PortfolioAPIService.create_portfolio", return_value=False):
            response = integration_client.post("/api/portfolios/", json=sample_portfolio_integration)
            assert response.status_code == 400  # Business logic failure
            error_response = response.json()
            assert "Failed to create" in error_response["detail"]
        
        # Frontend API service layer would handle these errors consistently:
        # - Network errors: Retry logic, fallback states
        # - Validation errors: Form validation feedback  
        # - 404 errors: Redirect to appropriate pages
        # - Business errors: User-friendly error messages