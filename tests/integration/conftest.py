"""Integration test fixtures and configuration."""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
import websockets
from datetime import datetime
import json

# Add project paths
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from backend.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def integration_client():
    """FastAPI test client for integration tests."""
    return TestClient(app)


@pytest.fixture
def temp_portfolio_dir():
    """Create temporary portfolio directory for integration tests."""
    temp_dir = tempfile.mkdtemp()
    portfolio_dir = Path(temp_dir) / "portfolios"
    state_dir = Path(temp_dir) / "state"
    portfolio_dir.mkdir(parents=True)
    state_dir.mkdir(parents=True)
    
    yield {"portfolios": portfolio_dir, "state": state_dir, "root": Path(temp_dir)}
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_portfolio_integration():
    """Sample portfolio for integration testing."""
    return {
        "name": "integration_test_portfolio",
        "initial_capital": 10000.0,
        "llm_model": "gpt-4",
        "llm_provider": "openai",
        "asset_class": "stocks",
        "agent_mode": "langgraph", 
        "run_frequency": "daily",
        "scheduler_enabled": False,
        "auto_apply_trades": False,
        "trades_per_run": 3,
        "strategy_prompt": "Focus on stable growth stocks with strong fundamentals"
    }


@pytest.fixture
def mock_external_services():
    """Mock external API services (yfinance, OpenAI, Anthropic)."""
    mocks = {}
    
    # Mock yfinance
    with patch("yfinance.Ticker") as mock_ticker:
        import pandas as pd
        from datetime import datetime, timedelta
        
        # Create mock price data
        dates = pd.date_range(start=datetime.now() - timedelta(days=365), 
                             end=datetime.now(), freq='D')
        mock_df = pd.DataFrame({
            'Open': [150.0] * len(dates),
            'High': [155.0] * len(dates),
            'Low': [145.0] * len(dates), 
            'Close': [150.0] * len(dates),
            'Volume': [1000000] * len(dates)
        }, index=dates)
        
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {
            "shortName": "Apple Inc.",
            "currentPrice": 150.0,
            "regularMarketPrice": 150.0,
            "currency": "USD"
        }
        mock_ticker_instance.history.return_value = mock_df
        mock_ticker.return_value = mock_ticker_instance
        mocks["yfinance"] = mock_ticker
        
        # Mock OpenAI
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="Mock AI response"))]
            )
            mock_openai.return_value = mock_client
            mocks["openai"] = mock_openai
            
            # Mock Anthropic
            with patch("anthropic.Anthropic") as mock_anthropic:
                mock_anthropic_client = MagicMock()
                mock_anthropic_client.messages.create.return_value = MagicMock(
                    content=[MagicMock(text="Mock Anthropic response")]
                )
                mock_anthropic.return_value = mock_anthropic_client
                mocks["anthropic"] = mock_anthropic
                
                yield mocks


@pytest.fixture
def mock_database_operations():
    """Mock database operations for testing persistence and transactions."""
    mock_db = MagicMock()
    
    # Mock transaction operations
    mock_transaction = MagicMock()
    mock_transaction.__enter__ = MagicMock(return_value=mock_transaction)
    mock_transaction.__exit__ = MagicMock(return_value=None)
    mock_transaction.commit = MagicMock()
    mock_transaction.rollback = MagicMock()
    
    mock_db.transaction = MagicMock(return_value=mock_transaction)
    mock_db.execute = MagicMock()
    mock_db.fetch_all = MagicMock(return_value=[])
    mock_db.fetch_one = MagicMock(return_value=None)
    
    return mock_db


@pytest.fixture
async def websocket_test_server():
    """Create WebSocket test server for integration tests."""
    test_messages = []
    
    async def websocket_handler(websocket, path):
        """Handle WebSocket connections for testing."""
        try:
            await websocket.send(json.dumps({
                "type": "connected",
                "data": {"status": "ready"}
            }))
            
            async for message in websocket:
                test_messages.append(json.loads(message))
                
                # Echo back progress updates
                if "user_context" in json.loads(message):
                    await websocket.send(json.dumps({
                        "type": "progress", 
                        "data": {"step": "initializing", "progress": 0.1}
                    }))
                    
                    await asyncio.sleep(0.1)
                    
                    await websocket.send(json.dumps({
                        "type": "progress",
                        "data": {"step": "executing", "progress": 0.5}
                    }))
                    
                    await asyncio.sleep(0.1)
                    
                    await websocket.send(json.dumps({
                        "type": "result",
                        "data": {
                            "success": True,
                            "recommendations": [
                                {
                                    "action": "buy",
                                    "symbol": "AAPL", 
                                    "quantity": 5,
                                    "price": 150.0,
                                    "reasoning": "Mock integration test recommendation"
                                }
                            ],
                            "execution_time_ms": 1500
                        }
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            pass
    
    # Start test server
    server = await websockets.serve(websocket_handler, "localhost", 8765)
    
    yield test_messages
    
    # Cleanup
    server.close()
    await server.wait_closed()


@pytest.fixture
def integration_test_data():
    """Shared test data for integration tests."""
    return {
        "portfolios": [
            {
                "name": "growth_portfolio", 
                "initial_capital": 50000.0,
                "holdings": [
                    {"symbol": "AAPL", "quantity": 10, "avg_cost": 150.0},
                    {"symbol": "GOOGL", "quantity": 5, "avg_cost": 2500.0}
                ]
            },
            {
                "name": "conservative_portfolio",
                "initial_capital": 25000.0, 
                "holdings": [
                    {"symbol": "VTI", "quantity": 100, "avg_cost": 200.0}
                ]
            }
        ],
        "trades": [
            {
                "portfolio": "growth_portfolio",
                "action": "buy",
                "symbol": "MSFT",
                "quantity": 8,
                "price": 300.0,
                "status": "pending"
            }
        ],
        "market_data": {
            "AAPL": {"price": 155.0, "change_pct": 3.33},
            "GOOGL": {"price": 2600.0, "change_pct": 4.0},
            "MSFT": {"price": 305.0, "change_pct": 1.67},
            "VTI": {"price": 210.0, "change_pct": 5.0}
        }
    }