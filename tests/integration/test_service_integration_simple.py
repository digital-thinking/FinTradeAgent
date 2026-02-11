"""Simple Service Integration Tests - Basic workflow testing."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestBasicPortfolioWorkflow:
    """Test basic portfolio management workflow integration."""

    def test_portfolio_api_service_basic_workflow(self, temp_portfolio_dir, mock_external_services):
        """Test basic workflow: create portfolio → verify → delete."""
        # Mock the data directory
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # Import API services after patching DATA_DIR
            from backend.services.portfolio_api import PortfolioAPIService
            from backend.models.portfolio import PortfolioConfigRequest
            
            portfolio_service = PortfolioAPIService()
            
            # 1. CREATE PORTFOLIO with correct API fields
            portfolio_config_request = PortfolioConfigRequest(
                name="basic_test_portfolio",
                initial_capital=10000.0,
                llm_model="gpt-4",
                asset_class="stocks",
                agent_mode="simple"
            )
            
            # Create portfolio
            success = portfolio_service.create_portfolio(portfolio_config_request)
            assert success, "Portfolio creation failed"
            
            # 2. VERIFY PORTFOLIO
            portfolio = portfolio_service.get_portfolio("basic_test_portfolio")
            assert portfolio is not None
            assert portfolio.config.name == "basic_test_portfolio"
            
            # 3. LIST PORTFOLIOS
            portfolios = portfolio_service.list_portfolios()
            portfolio_names = [p.name for p in portfolios]
            assert "basic_test_portfolio" in portfolio_names
            
            # 4. DELETE PORTFOLIO
            delete_success = portfolio_service.delete_portfolio("basic_test_portfolio")
            assert delete_success, "Portfolio deletion failed"


class TestBasicAttributionService:
    """Test basic AttributionService functionality."""

    def test_attribution_service_initialization(self, temp_portfolio_dir):
        """Test that AttributionService can be initialized correctly."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.security import SecurityService
            from backend.fin_trade.services.attribution import AttributionService
            
            # Initialize services with required dependencies
            security_service = SecurityService()
            attribution_service = AttributionService(security_service)
            
            # Basic functionality test
            assert attribution_service is not None
            assert attribution_service.security_service is not None


class TestBasicAgentAPIService:
    """Test basic AgentAPIService functionality."""

    def test_agent_api_service_initialization(self, temp_portfolio_dir):
        """Test that AgentAPIService can be initialized correctly.""" 
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.services.agent_api import AgentAPIService
            
            # Initialize service
            agent_service = AgentAPIService()
            
            # Basic functionality test
            assert agent_service is not None