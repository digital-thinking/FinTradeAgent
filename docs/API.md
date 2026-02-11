# FinTradeAgent API Documentation

## Overview

FinTradeAgent provides a comprehensive REST API with WebSocket support for real-time updates. The API is built with FastAPI and includes automatic OpenAPI/Swagger documentation.

**Base URL**: `http://localhost:8000/api`  
**Documentation**: `http://localhost:8000/docs`  
**Redoc**: `http://localhost:8000/redoc`

## Authentication

Currently, the API operates without authentication in development mode. Future versions will implement JWT-based authentication.

## Common Response Formats

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "field": ["Field is required"]
    }
  }
}
```

### Pagination Response
```json
{
  "success": true,
  "data": {
    "items": [...],
    "total": 150,
    "page": 1,
    "size": 20,
    "pages": 8
  }
}
```

## Portfolio Management

### List All Portfolios

**Endpoint**: `GET /api/portfolios/`

**Description**: Retrieve a list of all portfolios with summary information.

**Parameters**: None

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "name": "Take-Private Arbitrage",
      "strategy_prompt": "You are a merger arbitrage specialist...",
      "initial_amount": 10000.0,
      "current_cash": 8500.0,
      "total_value": 11250.0,
      "performance": {
        "total_return": 1250.0,
        "total_return_pct": 12.5,
        "annualized_return": 18.2
      },
      "num_initial_trades": 3,
      "trades_per_run": 3,
      "run_frequency": "daily",
      "llm_provider": "openai",
      "llm_model": "gpt-4o",
      "last_execution": "2026-02-11T10:30:00Z",
      "is_active": true,
      "created_at": "2026-01-15T09:00:00Z"
    }
  ]
}
```

### Get Portfolio Details

**Endpoint**: `GET /api/portfolios/{name}`

**Description**: Get detailed information about a specific portfolio.

