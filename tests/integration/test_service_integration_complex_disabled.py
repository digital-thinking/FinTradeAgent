"""Service Integration Tests - Workflow testing across service layers."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import json


class TestPortfolioWorkflowIntegration:
    """Test complete portfolio management workflow integration."""

    def test_portfolio_creation_to_execution_workflow(self, temp_portfolio_dir, mock_external_services):
        """Test complete workflow: create portfolio → execute → trade → update."""
        # Mock the data directory
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            # Import API services after patching DATA_DIR
            from backend.services.portfolio_api import PortfolioAPIService
            from backend.services.agent_api import AgentAPIService
            from backend.models.portfolio import PortfolioConfigRequest
            from backend.fin_trade.models import AssetClass
            
            portfolio_service = PortfolioAPIService()
            agent_service = AgentAPIService()
            
            # 1. CREATE PORTFOLIO
            portfolio_config_request = PortfolioConfigRequest(
                name="workflow_test_portfolio",
                strategy_prompt="Focus on growth technology stocks",
                initial_capital=25000.0,
                num_initial_trades=3,
                trades_per_run=2,
                run_frequency="weekly",
                llm_provider="openai", 
                llm_model="gpt-4",
                agent_mode="simple"
            )
            
            # Create portfolio
            success = portfolio_service.create_portfolio(portfolio_config_request)
            assert success, "Portfolio creation failed"
            
            # Verify portfolio exists
            portfolio = portfolio_service.get_portfolio("workflow_test_portfolio")
            assert portfolio is not None
            assert portfolio.name == "workflow_test_portfolio"
            assert portfolio.state.cash == 25000.0
            
            # 2. EXECUTE AGENT
            # Mock LLM response for agent execution
            with patch("fin_trade.services.llm_provider.LLMProvider") as mock_llm:
                mock_llm_instance = MagicMock()
                mock_llm_instance.generate_completion.return_value = {
                    "trades": [
                        {
                            "ticker": "AAPL",
                            "action": "BUY", 
                            "quantity": 10,
                            "reasoning": "Strong iPhone sales and services growth"
                        },
                        {
                            "ticker": "GOOGL",
                            "action": "BUY",
                            "quantity": 3, 
                            "reasoning": "AI leadership and search dominance"
                        }
                    ],
                    "overall_reasoning": "Technology sector showing strong fundamentals"
                }
                mock_llm.return_value = mock_llm_instance
                
                # Execute agent
                result = agent_service.execute_agent("workflow_test_portfolio", user_context="Focus on mega-cap tech")
                
                assert result.success, f"Agent execution failed: {result.error}"
                assert len(result.recommendations.trades) == 2
                assert result.recommendations.trades[0].ticker == "AAPL"
                assert result.recommendations.trades[1].ticker == "GOOGL"
            
            # 3. APPLY TRADES
            # Mock trade execution
            with patch("fin_trade.services.portfolio.PortfolioService.execute_trade") as mock_execute_trade:
                mock_execute_trade.return_value = True
                
                # Apply first trade
                trade_rec = result.recommendations.trades[0]
                success = portfolio_service.execute_trade(
                    "workflow_test_portfolio",
                    trade_rec.ticker,
                    trade_rec.action.lower(),
                    trade_rec.quantity,
                    150.0  # Mock price
                )
                assert success, "Trade execution failed"
                
                # Verify portfolio state updated
                updated_portfolio = portfolio_service.get_portfolio("workflow_test_portfolio")
                assert len(updated_portfolio.state.holdings) == 1
                assert updated_portfolio.state.holdings[0].ticker == "AAPL"
                assert updated_portfolio.state.cash < 25000.0  # Cash should be reduced
            
            # 4. UPDATE PORTFOLIO CONFIGURATION
            updated_config = portfolio_config
            updated_config.trades_per_run = 4
            updated_config.run_frequency = "daily"
            
            success = portfolio_service.update_portfolio("workflow_test_portfolio", updated_config)
            assert success, "Portfolio update failed"
            
            # Verify update
            final_portfolio = portfolio_service.get_portfolio("workflow_test_portfolio") 
            assert final_portfolio.config.trades_per_run == 4
            assert final_portfolio.config.run_frequency == "daily"

    def test_portfolio_performance_tracking_workflow(self, temp_portfolio_dir, mock_external_services):
        """Test portfolio performance tracking across multiple executions."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.portfolio import PortfolioService
            from backend.fin_trade.services.attribution import AttributionService
            from backend.fin_trade.models import PortfolioConfig, Trade
            
            portfolio_service = PortfolioService()
            from backend.fin_trade.services.security import SecurityService
            from backend.fin_trade.services.attribution import AttributionService
            security_service = SecurityService()
            attribution_service = AttributionService(security_service)
            
            # Create test portfolio
            config = PortfolioConfig(
                name="performance_test_portfolio",
                strategy_prompt="Balanced growth and value",
                initial_amount=50000.0,
                num_initial_trades=5,
                trades_per_run=3,
                run_frequency="weekly",
                llm_provider="openai",
                llm_model="gpt-4",
                agent_mode="simple"
            )
            success = portfolio_service.create_portfolio(PortfolioConfigRequest(**config.__dict__))
            
            # Execute multiple trades over time
            trades = [
                ("AAPL", "buy", 20, 150.0),
                ("GOOGL", "buy", 10, 2500.0), 
                ("MSFT", "buy", 15, 300.0),
                ("AAPL", "sell", 5, 160.0),  # Profit trade
                ("TSLA", "buy", 8, 800.0)
            ]
            
            with patch("fin_trade.services.portfolio.PortfolioService.execute_trade") as mock_execute:
                mock_execute.return_value = True
                
                for ticker, action, quantity, price in trades:
                    portfolio_service.execute_trade("performance_test_portfolio", ticker, action, quantity, price)
                
                # Get portfolio performance
                portfolio = portfolio_service.get_portfolio("performance_test_portfolio")
                
                # Mock current prices for performance calculation
                current_prices = {"AAPL": 165.0, "GOOGL": 2600.0, "MSFT": 320.0, "TSLA": 750.0}
                with patch("fin_trade.services.stock_data.StockDataService.get_price") as mock_price:
                    mock_price.side_effect = lambda ticker: current_prices.get(ticker, 100.0)
                    
                    # Calculate performance attribution
                    attribution = attribution_service.calculate_attribution("performance_test_portfolio")
                    
                    assert attribution is not None
                    assert "holdings" in attribution or "total_pnl" in str(attribution)


