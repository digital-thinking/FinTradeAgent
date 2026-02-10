"""Unit tests for Portfolio API endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from backend.models.portfolio import PortfolioSummary, PortfolioResponse
from datetime import datetime


class TestPortfoliosAPI:
    """Test cases for /api/portfolios endpoints."""
    
    def test_list_portfolios_success(self, client, mock_portfolio_service):
        """Test successful portfolio listing."""
        # Create mock portfolio summary
        from backend.models.portfolio import PortfolioSummary
        from datetime import datetime
        
        sample_portfolio_summary = PortfolioSummary(
            name="test_portfolio",
            total_value=12500.0,
            cash=2500.0,
            holdings_count=3,
            last_updated=datetime.now(),
            scheduler_enabled=False
        )
        
        # Mock the service response
        mock_portfolio_service.list_portfolios.return_value = [sample_portfolio_summary]
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.get("/api/portfolios/")
            
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "test_portfolio" 
        assert data[0]["total_value"] == 12500.0
        assert data[0]["holdings_count"] == 3
        mock_portfolio_service.list_portfolios.assert_called_once()

    def test_list_portfolios_empty(self, client, mock_portfolio_service):
        """Test portfolio listing when no portfolios exist."""
        mock_portfolio_service.list_portfolios.return_value = []
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.get("/api/portfolios/")
            
        assert response.status_code == 200
        assert response.json() == []

    def test_list_portfolios_server_error(self, client, mock_portfolio_service):
        """Test portfolio listing with server error."""
        mock_portfolio_service.list_portfolios.side_effect = Exception("Database error")
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.get("/api/portfolios/")
            
        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]

    def test_get_portfolio_success(self, client, sample_portfolio_response_api, mock_portfolio_service):
        """Test successful portfolio retrieval."""
        mock_portfolio_service.get_portfolio.return_value = sample_portfolio_response_api
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.get("/api/portfolios/test_portfolio")
            
        assert response.status_code == 200
        data = response.json()
        assert data["config"]["name"] == "test_portfolio"
        assert data["state"]["cash"] == 2500.0
        assert len(data["state"]["holdings"]) == 1
        mock_portfolio_service.get_portfolio.assert_called_once_with("test_portfolio")

    def test_get_portfolio_not_found(self, client, mock_portfolio_service):
        """Test portfolio retrieval when portfolio doesn't exist."""
        mock_portfolio_service.get_portfolio.return_value = None
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.get("/api/portfolios/nonexistent")
            
        assert response.status_code == 404
        assert "Portfolio 'nonexistent' not found" in response.json()["detail"]

    def test_create_portfolio_success(self, client, sample_portfolio_config_api, mock_portfolio_service):
        """Test successful portfolio creation."""
        mock_portfolio_service.create_portfolio.return_value = True
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.post("/api/portfolios/", json=sample_portfolio_config_api)
            
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Portfolio 'test_portfolio' created successfully"
        mock_portfolio_service.create_portfolio.assert_called_once()

    def test_create_portfolio_failure(self, client, sample_portfolio_config_api, mock_portfolio_service):
        """Test portfolio creation failure."""
        mock_portfolio_service.create_portfolio.return_value = False
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.post("/api/portfolios/", json=sample_portfolio_config_api)
            
        assert response.status_code == 400
        assert "Failed to create portfolio" in response.json()["detail"]

    def test_create_portfolio_invalid_data(self, client):
        """Test portfolio creation with invalid data."""
        invalid_config = {
            "name": "test",
            "initial_capital": -1000,  # Invalid negative capital
            "llm_model": "gpt-4"
        }
        
        response = client.post("/api/portfolios/", json=invalid_config)
        assert response.status_code == 422  # Validation error

    def test_create_portfolio_server_error(self, client, sample_portfolio_config_api, mock_portfolio_service):
        """Test portfolio creation with server error."""
        mock_portfolio_service.create_portfolio.side_effect = Exception("Database connection failed")
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.post("/api/portfolios/", json=sample_portfolio_config_api)
            
        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]

    def test_update_portfolio_success(self, client, sample_portfolio_config_api, mock_portfolio_service):
        """Test successful portfolio update."""
        mock_portfolio_service.update_portfolio.return_value = True
        updated_config = sample_portfolio_config_api.copy()
        updated_config["initial_capital"] = 15000.0
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.put("/api/portfolios/test_portfolio", json=updated_config)
            
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Portfolio 'test_portfolio' updated successfully"
        mock_portfolio_service.update_portfolio.assert_called_once()

    def test_update_portfolio_not_found(self, client, sample_portfolio_config_api, mock_portfolio_service):
        """Test portfolio update when portfolio doesn't exist."""
        mock_portfolio_service.update_portfolio.return_value = False
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.put("/api/portfolios/nonexistent", json=sample_portfolio_config_api)
            
        assert response.status_code == 404
        assert "Portfolio 'nonexistent' not found" in response.json()["detail"]

    def test_update_portfolio_invalid_data(self, client):
        """Test portfolio update with invalid data."""
        invalid_config = {
            "name": "test",
            "initial_capital": "not_a_number",
            "llm_model": "gpt-4"
        }
        
        response = client.put("/api/portfolios/test_portfolio", json=invalid_config)
        assert response.status_code == 422  # Validation error

    def test_update_portfolio_server_error(self, client, sample_portfolio_config_api, mock_portfolio_service):
        """Test portfolio update with server error."""
        mock_portfolio_service.update_portfolio.side_effect = Exception("Update failed")
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.put("/api/portfolios/test_portfolio", json=sample_portfolio_config_api)
            
        assert response.status_code == 500
        assert "Update failed" in response.json()["detail"]

    def test_delete_portfolio_success(self, client, mock_portfolio_service):
        """Test successful portfolio deletion."""
        mock_portfolio_service.delete_portfolio.return_value = True
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.delete("/api/portfolios/test_portfolio")
            
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Portfolio 'test_portfolio' deleted successfully"
        mock_portfolio_service.delete_portfolio.assert_called_once_with("test_portfolio")

    def test_delete_portfolio_not_found(self, client, mock_portfolio_service):
        """Test portfolio deletion when portfolio doesn't exist."""
        mock_portfolio_service.delete_portfolio.return_value = False
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.delete("/api/portfolios/nonexistent")
            
        assert response.status_code == 404
        assert "Portfolio 'nonexistent' not found" in response.json()["detail"]

    def test_delete_portfolio_server_error(self, client, mock_portfolio_service):
        """Test portfolio deletion with server error."""
        mock_portfolio_service.delete_portfolio.side_effect = Exception("Delete failed")
        
        with patch("backend.routers.portfolios.portfolio_service", mock_portfolio_service):
            response = client.delete("/api/portfolios/test_portfolio")
            
        assert response.status_code == 500
        assert "Delete failed" in response.json()["detail"]