**Parameters**:
- `name` (path): Portfolio name

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "Take-Private Arbitrage",
    "strategy_prompt": "You are a merger arbitrage specialist focused on announced take-private deals...",
    "initial_amount": 10000.0,
    "current_cash": 8500.0,
    "total_value": 11250.0,
    "holdings": [
      {
        "ticker": "ADBE",
        "shares": 15,
        "avg_price": 485.20,
        "current_price": 492.50,
        "total_value": 7387.50,
        "unrealized_pnl": 109.50,
        "unrealized_pnl_pct": 1.5
      }
    ],
    "performance": {
      "total_return": 1250.0,
      "total_return_pct": 12.5,
      "annualized_return": 18.2,
      "max_drawdown": -3.2,
      "sharpe_ratio": 1.45,
      "win_rate": 65.0
    },
    "recent_trades": [
      {
        "id": "trade_123",
        "ticker": "MSFT",
        "action": "BUY",
        "shares": 20,
        "price": 310.50,
        "reasoning": "Strong earnings beat with positive guidance...",
        "timestamp": "2026-02-10T14:30:00Z",
        "status": "executed"
      }
    ],
    "num_initial_trades": 3,
    "trades_per_run": 3,
    "run_frequency": "daily",
    "llm_provider": "openai",
    "llm_model": "gpt-4o",
    "created_at": "2026-01-15T09:00:00Z",
    "updated_at": "2026-02-11T10:30:00Z"
  }
}
```

### Create Portfolio

**Endpoint**: `POST /api/portfolios/`

**Description**: Create a new portfolio with AI trading strategy.

**Request Body**:
```json
{
  "name": "Earnings Momentum",
  "strategy_prompt": "You are an earnings momentum specialist. Focus on companies that beat both EPS and revenue estimates while raising guidance...",
  "initial_amount": 15000.0,
  "num_initial_trades": 5,
  "trades_per_run": 3,
  "run_frequency": "weekly",
  "llm_provider": "anthropic",
  "llm_model": "claude-3-opus"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "Earnings Momentum",
    "strategy_prompt": "You are an earnings momentum specialist...",
    "initial_amount": 15000.0,
    "current_cash": 15000.0,
    "total_value": 15000.0,
    "num_initial_trades": 5,
    "trades_per_run": 3,
    "run_frequency": "weekly",
    "llm_provider": "anthropic",
    "llm_model": "claude-3-opus",
    "is_active": true,
    "created_at": "2026-02-11T12:00:00Z"
  },
  "message": "Portfolio created successfully"
}
```

### Update Portfolio

**Endpoint**: `PUT /api/portfolios/{name}`

**Description**: Update an existing portfolio configuration.

**Parameters**:
- `name` (path): Portfolio name

**Request Body**:
```json
{
  "strategy_prompt": "Updated strategy prompt with new focus areas...",
  "trades_per_run": 5,
  "run_frequency": "daily",
  "llm_model": "gpt-4o-2024-05-13"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "Earnings Momentum",
    "strategy_prompt": "Updated strategy prompt with new focus areas...",
    "trades_per_run": 5,
    "run_frequency": "daily",
    "llm_model": "gpt-4o-2024-05-13",
    "updated_at": "2026-02-11T12:15:00Z"
  },
  "message": "Portfolio updated successfully"
}
```

### Delete Portfolio

**Endpoint**: `DELETE /api/portfolios/{name}`

**Description**: Delete a portfolio (soft delete - marks as inactive).

**Parameters**:
- `name` (path): Portfolio name

**Response**:
```json
{
  "success": true,
  "message": "Portfolio deleted successfully"
}
```

## Agent Execution

### Execute Agent

**Endpoint**: `POST /api/agents/{name}/execute`

**Description**: Execute the AI agent for a specific portfolio. This triggers the complete analysis and recommendation generation process.

**Parameters**:
- `name` (path): Portfolio name

**Request Body** (optional):
```json
{
  "user_guidance": "Focus on tech stocks today, avoid energy sector",
  "max_trades": 3,
  "risk_level": "moderate"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "execution_id": "exec_456789",
    "portfolio_name": "Take-Private Arbitrage",
    "status": "completed",
    "started_at": "2026-02-11T14:00:00Z",
    "completed_at": "2026-02-11T14:02:30Z",
    "execution_time_seconds": 150,
    "summary": "Market analysis shows 3 potential merger arbitrage opportunities with attractive spreads...",
    "recommendations": [
      {
        "ticker": "VMW",
        "action": "BUY",
        "shares": 25,
        "estimated_price": 142.50,
        "stop_loss_price": 135.00,
        "take_profit_price": 150.00,
        "confidence": 0.85,
        "reasoning": "Broadcom acquisition of VMware shows 15% spread to deal price with high completion probability based on regulatory progress and management statements...",
        "research_data": {
          "current_price": 142.50,
          "deal_price": 164.00,
          "spread_pct": 15.1,
          "volume_vs_avg": 1.45,
          "news_sentiment": "positive",
          "analyst_ratings": "majority_buy"
        }
      }
    ],
    "market_analysis": {
      "sp500_change": 0.75,
      "vix_level": 18.2,
      "sector_performance": {
        "technology": 1.2,
        "healthcare": 0.8,
        "financials": -0.3
      }
    },
    "cost_analysis": {
      "tokens_used": 8750,
      "estimated_cost_usd": 0.85,
      "provider": "openai"
    }
  }
}
```

### Get Execution History

**Endpoint**: `GET /api/agents/{name}/executions`

**Description**: Get execution history for a portfolio.

**Parameters**:
- `name` (path): Portfolio name
- `limit` (query): Number of executions to return (default: 20)
- `offset` (query): Offset for pagination (default: 0)

**Response**:
```json
{
  "success": true,
  "data": {
    "executions": [
      {
        "execution_id": "exec_456789",
        "started_at": "2026-02-11T14:00:00Z",
        "completed_at": "2026-02-11T14:02:30Z",
        "status": "completed",
        "recommendations_count": 3,
        "accepted_trades": 2,
        "execution_time_seconds": 150,
        "cost_usd": 0.85
      }
    ],
    "total": 45,
    "page": 1,
    "size": 20
  }
}
```

## WebSocket Real-time Updates

### Agent Execution WebSocket

**Endpoint**: `WS /api/agents/{name}/ws`

**Description**: Connect to receive real-time updates during agent execution.

**Connection**: Connect using WebSocket client to `ws://localhost:8000/api/agents/{name}/ws`