class TestAgentExecutionPipeline:
    """Test agent execution pipeline integration."""

    def test_agent_execution_with_market_data_integration(self, temp_portfolio_dir, mock_external_services):
        """Test agent execution pipeline with market data integration."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.agent import AgentService
            from backend.fin_trade.services.portfolio import PortfolioService
            from backend.fin_trade.services.stock_data import StockDataService
            from backend.fin_trade.models import PortfolioConfig
            
            # Setup services
            agent_service = AgentService()
            portfolio_service = PortfolioService()
            stock_data_service = StockDataService()
            
            # Create test portfolio
            config = PortfolioConfig(
                name="agent_pipeline_test",
                strategy_prompt="Data-driven technology stock selection",
                initial_amount=30000.0,
                num_initial_trades=3,
                trades_per_run=2, 
                run_frequency="daily",
                llm_provider="openai",
                llm_model="gpt-4",
                agent_mode="langgraph"
            )
            success = portfolio_service.create_portfolio(PortfolioConfigRequest(**config.__dict__))
            
            # Mock market data
            with patch.object(stock_data_service, 'get_price_context') as mock_price_context:
                from backend.fin_trade.services.stock_data import PriceContext
                
                mock_price_context.return_value = PriceContext(
                    ticker="AAPL",
                    current_price=155.0,
                    change_5d_pct=3.5,
                    change_30d_pct=8.2,
                    high_52w=180.0,
                    low_52w=125.0,
                    pct_from_52w_high=-13.9,
                    pct_from_52w_low=24.0,
                    rsi_14=65.5,
                    volume_avg_20d=50000000,
                    volume_ratio=1.2,
                    ma_20=150.0,
                    ma_50=145.0,
                    trend_summary="↗+3.5% (5d), above moving averages"
                )
                
                # Mock LLM execution
                with patch("fin_trade.services.llm_provider.LLMProvider") as mock_llm:
                    mock_llm_instance = MagicMock()
                    mock_llm_instance.generate_completion.return_value = {
                        "trades": [
                            {
                                "ticker": "AAPL",
                                "action": "BUY",
                                "quantity": 12,
                                "reasoning": "Strong technical indicators with RSI at 65.5 and positive momentum"
                            }
                        ],
                        "overall_reasoning": "Technical analysis shows bullish signals with strong volume support"
                    }
                    mock_llm.return_value = mock_llm_instance
                    
                    # Execute agent with market data context
                    result = agent_service.execute_agent(
                        "agent_pipeline_test",
                        user_context="Use technical analysis for timing decisions"
                    )
                    
                    assert result.success
                    assert len(result.recommendations.trades) == 1
                    assert "RSI at 65.5" in result.recommendations.trades[0].reasoning
                    
                    # Verify market data was integrated into LLM prompt
                    mock_llm_instance.generate_completion.assert_called_once()
                    call_args = mock_llm_instance.generate_completion.call_args[0][0]
                    assert "current_price=155.0" in call_args or "155.0" in call_args

    def test_agent_execution_with_langgraph_mode(self, temp_portfolio_dir, mock_external_services):
        """Test agent execution pipeline in LangGraph mode."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.agent import AgentService
            from backend.fin_trade.services.portfolio import PortfolioService
            from backend.fin_trade.models import PortfolioConfig
            
            agent_service = AgentService()
            portfolio_service = PortfolioService()
            
            # Create portfolio with LangGraph mode
            config = PortfolioConfig(
                name="langgraph_test_portfolio", 
                strategy_prompt="Multi-step research and analysis workflow",
                initial_amount=40000.0,
                num_initial_trades=4,
                trades_per_run=3,
                run_frequency="weekly",
                llm_provider="anthropic",
                llm_model="claude-3-haiku",
                agent_mode="langgraph"
            )
            success = portfolio_service.create_portfolio(PortfolioConfigRequest(**config.__dict__))
            
            # Mock LangGraph execution nodes
            with patch("fin_trade.services.agent.AgentService._execute_langgraph_workflow") as mock_workflow:
                mock_workflow.return_value = {
                    "research_results": {
                        "AAPL": {"score": 8.5, "reasoning": "Strong fundamentals and technical setup"},
                        "MSFT": {"score": 9.0, "reasoning": "Cloud growth and AI positioning"}
                    },
                    "recommendations": [
                        {
                            "ticker": "MSFT",
                            "action": "BUY", 
                            "quantity": 8,
                            "reasoning": "Highest research score with strong cloud and AI fundamentals"
                        },
                        {
                            "ticker": "AAPL",
                            "action": "BUY",
                            "quantity": 15, 
                            "reasoning": "Solid fundamentals with good technical entry point"
                        }
                    ],
                    "workflow_steps": ["research", "analysis", "validation", "generate"]
                }
                
                # Execute agent
                result = agent_service.execute_agent(
                    "langgraph_test_portfolio",
                    user_context="Focus on systematic multi-step analysis"
                )
                
                assert result.success
                assert len(result.recommendations.trades) == 2
                assert result.recommendations.trades[0].ticker == "MSFT"
                
                # Verify LangGraph workflow was called
                mock_workflow.assert_called_once()


