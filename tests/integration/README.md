# Integration Tests Documentation

This directory contains comprehensive integration tests for the FinTradeAgent application, covering end-to-end workflows, data flow verification, and system integration scenarios.

## Test Structure

### 1. API Integration Tests (`test_api_integration.py`)
Tests full request/response cycles between frontend and backend:

**TestAPIIntegration**
- `test_portfolio_crud_workflow()` - Complete portfolio CRUD operations through API layers
- `test_agent_execution_workflow()` - Agent execution pipeline with market data integration
- `test_trade_management_workflow()` - Trade application and management workflow
- `test_analytics_data_flow()` - Analytics data flow through all layers
- `test_system_health_monitoring()` - System health monitoring integration
- `test_error_handling_across_layers()` - Error propagation across system boundaries
- `test_concurrent_api_requests()` - Concurrent request handling and consistency

**TestWebSocketIntegration**
- `test_websocket_connection_lifecycle()` - WebSocket connection, execution, and disconnection
- `test_websocket_error_handling()` - WebSocket error handling and recovery
- `test_multiple_websocket_connections()` - Multiple concurrent WebSocket connections

### 2. Service Integration Tests (`test_service_integration.py`)
Tests workflow integration across service layers:

**TestPortfolioWorkflowIntegration**
- `test_portfolio_creation_to_execution_workflow()` - Complete workflow from creation to execution
- `test_portfolio_performance_tracking_workflow()` - Performance tracking across multiple executions

**TestAgentExecutionPipeline**
- `test_agent_execution_with_market_data_integration()` - Agent execution with market data
- `test_agent_execution_with_langgraph_mode()` - LangGraph workflow integration

**TestTradeApplicationProcess**
- `test_trade_recommendation_to_execution_workflow()` - Complete trade lifecycle
- `test_trade_validation_and_risk_management()` - Trade validation and risk controls

**TestSystemHealthMonitoring**
- `test_health_monitoring_across_services()` - Service health monitoring integration
- `test_service_failure_detection_and_recovery()` - Failure detection and recovery
- `test_performance_monitoring_integration()` - Performance metrics tracking

### 3. Database Integration Tests (`test_database_integration.py`)
Tests data persistence, transactions, and concurrency:

**TestDataPersistenceIntegration**
- `test_portfolio_state_persistence_workflow()` - Complete state persistence workflow
- `test_execution_log_persistence()` - Execution log persistence and retrieval
- `test_market_data_caching_persistence()` - Market data caching mechanisms

**TestDatabaseTransactions**
- `test_portfolio_transaction_rollback()` - Transaction rollback on failure
- `test_concurrent_portfolio_operations()` - Concurrent operations with isolation

**TestConcurrentOperations**
- `test_concurrent_portfolio_creation()` - Concurrent portfolio creation
- `test_concurrent_agent_executions()` - Concurrent agent executions

**TestExternalDependencyMocking**
- `test_yfinance_api_mocking()` - Comprehensive yfinance API mocking
- `test_llm_provider_mocking()` - LLM provider (OpenAI/Anthropic) mocking
- `test_multiple_external_dependencies_integration()` - Multi-dependency scenarios

### 4. Frontend-Backend Integration Tests (`test_frontend_backend_integration.py`)
Tests API service layer and real-time features:

**TestAPIServiceLayerIntegration**
- `test_portfolio_api_service_integration()` - Frontend API service for portfolios
- `test_agent_execution_api_service_integration()` - Agent execution API integration
- `test_trades_api_service_integration()` - Trade management API integration
- `test_analytics_api_service_integration()` - Analytics API integration
- `test_system_api_service_integration()` - System API integration

**TestWebSocketConnectionManagement**
- `test_websocket_connection_lifecycle_management()` - WebSocket lifecycle from frontend perspective
- `test_websocket_error_handling_and_recovery()` - Frontend WebSocket error handling
- `test_multiple_websocket_connections_management()` - Multiple connection management

**TestRealTimeUpdates**
- `test_portfolio_state_updates_propagation()` - Real-time state updates across clients
- `test_execution_progress_real_time_updates()` - Real-time execution progress

**TestThemePersistenceAndStateManagement**
- `test_theme_persistence_simulation()` - Theme persistence patterns
- `test_frontend_state_management_patterns()` - State management integration
- `test_api_service_layer_error_handling()` - API service error handling patterns

## Running Integration Tests

### Prerequisites

1. **Environment Setup**
   ```bash
   cd ~/scm/FinTradeAgent
   pip install -e .
   pip install pytest pytest-asyncio httpx websockets
   ```

2. **Test Data Directory**
   Tests use temporary directories for portfolios and state data to ensure isolation.

3. **External Dependencies**
   All external APIs (yfinance, OpenAI, Anthropic) are mocked to ensure reliable, fast tests.

### Running Tests

**Run all integration tests:**
```bash
pytest tests/integration/ -v
```