**Message Types**:

#### Execution Started
```json
{
  "type": "execution_started",
  "data": {
    "execution_id": "exec_456789",
    "portfolio_name": "Take-Private Arbitrage",
    "started_at": "2026-02-11T14:00:00Z"
  }
}
```

#### Data Collection Progress
```json
{
  "type": "data_collection",
  "data": {
    "execution_id": "exec_456789",
    "stage": "collecting_market_data",
    "progress": 45,
    "message": "Fetching current stock prices..."
  }
}
```

#### LLM Processing
```json
{
  "type": "llm_processing",
  "data": {
    "execution_id": "exec_456789",
    "stage": "generating_recommendations",
    "tokens_used": 5200,
    "estimated_cost": 0.52
  }
}
```

#### Execution Completed
```json
{
  "type": "execution_completed",
  "data": {
    "execution_id": "exec_456789",
    "status": "completed",
    "recommendations_count": 3,
    "execution_time_seconds": 150,
    "completed_at": "2026-02-11T14:02:30Z"
  }
}
```

#### Error
```json
{
  "type": "error",
  "data": {
    "execution_id": "exec_456789",
    "error_code": "LLM_TIMEOUT",
    "message": "LLM request timed out after 30 seconds",
    "timestamp": "2026-02-11T14:01:00Z"
  }
}
```

## Trade Management

### Get Pending Trades

**Endpoint**: `GET /api/trades/pending`

**Description**: Get all pending trade recommendations awaiting user approval.

**Parameters**:
- `portfolio_name` (query, optional): Filter by portfolio name
- `limit` (query): Number of trades to return (default: 50)
- `offset` (query): Offset for pagination (default: 0)

**Response**:
```json
{
  "success": true,
  "data": {
    "trades": [
      {
        "trade_id": "trade_789",
        "portfolio_name": "Take-Private Arbitrage",
        "execution_id": "exec_456789",
        "ticker": "VMW",
        "action": "BUY",
        "shares": 25,
        "estimated_price": 142.50,
        "stop_loss_price": 135.00,
        "take_profit_price": 150.00,
        "confidence": 0.85,
        "reasoning": "Broadcom acquisition of VMware shows 15% spread...",
        "current_price": 142.75,
        "market_cap": "58.5B",
        "volume": 2450000,
        "research_data": {
          "news_sentiment": "positive",
          "analyst_ratings": "majority_buy",
          "recent_filings": [
            {
              "type": "8-K",
              "date": "2026-02-10",
              "title": "Regulatory approval update"
            }
          ]
        },
        "created_at": "2026-02-11T14:02:30Z",
        "expires_at": "2026-02-11T17:00:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "size": 50
  }
}
```

### Apply Trade

**Endpoint**: `POST /api/trades/{trade_id}/apply`

**Description**: Execute a pending trade recommendation.

**Parameters**:
- `trade_id` (path): Trade identifier

**Request Body** (optional):
```json
{
  "shares": 20,
  "price_limit": 143.00,
  "notes": "Reducing position size due to market volatility"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "trade_id": "trade_789",
    "execution_id": "trade_exec_101",
    "status": "executed",
    "ticker": "VMW",
    "action": "BUY",
    "shares": 20,
    "executed_price": 142.85,
    "total_cost": 2857.00,
    "fees": 1.00,
    "net_cost": 2858.00,
    "executed_at": "2026-02-11T14:15:30Z",
    "portfolio_impact": {
      "new_cash_balance": 5642.00,
      "new_total_value": 11387.50,
      "position_summary": {
        "ticker": "VMW",
        "total_shares": 20,
        "avg_price": 142.85,
        "total_value": 2857.00
      }
    }
  },
  "message": "Trade executed successfully"
}
```

### Cancel Trade

**Endpoint**: `DELETE /api/trades/{trade_id}`

**Description**: Cancel a pending trade recommendation.

**Parameters**:
- `trade_id` (path): Trade identifier

