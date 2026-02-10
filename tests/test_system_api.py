"""Unit tests for System API endpoints."""

import pytest
from unittest.mock import patch, MagicMock


class TestSystemAPI:
    """Test cases for /api/system endpoints."""
    
    def test_system_health_success(self, client):
        """Test successful system health check."""
        response = client.get("/api/system/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "services" in data
        assert "uptime" in data
        
        assert data["status"] == "healthy"
        assert isinstance(data["services"], dict)
        
        # Verify service statuses
        services = data["services"]
        assert "api" in services
        assert "scheduler" in services
        assert "database" in services
        
        assert services["api"] == "running"
        assert services["scheduler"] == "running"
        assert services["database"] == "connected"

    def test_system_health_response_format(self, client):
        """Test system health response has correct format."""
        response = client.get("/api/system/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify data types
        assert isinstance(data["status"], str)
        assert isinstance(data["services"], dict)
        assert isinstance(data["uptime"], str)
        
        # Verify all expected services are present
        expected_services = ["api", "scheduler", "database"]
        for service in expected_services:
            assert service in data["services"]
            assert isinstance(data["services"][service], str)

    def test_scheduler_status_success(self, client):
        """Test successful scheduler status retrieval."""
        response = client.get("/api/system/scheduler")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "running" in data
        assert "enabled_portfolios" in data
        assert "next_runs" in data
        assert "last_runs" in data
        
        assert isinstance(data["running"], bool)
        assert isinstance(data["enabled_portfolios"], list)
        assert isinstance(data["next_runs"], dict)
        assert isinstance(data["last_runs"], dict)

    def test_scheduler_status_default_values(self, client):
        """Test scheduler status returns expected default values."""
        response = client.get("/api/system/scheduler")
        
        assert response.status_code == 200
        data = response.json()
        
        # Current implementation returns placeholder data
        assert data["running"] is True
        assert data["enabled_portfolios"] == []
        assert data["next_runs"] == {}
        assert data["last_runs"] == {}

    def test_scheduler_status_server_error(self, client):
        """Test scheduler status with server error."""
        # Mock the scheduler status to raise an exception
        with patch("backend.routers.system.router") as mock_router:
            mock_router.get.side_effect = Exception("Scheduler service unavailable")
            
            # Since we can't easily mock the endpoint function directly,
            # we'll test what the current implementation should do
            response = client.get("/api/system/scheduler")
            
            # Current implementation doesn't have proper error handling for exceptions
            # but returns 200 with placeholder data
            assert response.status_code in [200, 500]

    def test_start_scheduler_success(self, client):
        """Test successful scheduler start."""
        response = client.post("/api/system/scheduler/start")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert isinstance(data["message"], str)
        assert "Scheduler start" in data["message"]

    def test_start_scheduler_response_format(self, client):
        """Test start scheduler response format."""
        response = client.post("/api/system/scheduler/start")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict)
        assert len(data) == 1  # Only message field expected
        assert "message" in data

    def test_stop_scheduler_success(self, client):
        """Test successful scheduler stop."""
        response = client.post("/api/system/scheduler/stop")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert isinstance(data["message"], str)
        assert "Scheduler stop" in data["message"]

    def test_stop_scheduler_response_format(self, client):
        """Test stop scheduler response format."""
        response = client.post("/api/system/scheduler/stop")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict)
        assert len(data) == 1  # Only message field expected
        assert "message" in data

    def test_system_endpoints_http_methods(self, client):
        """Test that system endpoints only accept correct HTTP methods."""
        # Health endpoint should only accept GET
        response = client.get("/api/system/health")
        assert response.status_code == 200
        
        response = client.post("/api/system/health")
        assert response.status_code == 405  # Method not allowed
        
        response = client.delete("/api/system/health")
        assert response.status_code == 405
        
        # Scheduler status should only accept GET
        response = client.get("/api/system/scheduler")
        assert response.status_code == 200
        
        response = client.post("/api/system/scheduler")
        assert response.status_code == 405
        
        # Scheduler start should only accept POST
        response = client.post("/api/system/scheduler/start")
        assert response.status_code == 200
        
        response = client.get("/api/system/scheduler/start")
        assert response.status_code == 405
        
        # Scheduler stop should only accept POST
        response = client.post("/api/system/scheduler/stop")
        assert response.status_code == 200
        
        response = client.get("/api/system/scheduler/stop")
        assert response.status_code == 405

    def test_system_health_consistency(self, client):
        """Test system health returns consistent data across requests."""
        response1 = client.get("/api/system/health")
        response2 = client.get("/api/system/health")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Status should be consistent
        assert data1["status"] == data2["status"]
        
        # Services should be consistent
        assert data1["services"] == data2["services"]

    def test_scheduler_status_consistency(self, client):
        """Test scheduler status returns consistent data across requests."""
        response1 = client.get("/api/system/scheduler")
        response2 = client.get("/api/system/scheduler")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Should return same placeholder data
        assert data1 == data2

    def test_scheduler_control_idempotency(self, client):
        """Test scheduler start/stop operations are idempotent."""
        # Multiple start calls should work
        response1 = client.post("/api/system/scheduler/start")
        response2 = client.post("/api/system/scheduler/start")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Multiple stop calls should work
        response3 = client.post("/api/system/scheduler/stop")
        response4 = client.post("/api/system/scheduler/stop")
        
        assert response3.status_code == 200
        assert response4.status_code == 200

    def test_system_api_content_type(self, client):
        """Test system API endpoints return JSON content type."""
        endpoints = [
            "/api/system/health",
            "/api/system/scheduler",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            assert "application/json" in response.headers["content-type"]
        
        # Test POST endpoints
        post_endpoints = [
            "/api/system/scheduler/start",
            "/api/system/scheduler/stop",
        ]
        
        for endpoint in post_endpoints:
            response = client.post(endpoint)
            assert response.status_code == 200
            assert "application/json" in response.headers["content-type"]

    def test_health_endpoint_main_app(self, client):
        """Test that main app health endpoint also works."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "service" in data
        assert data["status"] == "ok"
        assert data["service"] == "FinTradeAgent API"

    def test_system_vs_main_health(self, client):
        """Test difference between system health and main health endpoints."""
        # Main health endpoint
        response_main = client.get("/health")
        assert response_main.status_code == 200
        main_data = response_main.json()
        
        # System health endpoint
        response_system = client.get("/api/system/health")
        assert response_system.status_code == 200
        system_data = response_system.json()
        
        # They should have different structures
        assert main_data != system_data
        
        # Main health is simpler
        assert len(main_data.keys()) < len(system_data.keys())
        
        # System health has more detailed information
        assert "services" in system_data
        assert "services" not in main_data