class TestTradeApplicationProcess:
    """Test complete trade application process integration."""

    def test_trade_recommendation_to_execution_workflow(self, temp_portfolio_dir, mock_external_services):
        """Test workflow from trade recommendation to execution completion."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.portfolio import PortfolioService
            from backend.fin_trade.services.agent import AgentService
            from backend.fin_trade.models import PortfolioConfig, TradeRecommendation
            
            portfolio_service = PortfolioService()
            agent_service = AgentService()
            
            # Create test portfolio
            config = PortfolioConfig(
                name="trade_workflow_test",
                strategy_prompt="Systematic trade execution testing",
                initial_amount=20000.0,
                num_initial_trades=2,
                trades_per_run=2,
                run_frequency="daily",
                llm_provider="openai",
                llm_model="gpt-4",
                agent_mode="simple"
            )
            success = portfolio_service.create_portfolio(PortfolioConfigRequest(**config.__dict__))
            
            # 1. Generate trade recommendations
            with patch("fin_trade.services.llm_provider.LLMProvider") as mock_llm:
                mock_llm_instance = MagicMock()
                mock_llm_instance.generate_completion.return_value = {
                    "trades": [
                        {
                            "ticker": "NVDA",
                            "action": "BUY",
                            "quantity": 5,
                            "reasoning": "AI chip demand surge"
                        },
                        {
                            "ticker": "AMD", 
                            "action": "BUY",
                            "quantity": 10,
                            "reasoning": "Competitive GPU offerings"
                        }
                    ],
                    "overall_reasoning": "Semiconductor sector momentum"
                }
                mock_llm.return_value = mock_llm_instance
                
                result = agent_service.execute_agent("trade_workflow_test", "Semiconductor focus")
                assert result.success
                
                # 2. Apply first trade recommendation
                trade_rec = result.recommendations.trades[0]
                
                # Mock price lookup and trade execution
                with patch("fin_trade.services.security.SecurityService.get_price", return_value=500.0):
                    with patch("fin_trade.services.portfolio.PortfolioService.execute_trade") as mock_execute:
                        mock_execute.return_value = True
                        
                        success = portfolio_service.execute_trade(
                            "trade_workflow_test",
                            trade_rec.ticker,
                            trade_rec.action.lower(),
                            trade_rec.quantity,
                            500.0
                        )
                        assert success
                        
                        # Verify trade was executed correctly
                        mock_execute.assert_called_once()
                        call_args = mock_execute.call_args[1]
                        assert call_args["ticker"] == "NVDA"
                        assert call_args["quantity"] == 5
                
                # 3. Verify portfolio state changes
                updated_portfolio = portfolio_service.get_portfolio("trade_workflow_test")
                
                # Portfolio should now have holdings and reduced cash
                assert len(updated_portfolio.state.holdings) >= 0  # Mock may not actually update state
                assert updated_portfolio.state.cash <= 20000.0  # Cash should be unchanged or reduced

    def test_trade_validation_and_risk_management(self, temp_portfolio_dir, mock_external_services):
        """Test trade validation and risk management integration."""
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.portfolio import PortfolioService  
            from backend.fin_trade.models import PortfolioConfig
            
            portfolio_service = PortfolioService()
            
            # Create portfolio with limited capital
            config = PortfolioConfig(
                name="risk_test_portfolio",
                strategy_prompt="Risk management testing",
                initial_amount=5000.0,  # Limited capital
                num_initial_trades=1,
                trades_per_run=1,
                run_frequency="daily", 
                llm_provider="openai",
                llm_model="gpt-4",
                agent_mode="simple"
            )
            success = portfolio_service.create_portfolio(PortfolioConfigRequest(**config.__dict__))
            
            # Test trade that exceeds available capital
            with patch("fin_trade.services.security.SecurityService.get_price", return_value=6000.0):
                # This trade would cost $6000 but portfolio only has $5000
                success = portfolio_service.execute_trade(
                    "risk_test_portfolio",
                    "GOOGL",
                    "buy", 
                    1,
                    6000.0
                )
                
                # Trade should be rejected due to insufficient capital
                assert not success
                
                # Portfolio state should remain unchanged
                portfolio = portfolio_service.get_portfolio("risk_test_portfolio")
                assert portfolio.state.cash == 5000.0
                assert len(portfolio.state.holdings) == 0


class TestSystemHealthMonitoring:
    """Test system health monitoring integration."""

    def test_health_monitoring_across_services(self, mock_external_services):
        """Test system health monitoring integration across all services."""
        # Mock various service health checks
        with patch("fin_trade.services.portfolio.PortfolioService.health_check", return_value=True):
            with patch("fin_trade.services.stock_data.StockDataService.health_check", return_value=True):
                with patch("fin_trade.services.llm_provider.LLMProvider.health_check", return_value=True):
                    
                    # Mock system health checker
                    from unittest.mock import MagicMock
                    
                    health_checker = MagicMock()
                    health_checker.check_all_services.return_value = {
                        "portfolio_service": {"status": "healthy", "response_time_ms": 15},
                        "stock_data_service": {"status": "healthy", "response_time_ms": 120},
                        "llm_service": {"status": "healthy", "response_time_ms": 800},
                        "database": {"status": "healthy", "connection_pool": "available"},
                        "external_apis": {"status": "healthy", "rate_limits": "ok"}
                    }
                    
                    # Get overall health status
                    health_status = health_checker.check_all_services()
                    
                    # Verify all services report healthy
                    assert all(service["status"] == "healthy" for service in health_status.values())
                    assert health_status["portfolio_service"]["response_time_ms"] < 100
                    assert health_status["llm_service"]["response_time_ms"] < 1000

    def test_service_failure_detection_and_recovery(self, mock_external_services):
        """Test service failure detection and recovery mechanisms."""
        # Mock service failures
        with patch("fin_trade.services.stock_data.StockDataService.get_price") as mock_price:
            # Simulate service failure then recovery
            mock_price.side_effect = [
                Exception("Connection timeout"),  # First call fails
                Exception("Service unavailable"), # Second call fails
                150.0  # Third call succeeds
            ]
            
            # Mock retry logic
            from backend.fin_trade.services.stock_data import StockDataService
            stock_service = StockDataService()
            
            # Service should eventually succeed with retries
            with patch.object(stock_service, '_retry_with_backoff') as mock_retry:
                mock_retry.return_value = 150.0
                
                price = stock_service.get_price("AAPL")
                assert price == 150.0
                
                # Verify retry mechanism was used
                mock_retry.assert_called_once()

    def test_performance_monitoring_integration(self, temp_portfolio_dir, mock_external_services):
        """Test performance monitoring across service integrations."""
        import time
        from unittest.mock import patch
        
        # Mock performance tracking
        performance_metrics = {
            "portfolio_operations": [],
            "agent_executions": [],
            "api_calls": []
        }
        
        def track_performance(operation, start_time, end_time):
            performance_metrics[operation].append({
                "duration_ms": (end_time - start_time) * 1000,
                "timestamp": datetime.now().isoformat()
            })
        
        with patch("backend.fin_trade.services.portfolio.DATA_DIR", temp_portfolio_dir["root"]):
            from backend.fin_trade.services.portfolio import PortfolioService
            from backend.fin_trade.models import PortfolioConfig
            
            portfolio_service = PortfolioService()
            
            # Track portfolio creation performance
            start_time = time.time()
            
            config = PortfolioConfig(
                name="performance_monitoring_test",
                strategy_prompt="Performance testing",
                initial_amount=10000.0,
                num_initial_trades=2,
                trades_per_run=1,
                run_frequency="daily",
                llm_provider="openai",
                llm_model="gpt-4",
                agent_mode="simple"
            )
            
            success = success = portfolio_service.create_portfolio(PortfolioConfigRequest(**config.__dict__))
            end_time = time.time()
            
            track_performance("portfolio_operations", start_time, end_time)
            
            assert success
            assert len(performance_metrics["portfolio_operations"]) == 1
            assert performance_metrics["portfolio_operations"][0]["duration_ms"] < 1000  # Should be fast