**Request Body** (optional):
```json
{
  "reason": "Market conditions changed"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Trade cancelled successfully"
}
```

### Get Trade History

**Endpoint**: `GET /api/trades/history`

**Description**: Get historical trade data.

**Parameters**:
- `portfolio_name` (query, optional): Filter by portfolio name
- `ticker` (query, optional): Filter by ticker symbol
- `action` (query, optional): Filter by action (BUY/SELL)
- `start_date` (query, optional): Start date (ISO format)
- `end_date` (query, optional): End date (ISO format)
- `limit` (query): Number of trades to return (default: 100)
- `offset` (query): Offset for pagination (default: 0)

**Response**:
```json
{
  "success": true,
  "data": {
    "trades": [
      {
        "trade_id": "trade_789",
        "portfolio_name": "Take-Private Arbitrage",
        "ticker": "VMW",
        "action": "BUY",
        "shares": 20,
        "executed_price": 142.85,
        "total_cost": 2858.00,
        "executed_at": "2026-02-11T14:15:30Z",
        "status": "executed"
      }
    ],
    "summary": {
      "total_trades": 156,
      "total_volume": 2450000.00,
      "avg_trade_size": 15705.13,
      "win_rate": 68.2
    },
    "total": 156,
    "page": 1,
    "size": 100
  }
}
```

## Analytics & Dashboard

### Get Dashboard Data

**Endpoint**: `GET /api/analytics/dashboard`

**Description**: Get comprehensive dashboard data including portfolio performance, system metrics, and market overview.

**Response**:
```json
{
  "success": true,
  "data": {
    "portfolio_summary": {
      "total_portfolios": 5,
      "total_aum": 75250.00,
      "total_return": 8750.00,
      "total_return_pct": 13.2,
      "best_performer": {
        "name": "Take-Private Arbitrage",
        "return_pct": 18.5
      },
      "worst_performer": {
        "name": "Tech Momentum",
        "return_pct": 2.1
      }
    },
    "recent_activity": {
      "last_execution": "2026-02-11T14:15:30Z",
      "executions_today": 3,
      "pending_trades": 7,
      "trades_executed_today": 5
    },
    "performance_chart": {
      "dates": ["2026-01-01", "2026-01-02", "..."],
      "values": [66500.00, 66750.00, "..."],
      "returns": [0.0, 0.38, "..."]
    },
    "top_holdings": [
      {
        "ticker": "AAPL",
        "total_shares": 45,
        "total_value": 8550.00,
        "weight_pct": 11.4,
        "unrealized_pnl": 450.00
      }
    ],
    "system_health": {
      "api_status": "healthy",
      "database_status": "healthy",
      "cache_status": "healthy",
      "avg_response_time_ms": 125,
      "error_rate_pct": 0.1
    }
  }
}
```

### Get Execution Logs

**Endpoint**: `GET /api/analytics/execution-logs`

**Description**: Get detailed execution logs for debugging and analysis.

**Parameters**:
- `portfolio_name` (query, optional): Filter by portfolio name
- `start_date` (query, optional): Start date (ISO format)
- `end_date` (query, optional): End date (ISO format)
- `status` (query, optional): Filter by status (completed, failed, timeout)
- `limit` (query): Number of logs to return (default: 50)
- `offset` (query): Offset for pagination (default: 0)