**Run specific test categories:**
```bash
# API integration tests
pytest tests/integration/test_api_integration.py -v

# Service integration tests  
pytest tests/integration/test_service_integration.py -v

# Database integration tests
pytest tests/integration/test_database_integration.py -v

# Frontend-backend integration tests
pytest tests/integration/test_frontend_backend_integration.py -v
```

**Run with coverage:**
```bash
pytest tests/integration/ --cov=backend/fin_trade --cov=backend --cov-report=html
```

**Run specific test patterns:**
```bash
# WebSocket tests only
pytest tests/integration/ -k "websocket" -v

# Concurrent operation tests
pytest tests/integration/ -k "concurrent" -v

# Error handling tests
pytest tests/integration/ -k "error" -v
```

### Test Configuration

**Async Test Support**
Tests use `pytest-asyncio` for async/await support in WebSocket and concurrent testing.

**Mock Configuration**
- External APIs are comprehensively mocked
- Database operations use temporary directories
- Time-dependent operations use controlled delays

**Fixtures**
- `integration_client` - FastAPI TestClient for HTTP requests
- `temp_portfolio_dir` - Temporary directory structure for tests
- `mock_external_services` - Mocked external API services
- `integration_test_data` - Shared test data across tests

## Test Scenarios Covered

### 1. Data Flow Testing
- **Portfolio Management**: Create → Configure → Execute → Update → Delete
- **Agent Execution**: Initialize → Market Data → Analysis → Recommendations → Completion
- **Trade Processing**: Recommend → Validate → Apply → Confirm → Update Portfolio
- **Analytics Pipeline**: Execute → Log → Aggregate → Report → Display

### 2. Error Handling
- **Network Failures**: Connection timeouts, service unavailable
- **Validation Errors**: Invalid data, constraint violations
- **Business Logic Errors**: Insufficient funds, invalid trades
- **System Errors**: Database failures, external API failures

### 3. Concurrency and Performance
- **Concurrent Portfolio Operations**: Multiple users creating/updating portfolios
- **Concurrent Agent Executions**: Parallel agent runs on different portfolios
- **WebSocket Connection Management**: Multiple simultaneous connections
- **Data Consistency**: Transaction isolation and rollback testing

### 4. Real-Time Features
- **WebSocket Communication**: Progress updates, error handling, reconnection
- **Live Data Updates**: Portfolio state changes, execution progress
- **Multi-Client Synchronization**: State consistency across multiple clients

### 5. External Integration
- **Market Data Integration**: yfinance API integration with caching
- **LLM Provider Integration**: OpenAI and Anthropic API integration
- **Error Recovery**: Handling external service failures gracefully

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Integration Tests
on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio httpx websockets pytest-cov
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v --cov=backend/fin_trade --cov=backend --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Local CI/CD Pipeline

**Pre-commit Integration Tests:**
```bash
#!/bin/bash
# Run integration tests before commits
pytest tests/integration/ -x --tb=short
if [ $? -eq 0 ]; then
    echo "✅ Integration tests passed"
else
    echo "❌ Integration tests failed"
    exit 1
fi
```

**Performance Monitoring:**
```bash
# Run integration tests with timing
pytest tests/integration/ -v --durations=10
```

## Debugging Integration Tests

### Common Issues

1. **Test Database Conflicts**
   - Ensure tests use temporary directories
   - Check for file system permissions
   - Verify cleanup after test failures

2. **WebSocket Connection Issues**
   - Check port availability
   - Verify WebSocket endpoint configuration
   - Monitor connection timeouts

3. **Mock Configuration Problems**
   - Verify mock setup in conftest.py
   - Check external dependency mocking
   - Ensure consistent mock behavior

4. **Timing Issues**
   - Add appropriate delays for async operations
   - Use pytest-asyncio for async test support
   - Monitor concurrent operation timing

### Debug Commands

```bash
# Run single test with detailed output
pytest tests/integration/test_api_integration.py::TestAPIIntegration::test_portfolio_crud_workflow -v -s

# Run with pdb debugger
pytest tests/integration/ --pdb

# Run with extended tracebacks
pytest tests/integration/ -v --tb=long

# Run with logging output
pytest tests/integration/ -v --log-cli-level=INFO
```

## Contributing

When adding new integration tests:

1. **Follow naming conventions**: `test_<workflow>_<scenario>()`
2. **Use appropriate fixtures**: Leverage existing fixtures for setup
3. **Mock external dependencies**: Don't make real API calls
4. **Test error conditions**: Include negative test cases
5. **Document test purpose**: Add docstrings explaining test scenarios
6. **Ensure cleanup**: Use temporary directories and proper teardown

## Performance Benchmarks

Integration test performance targets:
- **Full test suite**: < 5 minutes
- **API integration tests**: < 2 minutes  
- **Service integration tests**: < 1.5 minutes
- **Database integration tests**: < 1 minute
- **Frontend-backend tests**: < 1 minute

Individual test performance:
- **Simple workflow tests**: < 5 seconds
- **Complex integration tests**: < 15 seconds
- **Concurrent operation tests**: < 20 seconds
- **WebSocket tests**: < 10 seconds