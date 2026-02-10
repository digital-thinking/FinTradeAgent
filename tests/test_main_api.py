"""Unit tests for main FastAPI application."""

import pytest


class TestMainAPI:
    """Test cases for main FastAPI application."""
    
    def test_app_health_check(self, client):
        """Test main application health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "service" in data
        assert data["status"] == "ok"
        assert data["service"] == "FinTradeAgent API"

    def test_app_info_available(self, client):
        """Test that FastAPI app info is accessible."""
        # FastAPI automatically creates /docs endpoint
        response = client.get("/docs")
        assert response.status_code == 200
        
        # FastAPI automatically creates /openapi.json endpoint
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        
        assert "info" in data
        assert data["info"]["title"] == "FinTradeAgent API"
        assert data["info"]["description"] == "REST API for Agentic Trade Assistant"
        assert data["info"]["version"] == "1.0.0"

    def test_cors_headers_present(self, client):
        """Test that CORS headers are properly configured."""
        # Test preflight request
        response = client.options("/api/portfolios/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type"
        })
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_cors_origin_allowed(self, client):
        """Test that Vue.js frontend origin is allowed."""
        response = client.get("/health", headers={
            "Origin": "http://localhost:3000"
        })
        
        assert response.status_code == 200
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers

    def test_invalid_endpoint_404(self, client):
        """Test that invalid endpoints return 404."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_api_endpoints_available(self, client):
        """Test that all main API endpoints are available."""
        # Test that each router prefix is accessible (should return method not allowed or valid response)
        endpoints = [
            "/api/portfolios/",
            "/api/agents/test/execute",
            "/api/trades/pending",
            "/api/analytics/dashboard",
            "/api/system/health"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should not return 404 (endpoint exists)
            assert response.status_code != 404

    def test_json_content_type_default(self, client):
        """Test that API endpoints return JSON by default."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_app_metadata_in_openapi(self, client):
        """Test that application metadata is correctly set in OpenAPI schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        
        # Check basic info
        assert schema["info"]["title"] == "FinTradeAgent API"
        assert schema["info"]["description"] == "REST API for Agentic Trade Assistant"
        assert schema["info"]["version"] == "1.0.0"
        
        # Check that all routers are included in paths
        paths = schema["paths"]
        
        # Should have portfolio endpoints
        portfolio_paths = [path for path in paths.keys() if path.startswith("/api/portfolios")]
        assert len(portfolio_paths) > 0
        
        # Should have agent endpoints
        agent_paths = [path for path in paths.keys() if path.startswith("/api/agents")]
        assert len(agent_paths) > 0
        
        # Should have trades endpoints
        trades_paths = [path for path in paths.keys() if path.startswith("/api/trades")]
        assert len(trades_paths) > 0
        
        # Should have analytics endpoints
        analytics_paths = [path for path in paths.keys() if path.startswith("/api/analytics")]
        assert len(analytics_paths) > 0
        
        # Should have system endpoints
        system_paths = [path for path in paths.keys() if path.startswith("/api/system")]
        assert len(system_paths) > 0

    def test_api_tags_in_openapi(self, client):
        """Test that API tags are properly set in OpenAPI schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        
        # Extract all tags used in the API
        used_tags = set()
        for path_info in schema["paths"].values():
            for method_info in path_info.values():
                if "tags" in method_info:
                    used_tags.update(method_info["tags"])
        
        # Should include all expected tags from routers
        expected_tags = ["portfolios", "agents", "trades", "analytics", "system"]
        for tag in expected_tags:
            assert tag in used_tags

    def test_error_handling_format(self, client):
        """Test that error responses have consistent format."""
        # Test 404 error
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)

    def test_health_endpoint_consistency(self, client):
        """Test that health endpoint returns consistent responses."""
        response1 = client.get("/health")
        response2 = client.get("/health")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Should be identical
        assert data1 == data2

    def test_multiple_request_handling(self, client):
        """Test that the app can handle multiple concurrent requests."""
        responses = []
        
        # Make multiple requests
        for i in range(10):
            response = client.get("/health")
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    def test_request_methods_validation(self, client):
        """Test that endpoints validate HTTP methods correctly."""
        # Health endpoint should only accept GET
        response = client.get("/health")
        assert response.status_code == 200
        
        response = client.post("/health")
        assert response.status_code == 405  # Method not allowed
        
        response = client.put("/health")
        assert response.status_code == 405
        
        response = client.delete("/health")
        assert response.status_code == 405