**Response**:
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "execution_id": "exec_456789",
        "portfolio_name": "Take-Private Arbitrage",
        "status": "completed",
        "started_at": "2026-02-11T14:00:00Z",
        "completed_at": "2026-02-11T14:02:30Z",
        "execution_time_seconds": 150,
        "llm_provider": "openai",
        "llm_model": "gpt-4o",
        "tokens_used": 8750,
        "cost_usd": 0.85,
        "recommendations_generated": 3,
        "recommendations_accepted": 2,
        "error_message": null,
        "user_guidance": "Focus on tech stocks today",
        "market_conditions": {
          "sp500_change": 0.75,
          "vix_level": 18.2
        }
      }
    ],
    "summary": {
      "total_executions": 245,
      "success_rate": 94.3,
      "avg_execution_time": 142,
      "total_cost": 125.40
    },
    "total": 245,
    "page": 1,
    "size": 50
  }
}
```

### Get Performance Metrics

**Endpoint**: `GET /api/analytics/performance`

**Description**: Get detailed performance analytics for portfolios.

**Parameters**:
- `portfolio_name` (query, optional): Filter by specific portfolio
- `period` (query): Time period (1d, 7d, 30d, 90d, 1y, all) (default: 30d)
- `benchmark` (query, optional): Benchmark symbol for comparison (default: SPY)

**Response**:
```json
{
  "success": true,
  "data": {
    "period": "30d",
    "portfolio_performance": {
      "total_return": 1250.00,
      "total_return_pct": 12.5,
      "annualized_return": 18.2,
      "max_drawdown": -3.2,
      "max_drawdown_date": "2026-01-25",
      "sharpe_ratio": 1.45,
      "sortino_ratio": 1.82,
      "calmar_ratio": 5.69,
      "win_rate": 65.0,
      "avg_win": 2.8,
      "avg_loss": -1.9,
      "profit_factor": 1.95
    },
    "benchmark_comparison": {
      "benchmark_return": 5.2,
      "alpha": 7.3,
      "beta": 0.85,
      "correlation": 0.72,
      "tracking_error": 4.1,
      "information_ratio": 1.78
    },
    "daily_returns": [
      {"date": "2026-01-15", "portfolio": 0.5, "benchmark": 0.3},
      {"date": "2026-01-16", "portfolio": -0.2, "benchmark": 0.1}
    ],
    "drawdown_periods": [
      {
        "start_date": "2026-01-20",
        "end_date": "2026-01-25",
        "max_drawdown": -3.2,
        "duration_days": 5,
        "recovery_date": "2026-01-30"
      }
    ]
  }
}
```

## System Health & Monitoring

### Get System Health

**Endpoint**: `GET /api/system/health`

**Description**: Get comprehensive system health status.

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2026-02-11T14:30:00Z",
    "version": "2.0.0",
    "uptime_seconds": 86400,
    "services": {
      "database": {
        "status": "healthy",
        "response_time_ms": 5,
        "connection_pool": {
          "active": 2,
          "idle": 8,
          "max": 20
        }
      },
      "cache": {
        "status": "healthy",
        "response_time_ms": 2,
        "hit_rate": 85.4,
        "memory_usage_mb": 245
      },
      "llm_providers": {
        "openai": {
          "status": "healthy",
          "last_request": "2026-02-11T14:25:00Z",
          "avg_response_time_ms": 1850,
          "rate_limit_remaining": 4500
        },
        "anthropic": {
          "status": "healthy",
          "last_request": "2026-02-11T13:45:00Z",
          "avg_response_time_ms": 2100,
          "rate_limit_remaining": 850
        }
      },
      "market_data": {
        "status": "healthy",
        "last_update": "2026-02-11T14:28:00Z",
        "sources_available": 3,
        "cache_hit_rate": 92.1
      }
    },
    "performance": {
      "requests_per_minute": 45,
      "avg_response_time_ms": 125,
      "error_rate_pct": 0.1,
      "cpu_usage_pct": 15.2,
      "memory_usage_mb": 512,
      "disk_usage_pct": 23.8
    }
  }
}
```

### Get System Metrics

**Endpoint**: `GET /api/system/metrics`

**Description**: Get detailed system performance metrics.

**Parameters**:
- `period` (query): Time period for metrics (1h, 24h, 7d) (default: 24h)
- `granularity` (query): Data granularity (1m, 5m, 1h) (default: 5m)

