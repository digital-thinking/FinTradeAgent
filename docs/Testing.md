# Testing Documentation

## Overview

This document describes the testing framework and procedures for the FinTradeAgent API endpoints.

## Test Framework

The project uses:
- **pytest**: Main testing framework
- **pytest-asyncio**: For async test support  
- **pytest-cov**: For coverage reporting
- **httpx**: HTTP client for API testing
- **FastAPI TestClient**: For testing FastAPI endpoints

## Test Structure

### Test Files

- `tests/test_main_api.py` - Main FastAPI application tests
- `tests/test_portfolios_api.py` - Portfolio CRUD endpoint tests  
- `tests/test_agents_api.py` - Agent execution endpoint tests (HTTP + WebSocket)
- `tests/test_trades_api.py` - Trade management endpoint tests
- `tests/test_analytics_api.py` - Analytics and dashboard endpoint tests
- `tests/test_system_api.py` - System health and scheduler endpoint tests

### Test Categories

1. **Successful Operations** - Test happy path scenarios
2. **Error Handling** - Test 404, 400, 500 error responses
3. **Data Validation** - Test request/response validation 
4. **Edge Cases** - Test boundary conditions and special cases
5. **WebSocket Communication** - Test real-time agent execution

## Running Tests

### Quick Test Run

```bash
# Run all API tests
poetry run pytest tests/test_*_api.py -v

# Run specific test file
poetry run pytest tests/test_portfolios_api.py -v

# Run specific test
poetry run pytest tests/test_portfolios_api.py::TestPortfoliosAPI::test_create_portfolio_success -v
```

### With Coverage

```bash
# Run tests with coverage report
poetry run pytest tests/test_*_api.py --cov=backend --cov-report=html --cov-report=term

# Coverage report will be in htmlcov/index.html
```

### Using Test Script

```bash
# Use provided test script
./scripts/run_api_tests.sh
```

## Test Configuration

### pytest.ini Options (pyproject.toml)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short --asyncio-mode=auto"
markers = [
    "asyncio: mark test as async",
]
```

### Dependencies

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-cov = "^4.1.0"
httpx = "^0.28.1"
pytest-asyncio = "^1.3.0"
```

## Test Coverage

### API Endpoints Covered

#### Portfolio API (`/api/portfolios/`)
- ✅ GET `/` - List portfolios
- ✅ GET `/{name}` - Get portfolio details
- ✅ POST `/` - Create portfolio
- ✅ PUT `/{name}` - Update portfolio
- ✅ DELETE `/{name}` - Delete portfolio

#### Agent API (`/api/agents/`)
- ✅ POST `/{portfolio}/execute` - Execute agent (sync)
- ✅ WebSocket `/ws/{portfolio}` - Execute with real-time updates

#### Trades API (`/api/trades/`)
- ✅ GET `/pending` - Get pending trades
- ✅ POST `/{trade_id}/apply` - Apply trade
- ✅ DELETE `/{trade_id}` - Cancel trade

#### Analytics API (`/api/analytics/`)
- ✅ GET `/execution-logs` - Get execution history
- ✅ GET `/dashboard` - Get dashboard data

#### System API (`/api/system/`)
- ✅ GET `/health` - System health check
- ✅ GET `/scheduler` - Scheduler status
- ✅ POST `/scheduler/start` - Start scheduler
- ✅ POST `/scheduler/stop` - Stop scheduler

### Scenarios Tested

For each endpoint:
- ✅ Successful requests with valid data
- ✅ Invalid/missing data validation
- ✅ Not found (404) responses
- ✅ Server error (500) handling
- ✅ HTTP method validation
- ✅ Response format verification
- ✅ CORS headers (where applicable)

## Mocking Strategy

### Service Layer Mocking
- Portfolio operations mocked at service layer
- Agent execution mocked with realistic responses
- Database/external service calls mocked
- WebSocket connections tested with mock callbacks

### Fixtures Used
- `client` - FastAPI TestClient instance
- `mock_portfolio_service` - Mocked portfolio operations
- `mock_agent_service` - Mocked agent execution
- `mock_execution_log_service` - Mocked analytics data
- `sample_*_api` fixtures - Test data samples

## Best Practices

### Writing Tests
1. **Test names** should clearly describe what's being tested
2. **Arrange-Act-Assert** pattern for test structure  
3. **Mock external dependencies** at service layer
4. **Test both success and failure** scenarios
5. **Validate response format** and status codes

### Test Data
- Use fixtures for reusable test data
- Create realistic but minimal test scenarios
- Test edge cases and boundary conditions
- Use descriptive test data that aids debugging

### Async Testing
```python
@pytest.mark.asyncio
async def test_async_endpoint(client, mock_service):
    mock_service.async_method.return_value = expected_result
    
    response = client.post("/api/endpoint", json=data)
    
    assert response.status_code == 200
```

### WebSocket Testing
```python
def test_websocket(client, mock_service):
    with client.websocket_connect("/ws/endpoint") as websocket:
        websocket.send_text(json.dumps(request_data))
        response = websocket.receive_text()
        data = json.loads(response)
        assert data["type"] == "result"
```

## Continuous Integration

Tests are configured to run in CI environments with:
- Automated test execution on pull requests
- Coverage reporting and enforcement
- Failure notifications and detailed logs

## Troubleshooting

### Common Issues

**Import Errors**
- Ensure backend modules are in Python path
- Check that all dependencies are installed

**WebSocket Test Failures**  
- Verify WebSocket connection handling
- Check async/await patterns in test code

**Mock Setup Issues**
- Verify service mocking at correct layer
- Check that mock return values match expected types

### Debug Mode
```bash
# Run with more verbose output
poetry run pytest tests/ -v -s --tb=long

# Run with PDB debugging
poetry run pytest tests/ --pdb
```