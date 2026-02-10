"""Unit tests for Analytics API endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class MockExecutionLog:
    """Mock execution log model."""
    def __init__(self, log_id, timestamp, portfolio_name, agent_mode, model, duration_ms, success, num_trades, error_message=None):
        self.id = log_id
        self.timestamp = timestamp
        self.portfolio_name = portfolio_name
        self.agent_mode = agent_mode
        self.model = model
        self.duration_ms = duration_ms
        self.success = success
        self.num_trades = num_trades
        self.error_message = error_message


class TestAnalyticsAPI:
    """Test cases for /api/analytics endpoints."""
    
    def test_get_execution_logs_success(self, client, mock_execution_log_service):
        """Test successful retrieval of execution logs."""
        # Create mock logs
        mock_logs = [
            MockExecutionLog(
                log_id=1,
                timestamp=datetime.now() - timedelta(hours=1),
                portfolio_name="tech_portfolio",
                agent_mode="langgraph",
                model="gpt-4",
                duration_ms=2500,
                success=True,
                num_trades=3
            ),
            MockExecutionLog(
                log_id=2,
                timestamp=datetime.now() - timedelta(hours=2),
                portfolio_name="growth_portfolio",
                agent_mode="simple",
                model="gpt-3.5-turbo",
                duration_ms=1800,
                success=False,
                num_trades=0,
                error_message="API rate limit exceeded"
            )
        ]
        
        mock_execution_log_service.get_recent_logs.return_value = mock_logs
        
        with patch("backend.routers.analytics.ExecutionLogService", return_value=mock_execution_log_service):
            response = client.get("/api/analytics/execution-logs")
            
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert len(data["logs"]) == 2
        
        # Verify first log
        log1 = data["logs"][0]
        assert log1["id"] == 1
        assert log1["portfolio_name"] == "tech_portfolio"
        assert log1["agent_mode"] == "langgraph"
        assert log1["model"] == "gpt-4"
        assert log1["duration_ms"] == 2500
        assert log1["success"] is True
        assert log1["num_trades"] == 3
        assert log1["error_message"] is None
        
        # Verify second log
        log2 = data["logs"][1]
        assert log2["id"] == 2
        assert log2["success"] is False
        assert log2["error_message"] == "API rate limit exceeded"

    def test_get_execution_logs_with_limit(self, client, mock_execution_log_service):
        """Test execution logs with custom limit."""
        mock_logs = [
            MockExecutionLog(
                log_id=i,
                timestamp=datetime.now() - timedelta(hours=i),
                portfolio_name=f"portfolio_{i}",
                agent_mode="langgraph",
                model="gpt-4",
                duration_ms=2000 + i * 100,
                success=True,
                num_trades=i
            ) for i in range(1, 11)
        ]
        
        mock_execution_log_service.get_recent_logs.return_value = mock_logs
        
        with patch("backend.routers.analytics.ExecutionLogService", return_value=mock_execution_log_service):
            response = client.get("/api/analytics/execution-logs?limit=10")
            
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 10
        mock_execution_log_service.get_recent_logs.assert_called_with(limit=10)

    def test_get_execution_logs_default_limit(self, client, mock_execution_log_service):
        """Test execution logs with default limit."""
        mock_execution_log_service.get_recent_logs.return_value = []
        
        with patch("backend.routers.analytics.ExecutionLogService", return_value=mock_execution_log_service):
            response = client.get("/api/analytics/execution-logs")
            
        assert response.status_code == 200
        mock_execution_log_service.get_recent_logs.assert_called_with(limit=50)

    def test_get_execution_logs_empty(self, client, mock_execution_log_service):
        """Test execution logs when no logs exist."""
        mock_execution_log_service.get_recent_logs.return_value = []
        
        with patch("backend.routers.analytics.ExecutionLogService", return_value=mock_execution_log_service):
            response = client.get("/api/analytics/execution-logs")
            
        assert response.status_code == 200
        data = response.json()
        assert data["logs"] == []

    def test_get_execution_logs_server_error(self, client, mock_execution_log_service):
        """Test execution logs with server error."""
        mock_execution_log_service.get_recent_logs.side_effect = Exception("Database connection failed")
        
        with patch("backend.routers.analytics.ExecutionLogService", return_value=mock_execution_log_service):
            response = client.get("/api/analytics/execution-logs")
            
        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]

    def test_get_dashboard_data_success(self, client, mock_execution_log_service):
        """Test successful dashboard data retrieval."""
        # Create mock logs with mixed success/failure
        mock_logs = [
            MockExecutionLog(1, datetime.now(), "p1", "langgraph", "gpt-4", 2000, True, 2),
            MockExecutionLog(2, datetime.now(), "p2", "langgraph", "gpt-4", 2500, True, 1),
            MockExecutionLog(3, datetime.now(), "p3", "simple", "gpt-3.5", 1500, False, 0, "Error"),
            MockExecutionLog(4, datetime.now(), "p4", "langgraph", "gpt-4", 3000, True, 3),
        ]
        
        mock_execution_log_service.get_recent_logs.return_value = mock_logs
        
        with patch("backend.routers.analytics.ExecutionLogService", return_value=mock_execution_log_service):
            response = client.get("/api/analytics/dashboard")
            
        assert response.status_code == 200
        data = response.json()
        
        assert "total_executions" in data
        assert "success_rate" in data
        assert "avg_duration_ms" in data
        assert "recent_executions" in data
        
        assert data["total_executions"] == 4
        assert data["success_rate"] == 0.75  # 3 out of 4 successful
        assert data["avg_duration_ms"] == 2250  # (2000+2500+1500+3000)/4
        assert data["recent_executions"] == 3  # 3 successful executions

    def test_get_dashboard_data_empty(self, client, mock_execution_log_service):
        """Test dashboard data when no logs exist."""
        mock_execution_log_service.get_recent_logs.return_value = []
        
        with patch("backend.routers.analytics.ExecutionLogService", return_value=mock_execution_log_service):
            response = client.get("/api/analytics/dashboard")
            
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_executions"] == 0
        assert data["success_rate"] == 0
        assert data["avg_duration_ms"] == 0
        assert data["recent_executions"] == 0

    def test_get_dashboard_data_all_failures(self, client, mock_execution_log_service):
        """Test dashboard data with all failed executions."""
        mock_logs = [
            MockExecutionLog(1, datetime.now(), "p1", "langgraph", "gpt-4", 1000, False, 0, "Error 1"),
            MockExecutionLog(2, datetime.now(), "p2", "simple", "gpt-3.5", 1500, False, 0, "Error 2"),
        ]
        
        mock_execution_log_service.get_recent_logs.return_value = mock_logs
        
        with patch("backend.routers.analytics.ExecutionLogService", return_value=mock_execution_log_service):
            response = client.get("/api/analytics/dashboard")
            
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_executions"] == 2
        assert data["success_rate"] == 0.0
        assert data["avg_duration_ms"] == 1250
        assert data["recent_executions"] == 0

    def test_get_dashboard_data_server_error(self, client, mock_execution_log_service):
        """Test dashboard data with server error."""
        mock_execution_log_service.get_recent_logs.side_effect = Exception("Service unavailable")
        
        with patch("backend.routers.analytics.ExecutionLogService", return_value=mock_execution_log_service):
            response = client.get("/api/analytics/dashboard")
            
        assert response.status_code == 500
        assert "Service unavailable" in response.json()["detail"]

    def test_execution_logs_invalid_limit(self, client, mock_execution_log_service):
        """Test execution logs with invalid limit parameter."""
        mock_execution_log_service.get_recent_logs.return_value = []
        
        with patch("backend.routers.analytics.ExecutionLogService", return_value=mock_execution_log_service):
            # Test with negative limit
            response = client.get("/api/analytics/execution-logs?limit=-5")
            # FastAPI should handle this and may either use default or raise validation error
            assert response.status_code in [200, 422]
            
            # Test with non-integer limit
            response = client.get("/api/analytics/execution-logs?limit=invalid")
            assert response.status_code == 422

    def test_execution_logs_large_limit(self, client, mock_execution_log_service):
        """Test execution logs with very large limit."""
        mock_execution_log_service.get_recent_logs.return_value = []
        
        with patch("backend.routers.analytics.ExecutionLogService", return_value=mock_execution_log_service):
            response = client.get("/api/analytics/execution-logs?limit=10000")
            
        assert response.status_code == 200
        mock_execution_log_service.get_recent_logs.assert_called_with(limit=10000)

    def test_analytics_response_format(self, client, mock_execution_log_service):
        """Test analytics endpoints return properly formatted responses."""
        mock_log = MockExecutionLog(
            1, datetime(2024, 1, 15, 10, 30), "test_portfolio", 
            "langgraph", "gpt-4", 2500, True, 2
        )
        mock_execution_log_service.get_recent_logs.return_value = [mock_log]
        
        with patch("backend.routers.analytics.ExecutionLogService", return_value=mock_execution_log_service):
            # Test execution logs response format
            response = client.get("/api/analytics/execution-logs")
            assert response.status_code == 200
            data = response.json()
            
            assert isinstance(data, dict)
            assert "logs" in data
            assert isinstance(data["logs"], list)
            
            if data["logs"]:
                log = data["logs"][0]
                assert "id" in log
                assert "timestamp" in log
                assert "portfolio_name" in log
                assert "agent_mode" in log
                assert "model" in log
                assert "duration_ms" in log
                assert "success" in log
                assert "num_trades" in log
                assert "error_message" in log
                
                # Verify timestamp is ISO format
                datetime.fromisoformat(log["timestamp"])
            
            # Test dashboard response format
            response = client.get("/api/analytics/dashboard")
            assert response.status_code == 200
            data = response.json()
            
            assert isinstance(data, dict)
            assert "total_executions" in data
            assert "success_rate" in data
            assert "avg_duration_ms" in data
            assert "recent_executions" in data
            
            assert isinstance(data["total_executions"], int)
            assert isinstance(data["success_rate"], (int, float))
            assert isinstance(data["avg_duration_ms"], (int, float))
            assert isinstance(data["recent_executions"], int)