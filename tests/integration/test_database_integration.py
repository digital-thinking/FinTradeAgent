"""Database Integration Tests - Persistence, transactions, and concurrency."""

import pytest
import tempfile
import shutil
import json
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor


class TestDataPersistenceIntegration:
    """Test data persistence and retrieval across the application."""

    def test_portfolio_state_persistence_workflow(self, temp_portfolio_dir, mock_external_services):
        """Test complete portfolio state persistence across operations."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.portfolio import PortfolioService
            from backend.fin_trade.models import PortfolioConfig
            
            portfolio_service = PortfolioService()
            portfolio_name = "persistence_test_portfolio"
            
            # 1. CREATE and persist portfolio
            config = PortfolioConfig(
                name=portfolio_name,
                strategy_prompt="Persistence testing strategy",
                initial_amount=15000.0,
                num_initial_trades=3,
                trades_per_run=2,
                run_frequency="weekly",
                llm_provider="openai",
                llm_model="gpt-4",
                agent_mode="simple"
            )
            
            success = portfolio_service.create_portfolio(config)
            assert success, "Portfolio creation failed"
            
            # Verify files were created
            portfolio_config_file = temp_portfolio_dir["portfolios"] / f"{portfolio_name}.yaml"
            portfolio_state_file = temp_portfolio_dir["state"] / f"{portfolio_name}.json"
            assert portfolio_config_file.exists(), "Portfolio config file not created"
            assert portfolio_state_file.exists(), "Portfolio state file not created"
            
            # 2. EXECUTE trades and verify persistence
            with patch("fin_trade.services.security.SecurityService.get_price", return_value=200.0):
                with patch("fin_trade.services.portfolio.PortfolioService.execute_trade") as mock_execute:
                    # Mock successful trade execution that updates state
                    def mock_trade_execution(portfolio_name, ticker, action, quantity, price):
                        # Simulate state update
                        portfolio = portfolio_service.get_portfolio(portfolio_name)
                        if portfolio and action == "buy":
                            # Update portfolio state (simplified)
                            portfolio.state.cash -= quantity * price
                            portfolio_service.save_portfolio_state(portfolio_name, portfolio.state)
                        return True
                    
                    mock_execute.side_effect = mock_trade_execution
                    
                    # Execute multiple trades
                    trades = [
                        ("AAPL", "buy", 10, 200.0),
                        ("GOOGL", "buy", 5, 2400.0),
                        ("MSFT", "buy", 8, 300.0)
                    ]
                    
                    for ticker, action, quantity, price in trades:
                        success = portfolio_service.execute_trade(portfolio_name, ticker, action, quantity, price)
                        assert success, f"Trade execution failed for {ticker}"
                    
                    # 3. VERIFY persistence by reloading
                    # Create new service instance to force reload from disk
                    portfolio_service_new = PortfolioService()
                    reloaded_portfolio = portfolio_service_new.get_portfolio(portfolio_name)
                    
                    assert reloaded_portfolio is not None, "Portfolio not found after reload"
                    assert reloaded_portfolio.config.name == portfolio_name
                    # Cash should be reduced from trades
                    assert reloaded_portfolio.state.cash < 15000.0
            
            # 4. UPDATE configuration and verify persistence
            updated_config = config
            updated_config.trades_per_run = 5
            updated_config.strategy_prompt = "Updated persistence testing strategy"
            
            success = portfolio_service.update_portfolio(portfolio_name, updated_config)
            assert success, "Portfolio update failed"
            
            # Verify configuration persistence
            portfolio_service_new2 = PortfolioService()
            updated_portfolio = portfolio_service_new2.get_portfolio(portfolio_name)
            assert updated_portfolio.config.trades_per_run == 5
            assert "Updated persistence" in updated_portfolio.config.strategy_prompt

    def test_execution_log_persistence(self, temp_portfolio_dir, mock_external_services):
        """Test execution log persistence and retrieval."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.execution_log import ExecutionLogService
            from backend.fin_trade.models import ExecutionResult
            
            log_service = ExecutionLogService()
            
            # Create test execution logs
            executions = [
                ExecutionResult(
                    portfolio_name="test_portfolio_1",
                    execution_id="exec_001",
                    timestamp=datetime.now() - timedelta(days=2),
                    status="completed",
                    duration_seconds=45.5,
                    trades_generated=3,
                    tokens_used=250,
                    error_message=None
                ),
                ExecutionResult(
                    portfolio_name="test_portfolio_1", 
                    execution_id="exec_002",
                    timestamp=datetime.now() - timedelta(days=1),
                    status="failed",
                    duration_seconds=15.2,
                    trades_generated=0,
                    tokens_used=100,
                    error_message="Market data unavailable"
                ),
                ExecutionResult(
                    portfolio_name="test_portfolio_2",
                    execution_id="exec_003", 
                    timestamp=datetime.now(),
                    status="completed",
                    duration_seconds=38.7,
                    trades_generated=2,
                    tokens_used=180,
                    error_message=None
                )
            ]
            
            # Persist execution logs
            for execution in executions:
                log_service.log_execution(execution)
            
            # Test retrieval by portfolio
            portfolio_1_logs = log_service.get_portfolio_logs("test_portfolio_1")
            assert len(portfolio_1_logs) == 2
            assert portfolio_1_logs[0].status == "failed"  # Most recent first
            assert portfolio_1_logs[1].status == "completed"
            
            # Test retrieval by date range
            recent_logs = log_service.get_logs_by_date_range(
                datetime.now() - timedelta(days=1),
                datetime.now() + timedelta(days=1)
            )
            assert len(recent_logs) >= 2  # Should include exec_002 and exec_003
            
            # Test persistence across service instances
            log_service_new = ExecutionLogService()
            all_logs = log_service_new.get_recent_logs(limit=10)
            assert len(all_logs) == 3

    def test_market_data_caching_persistence(self, temp_portfolio_dir, mock_external_services):
        """Test market data caching and persistence."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.stock_data import StockDataService
            from backend.fin_trade.cache import CacheManager
            
            stock_service = StockDataService()
            cache_manager = CacheManager()
            
            # Mock external API responses
            with patch("yfinance.Ticker") as mock_ticker:
                mock_ticker_instance = MagicMock()
                mock_ticker_instance.info = {
                    "shortName": "Apple Inc.",
                    "currentPrice": 155.0,
                    "regularMarketPrice": 155.0
                }
                mock_ticker_instance.history.return_value = MagicMock()
                mock_ticker.return_value = mock_ticker_instance
                
                # First request - should hit external API and cache
                price_context_1 = stock_service.get_price_context("AAPL")
                assert price_context_1.current_price == 155.0
                
                # Verify data was cached
                cached_data = cache_manager.get("stock_data_AAPL")
                assert cached_data is not None
                
                # Mock API to return different price
                mock_ticker_instance.info["currentPrice"] = 160.0
                
                # Second request - should return cached data if within cache period
                price_context_2 = stock_service.get_price_context("AAPL")
                # Should still be cached value
                if cache_manager.is_cached("stock_data_AAPL"):
                    assert price_context_2.current_price == 155.0  # Cached
                else:
                    assert price_context_2.current_price == 160.0  # Fresh


class TestDatabaseTransactions:
    """Test database transaction handling and rollbacks."""

    def test_portfolio_transaction_rollback(self, temp_portfolio_dir, mock_external_services):
        """Test transaction rollback on portfolio operation failure."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.portfolio import PortfolioService
            from backend.fin_trade.models import PortfolioConfig
            
            portfolio_service = PortfolioService()
            portfolio_name = "transaction_test_portfolio"
            
            # Create initial portfolio
            config = PortfolioConfig(
                name=portfolio_name,
                strategy_prompt="Transaction testing",
                initial_amount=20000.0,
                num_initial_trades=2,
                trades_per_run=2,
                run_frequency="daily",
                llm_provider="openai",
                llm_model="gpt-4",
                agent_mode="simple"
            )
            
            portfolio_service.create_portfolio(config)
            initial_portfolio = portfolio_service.get_portfolio(portfolio_name)
            initial_cash = initial_portfolio.state.cash
            
            # Simulate transaction that should rollback
            with patch("fin_trade.services.portfolio.PortfolioService.save_portfolio_state") as mock_save:
                # Make save operation fail after trade execution
                mock_save.side_effect = Exception("Disk write failed")
                
                with patch("fin_trade.services.security.SecurityService.get_price", return_value=100.0):
                    # Attempt trade that should rollback due to save failure
                    success = portfolio_service.execute_trade(portfolio_name, "AAPL", "buy", 10, 100.0)
                    
                    # Trade should fail due to save error
                    assert not success, "Trade should have failed due to save error"
                    
                    # Portfolio state should remain unchanged
                    portfolio_after_failed_trade = portfolio_service.get_portfolio(portfolio_name)
                    assert portfolio_after_failed_trade.state.cash == initial_cash
                    assert len(portfolio_after_failed_trade.state.holdings) == 0

    def test_concurrent_portfolio_operations(self, temp_portfolio_dir, mock_external_services):
        """Test concurrent portfolio operations with transaction isolation."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.portfolio import PortfolioService
            from backend.fin_trade.models import PortfolioConfig
            
            # Create multiple portfolio services (simulating concurrent requests)
            portfolio_services = [PortfolioService() for _ in range(3)]
            portfolio_name = "concurrent_test_portfolio"
            
            # Create initial portfolio
            config = PortfolioConfig(
                name=portfolio_name,
                strategy_prompt="Concurrent operation testing",
                initial_amount=30000.0,
                num_initial_trades=3,
                trades_per_run=3,
                run_frequency="daily",
                llm_provider="openai",
                llm_model="gpt-4",
                agent_mode="simple"
            )
            
            portfolio_services[0].create_portfolio(config)
            
            # Define concurrent operations
            results = []
            errors = []
            
            def concurrent_trade_operation(service_index):
                """Execute trade in separate thread."""
                try:
                    service = portfolio_services[service_index]
                    
                    with patch("fin_trade.services.security.SecurityService.get_price", return_value=150.0):
                        # Each thread attempts different trades
                        tickers = ["AAPL", "GOOGL", "MSFT"]
                        ticker = tickers[service_index]
                        
                        success = service.execute_trade(portfolio_name, ticker, "buy", 5, 150.0)
                        results.append((service_index, ticker, success))
                        
                except Exception as e:
                    errors.append((service_index, str(e)))
            
            # Execute concurrent operations
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(concurrent_trade_operation, i) for i in range(3)]
                for future in futures:
                    future.result()  # Wait for completion
            
            # Verify results
            assert len(errors) == 0, f"Concurrent operations had errors: {errors}"
            assert len(results) == 3, f"Not all operations completed: {results}"
            
            # Check final portfolio state consistency
            final_portfolio = portfolio_services[0].get_portfolio(portfolio_name)
            # All services should see the same final state
            for service in portfolio_services:
                portfolio = service.get_portfolio(portfolio_name)
                assert portfolio.state.cash == final_portfolio.state.cash
                assert len(portfolio.state.holdings) == len(final_portfolio.state.holdings)


class TestConcurrentOperations:
    """Test concurrent operations and data consistency."""

    def test_concurrent_portfolio_creation(self, temp_portfolio_dir, mock_external_services):
        """Test concurrent portfolio creation with unique names."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.portfolio import PortfolioService
            from backend.fin_trade.models import PortfolioConfig
            
            results = []
            errors = []
            
            def create_portfolio_concurrent(portfolio_index):
                """Create portfolio in separate thread."""
                try:
                    service = PortfolioService()
                    config = PortfolioConfig(
                        name=f"concurrent_portfolio_{portfolio_index}",
                        strategy_prompt=f"Concurrent testing strategy {portfolio_index}",
                        initial_amount=10000.0 + (portfolio_index * 1000),
                        num_initial_trades=2,
                        trades_per_run=1,
                        run_frequency="daily",
                        llm_provider="openai",
                        llm_model="gpt-4",
                        agent_mode="simple"
                    )
                    
                    success = service.create_portfolio(config)
                    results.append((portfolio_index, success))
                    
                except Exception as e:
                    errors.append((portfolio_index, str(e)))
            
            # Create multiple portfolios concurrently
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(create_portfolio_concurrent, i) for i in range(5)]
                for future in futures:
                    future.result()
            
            # Verify all portfolios were created successfully
            assert len(errors) == 0, f"Concurrent portfolio creation had errors: {errors}"
            assert len(results) == 5
            assert all(success for _, success in results), "Some portfolio creations failed"
            
            # Verify all portfolios exist and are unique
            service = PortfolioService()
            portfolios = service.list_portfolios()
            portfolio_names = [p.name for p in portfolios]
            
            assert len(portfolio_names) == 5
            assert len(set(portfolio_names)) == 5  # All names should be unique
            
            for i in range(5):
                assert f"concurrent_portfolio_{i}" in portfolio_names

    def test_concurrent_agent_executions(self, temp_portfolio_dir, mock_external_services):
        """Test concurrent agent executions on different portfolios."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.portfolio import PortfolioService
            from backend.fin_trade.services.agent import AgentService
            from backend.fin_trade.models import PortfolioConfig
            
            # Create test portfolios
            portfolio_service = PortfolioService()
            portfolios = []
            
            for i in range(3):
                config = PortfolioConfig(
                    name=f"agent_concurrent_portfolio_{i}",
                    strategy_prompt=f"Concurrent agent testing {i}",
                    initial_amount=15000.0,
                    num_initial_trades=2,
                    trades_per_run=2, 
                    run_frequency="daily",
                    llm_provider="openai",
                    llm_model="gpt-4",
                    agent_mode="simple"
                )
                
                success = portfolio_service.create_portfolio(config)
                assert success
                portfolios.append(config.name)
            
            # Execute agents concurrently
            agent_service = AgentService()
            execution_results = []
            execution_errors = []
            
            def execute_agent_concurrent(portfolio_index):
                """Execute agent in separate thread."""
                try:
                    portfolio_name = portfolios[portfolio_index]
                    
                    # Mock LLM response
                    with patch("fin_trade.services.llm_provider.LLMProvider") as mock_llm:
                        mock_llm_instance = MagicMock()
                        mock_llm_instance.generate_completion.return_value = {
                            "trades": [
                                {
                                    "ticker": f"TEST{portfolio_index}",
                                    "action": "BUY",
                                    "quantity": 5 + portfolio_index,
                                    "reasoning": f"Concurrent test reasoning {portfolio_index}"
                                }
                            ],
                            "overall_reasoning": f"Concurrent execution test {portfolio_index}"
                        }
                        mock_llm.return_value = mock_llm_instance
                        
                        result = agent_service.execute_agent(
                            portfolio_name,
                            user_context=f"Concurrent test context {portfolio_index}"
                        )
                        
                        execution_results.append((portfolio_index, result.success, len(result.recommendations.trades) if result.success else 0))
                        
                except Exception as e:
                    execution_errors.append((portfolio_index, str(e)))
            
            # Run concurrent executions
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(execute_agent_concurrent, i) for i in range(3)]
                for future in futures:
                    future.result()
            
            # Verify all executions completed successfully
            assert len(execution_errors) == 0, f"Concurrent agent executions had errors: {execution_errors}"
            assert len(execution_results) == 3
            assert all(success for _, success, _ in execution_results), "Some agent executions failed"
            assert all(trades > 0 for _, success, trades in execution_results if success), "Some executions produced no trades"


class TestExternalDependencyMocking:
    """Test mocking of external dependencies in integration scenarios."""

    def test_yfinance_api_mocking(self, temp_portfolio_dir):
        """Test comprehensive yfinance API mocking for integration tests."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.stock_data import StockDataService
            
            # Mock yfinance with comprehensive data
            with patch("yfinance.Ticker") as mock_ticker:
                # Setup mock ticker with complete data
                mock_ticker_instance = MagicMock()
                
                # Mock info data
                mock_ticker_instance.info = {
                    "shortName": "Apple Inc.",
                    "currentPrice": 175.0,
                    "regularMarketPrice": 175.0,
                    "currency": "USD",
                    "marketCap": 2800000000000,
                    "trailingPE": 28.5,
                    "forwardPE": 26.2,
                    "dividendYield": 0.0055,
                    "beta": 1.2,
                    "52WeekHigh": 198.23,
                    "52WeekLow": 129.04
                }
                
                # Mock historical data  
                import pandas as pd
                historical_data = pd.DataFrame({
                    'Open': [170.0, 172.0, 174.0, 176.0, 175.0],
                    'High': [172.0, 174.0, 176.0, 178.0, 177.0], 
                    'Low': [168.0, 170.0, 172.0, 174.0, 173.0],
                    'Close': [171.0, 173.0, 175.0, 177.0, 175.0],
                    'Volume': [50000000, 45000000, 55000000, 60000000, 48000000]
                }, index=pd.date_range('2024-01-01', periods=5, freq='D'))
                
                mock_ticker_instance.history.return_value = historical_data
                mock_ticker.return_value = mock_ticker_instance
                
                # Test service integration with mocked data
                stock_service = StockDataService()
                
                # Test price context generation
                price_context = stock_service.get_price_context("AAPL")
                assert price_context.current_price == 175.0
                assert price_context.high_52w == 198.23
                assert price_context.low_52w == 129.04
                
                # Test multiple ticker handling
                tickers = ["AAPL", "GOOGL", "MSFT"] 
                contexts = stock_service.get_holdings_context(tickers)
                assert len(contexts) == 3
                assert all(ticker in contexts for ticker in tickers)

    def test_llm_provider_mocking(self, temp_portfolio_dir):
        """Test comprehensive LLM provider mocking for integration tests."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.llm_provider import LLMProvider
            
            # Mock OpenAI
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                
                # Mock chat completion response
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message = MagicMock()
                mock_response.choices[0].message.content = json.dumps({
                    "trades": [
                        {
                            "ticker": "AAPL",
                            "action": "BUY",
                            "quantity": 10,
                            "reasoning": "Strong fundamentals and technical indicators"
                        }
                    ],
                    "overall_reasoning": "Market conditions favor technology stocks"
                })
                mock_response.usage = MagicMock()
                mock_response.usage.total_tokens = 250
                
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                # Test LLM provider integration
                llm_provider = LLMProvider("openai", "gpt-4")
                
                prompt = "Analyze the following portfolio and recommend trades..."
                response = llm_provider.generate_completion(prompt)
                
                assert "trades" in response
                assert len(response["trades"]) == 1
                assert response["trades"][0]["ticker"] == "AAPL"
                assert response["overall_reasoning"] is not None
                
                # Verify API was called correctly
                mock_client.chat.completions.create.assert_called_once()
                call_args = mock_client.chat.completions.create.call_args
                assert "messages" in call_args[1]
                assert call_args[1]["model"] == "gpt-4"

    def test_anthropic_provider_mocking(self, temp_portfolio_dir):
        """Test Anthropic API mocking for integration tests."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.llm_provider import LLMProvider
            
            # Mock Anthropic
            with patch("anthropic.Anthropic") as mock_anthropic:
                mock_client = MagicMock()
                
                # Mock message response
                mock_response = MagicMock()
                mock_response.content = [MagicMock()]
                mock_response.content[0].text = json.dumps({
                    "trades": [
                        {
                            "ticker": "GOOGL",
                            "action": "BUY", 
                            "quantity": 5,
                            "reasoning": "AI leadership and strong cloud growth"
                        },
                        {
                            "ticker": "MSFT",
                            "action": "BUY",
                            "quantity": 8,
                            "reasoning": "Enterprise software dominance and Azure growth"
                        }
                    ],
                    "overall_reasoning": "Technology giants showing strong fundamentals"
                })
                mock_response.usage = MagicMock()
                mock_response.usage.input_tokens = 100
                mock_response.usage.output_tokens = 150
                
                mock_client.messages.create.return_value = mock_response
                mock_anthropic.return_value = mock_client
                
                # Test Anthropic provider integration
                llm_provider = LLMProvider("anthropic", "claude-3-haiku")
                
                prompt = "Generate trade recommendations based on market analysis..."
                response = llm_provider.generate_completion(prompt)
                
                assert "trades" in response
                assert len(response["trades"]) == 2
                assert response["trades"][0]["ticker"] == "GOOGL"
                assert response["trades"][1]["ticker"] == "MSFT"
                
                # Verify Anthropic API was called
                mock_client.messages.create.assert_called_once()
                call_args = mock_client.messages.create.call_args
                assert "messages" in call_args[1]
                assert call_args[1]["model"] == "claude-3-haiku"

    def test_multiple_external_dependencies_integration(self, temp_portfolio_dir):
        """Test integration scenario with multiple external dependencies mocked."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.agent import AgentService
            from backend.fin_trade.services.portfolio import PortfolioService
            from backend.fin_trade.models import PortfolioConfig
            
            # Mock all external dependencies simultaneously
            with patch("yfinance.Ticker") as mock_yfinance:
                with patch("openai.OpenAI") as mock_openai:
                    
                    # Setup yfinance mock
                    mock_ticker = MagicMock()
                    mock_ticker.info = {"shortName": "Test Stock", "currentPrice": 100.0}
                    mock_yfinance.return_value = mock_ticker
                    
                    # Setup OpenAI mock
                    mock_openai_client = MagicMock()
                    mock_openai_response = MagicMock()
                    mock_openai_response.choices = [MagicMock()]
                    mock_openai_response.choices[0].message = MagicMock()
                    mock_openai_response.choices[0].message.content = json.dumps({
                        "trades": [
                            {"ticker": "TEST", "action": "BUY", "quantity": 10, "reasoning": "Integration test"}
                        ],
                        "overall_reasoning": "Multi-dependency integration test"
                    })
                    mock_openai_client.chat.completions.create.return_value = mock_openai_response
                    mock_openai.return_value = mock_openai_client
                    
                    # Execute complete workflow with all dependencies mocked
                    portfolio_service = PortfolioService()
                    agent_service = AgentService()
                    
                    # Create portfolio
                    config = PortfolioConfig(
                        name="multi_dependency_test",
                        strategy_prompt="Multi-dependency integration test",
                        initial_amount=25000.0,
                        num_initial_trades=3,
                        trades_per_run=2,
                        run_frequency="daily",
                        llm_provider="openai",
                        llm_model="gpt-4",
                        agent_mode="simple"
                    )
                    
                    success = portfolio_service.create_portfolio(config)
                    assert success, "Portfolio creation failed"
                    
                    # Execute agent (uses both yfinance and OpenAI)
                    result = agent_service.execute_agent("multi_dependency_test", "Integration test context")
                    
                    assert result.success, "Agent execution failed"
                    assert len(result.recommendations.trades) == 1
                    assert result.recommendations.trades[0].ticker == "TEST"
                    
                    # Verify both external APIs were called
                    mock_yfinance.assert_called()  # Stock data lookup
                    mock_openai_client.chat.completions.create.assert_called_once()  # LLM completion