**Response**:
```json
{
  "success": true,
  "data": {
    "period": "24h",
    "granularity": "5m",
    "metrics": {
      "response_times": [
        {"timestamp": "2026-02-11T14:00:00Z", "avg_ms": 120, "p95_ms": 250, "p99_ms": 500},
        {"timestamp": "2026-02-11T14:05:00Z", "avg_ms": 118, "p95_ms": 245, "p99_ms": 480}
      ],
      "throughput": [
        {"timestamp": "2026-02-11T14:00:00Z", "requests": 42},
        {"timestamp": "2026-02-11T14:05:00Z", "requests": 38}
      ],
      "error_rates": [
        {"timestamp": "2026-02-11T14:00:00Z", "errors": 0, "rate_pct": 0.0},
        {"timestamp": "2026-02-11T14:05:00Z", "errors": 1, "rate_pct": 2.6}
      ],
      "resource_usage": [
        {"timestamp": "2026-02-11T14:00:00Z", "cpu_pct": 15.2, "memory_mb": 512, "disk_pct": 23.8},
        {"timestamp": "2026-02-11T14:05:00Z", "cpu_pct": 16.1, "memory_mb": 518, "disk_pct": 23.8}
      ]
    }
  }
}
```

## Error Codes

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `PORTFOLIO_NOT_FOUND` | 404 | Portfolio does not exist |
| `TRADE_NOT_FOUND` | 404 | Trade does not exist |
| `EXECUTION_IN_PROGRESS` | 409 | Agent execution already in progress |
| `INSUFFICIENT_CASH` | 400 | Insufficient cash for trade |
| `INVALID_TICKER` | 400 | Invalid ticker symbol |
| `LLM_TIMEOUT` | 408 | LLM request timeout |
| `LLM_ERROR` | 502 | LLM service error |
| `MARKET_DATA_ERROR` | 502 | Market data service error |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `CACHE_ERROR` | 500 | Cache operation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | API rate limit exceeded |

### Example Error Responses

```json
{
  "success": false,
  "error": {
    "code": "PORTFOLIO_NOT_FOUND",
    "message": "Portfolio 'Non-Existent' not found",
    "details": {
      "portfolio_name": "Non-Existent"
    }
  }
}
```

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "initial_amount": ["Must be greater than 0"],
      "llm_model": ["Invalid model name"]
    }
  }
}
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **General API**: 1000 requests per hour per client
- **Agent Execution**: 10 executions per hour per portfolio
- **WebSocket Connections**: 50 concurrent connections per client

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when the rate limit resets

## SDK and Client Libraries

### Python Client Example

```python
import asyncio
import aiohttp
import json

class FinTradeClient:
    def __init__(self, base_url="http://localhost:8000/api"):
        self.base_url = base_url

    async def list_portfolios(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/portfolios/") as resp:
                return await resp.json()

    async def execute_agent(self, portfolio_name, guidance=None):
        data = {"user_guidance": guidance} if guidance else {}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/agents/{portfolio_name}/execute",
                json=data
            ) as resp:
                return await resp.json()

# Usage
client = FinTradeClient()
portfolios = await client.list_portfolios()
execution = await client.execute_agent("Take-Private Arbitrage", "Focus on tech sector")
```

### JavaScript/TypeScript Client Example

```typescript
class FinTradeClient {
  constructor(private baseUrl = 'http://localhost:8000/api') {}

  async listPortfolios() {
    const response = await fetch(`${this.baseUrl}/portfolios/`)
    return response.json()
  }

  async executeAgent(portfolioName: string, guidance?: string) {
    const response = await fetch(`${this.baseUrl}/agents/${portfolioName}/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_guidance: guidance }),
    })
    return response.json()
  }

  connectWebSocket(portfolioName: string, callbacks: {
    onMessage?: (data: any) => void
    onError?: (error: Event) => void
  }) {
    const ws = new WebSocket(`ws://localhost:8000/api/agents/${portfolioName}/ws`)
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      callbacks.onMessage?.(data)
    }
    
    ws.onerror = callbacks.onError
    return ws
  }
}

// Usage
const client = new FinTradeClient()
const portfolios = await client.listPortfolios()
const execution = await client.executeAgent('Take-Private Arbitrage', 'Focus on tech sector')

const ws = client.connectWebSocket('Take-Private Arbitrage', {
  onMessage: (data) => console.log('Received:', data),
  onError: (error) => console.error('WebSocket error:', error)
})
```

This comprehensive API documentation provides all the information needed to integrate with the FinTradeAgent platform. For interactive testing and additional examples, visit the automatic Swagger documentation at `/docs` when running the backend server.