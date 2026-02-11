# FinTradeAgent Database Schema Documentation

## Overview

FinTradeAgent uses a hybrid data storage approach that combines SQLite databases for operational data with file-based storage for configuration. This design provides flexibility for development while maintaining the option to migrate to a full database solution for production deployments.

## Storage Architecture

### Current Hybrid Approach

```
Data Layer Architecture:
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│                     │    │                     │    │                     │
│   SQLite Databases  │    │   YAML/JSON Files   │    │   Cache Layer       │
│                     │    │                     │    │                     │
│  - Execution logs   │    │  - Portfolio config │    │  - Market data      │
│  - Trade history    │    │  - Portfolio state  │    │  - Price cache      │
│  - Performance      │    │  - Holdings data    │    │  - Session data     │
│  - System metrics   │    │                     │    │                     │
│                     │    │                     │    │                     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
        SQLAlchemy              File I/O                    Redis
```

### File Storage Locations

```
data/
├── portfolios/              # Portfolio configurations (YAML)
├── state/                   # Portfolio state and holdings (JSON)
│   ├── execution_logs.db    # SQLite database for logs
│   └── {portfolio}_state.json
├── logs/                    # Execution logs (Markdown)
├── market_data/             # Cached market data
└── stock_data/              # Cached stock price data
```

## Database Tables (SQLite)

### Execution Logs Database

**File**: `data/state/execution_logs.db`

#### Table: execution_logs

Stores detailed information about agent execution runs.

```sql
CREATE TABLE execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id VARCHAR(50) UNIQUE NOT NULL,
    portfolio_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,          -- 'running', 'completed', 'failed', 'timeout'
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NULL,
    execution_time_seconds INTEGER NULL,
    llm_provider VARCHAR(20) NOT NULL,    -- 'openai', 'anthropic', 'ollama'
    llm_model VARCHAR(50) NOT NULL,
    tokens_used INTEGER NULL,
    cost_usd DECIMAL(10,4) NULL,
    user_guidance TEXT NULL,
    recommendations_generated INTEGER DEFAULT 0,
    recommendations_accepted INTEGER DEFAULT 0,
    error_message TEXT NULL,
    raw_llm_response TEXT NULL,
    market_conditions JSON NULL,         -- JSON blob with market data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_execution_logs_portfolio ON execution_logs(portfolio_name);
CREATE INDEX idx_execution_logs_status ON execution_logs(status);
CREATE INDEX idx_execution_logs_started_at ON execution_logs(started_at);
CREATE INDEX idx_execution_logs_execution_id ON execution_logs(execution_id);
```

#### Table: trade_history

Stores all executed trades with detailed information.

```sql
CREATE TABLE trade_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id VARCHAR(50) UNIQUE NOT NULL,
    execution_id VARCHAR(50) NOT NULL,
    portfolio_name VARCHAR(100) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    action VARCHAR(10) NOT NULL,          -- 'BUY', 'SELL'
    shares DECIMAL(10,4) NOT NULL,
    target_price DECIMAL(10,4) NULL,
    executed_price DECIMAL(10,4) NULL,
    total_cost DECIMAL(15,4) NULL,
    fees DECIMAL(10,4) DEFAULT 0,
    stop_loss_price DECIMAL(10,4) NULL,
    take_profit_price DECIMAL(10,4) NULL,
    confidence_score DECIMAL(3,2) NULL,   -- 0.00 to 1.00
    reasoning TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,          -- 'pending', 'executed', 'cancelled', 'expired'
    created_at TIMESTAMP NOT NULL,
    executed_at TIMESTAMP NULL,
    cancelled_at TIMESTAMP NULL,
    expires_at TIMESTAMP NULL,
    
    FOREIGN KEY (execution_id) REFERENCES execution_logs(execution_id)
);

-- Indexes
CREATE INDEX idx_trades_portfolio ON trade_history(portfolio_name);
CREATE INDEX idx_trades_ticker ON trade_history(ticker);
CREATE INDEX idx_trades_status ON trade_history(status);
CREATE INDEX idx_trades_executed_at ON trade_history(executed_at);
CREATE INDEX idx_trades_execution_id ON trade_history(execution_id);
```

#### Table: portfolio_performance

Stores daily portfolio performance snapshots.

```sql
CREATE TABLE portfolio_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_name VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    total_value DECIMAL(15,4) NOT NULL,
    cash_balance DECIMAL(15,4) NOT NULL,
    holdings_value DECIMAL(15,4) NOT NULL,
    daily_return_pct DECIMAL(8,4) NULL,
    cumulative_return_pct DECIMAL(8,4) NULL,
    benchmark_return_pct DECIMAL(8,4) NULL,     -- S&P 500 return for comparison
    alpha DECIMAL(8,4) NULL,
    beta DECIMAL(6,4) NULL,
    sharpe_ratio DECIMAL(6,4) NULL,
    max_drawdown_pct DECIMAL(8,4) NULL,
    volatility_pct DECIMAL(8,4) NULL,
    trade_count INTEGER DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(portfolio_name, date)
);

-- Indexes
CREATE INDEX idx_performance_portfolio ON portfolio_performance(portfolio_name);
CREATE INDEX idx_performance_date ON portfolio_performance(date);
CREATE INDEX idx_performance_portfolio_date ON portfolio_performance(portfolio_name, date);
```

#### Table: system_metrics

Stores system performance and health metrics.

```sql
CREATE TABLE system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    metric_type VARCHAR(50) NOT NULL,     -- 'api_response_time', 'database_query_time', etc.
    metric_name VARCHAR(100) NOT NULL,    -- Specific metric identifier
    value DECIMAL(12,4) NOT NULL,
    unit VARCHAR(20) NULL,                -- 'ms', 'pct', 'count', etc.
    tags JSON NULL,                       -- Additional context as JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_metrics_timestamp ON system_metrics(timestamp);
CREATE INDEX idx_metrics_type ON system_metrics(metric_type);
CREATE INDEX idx_metrics_name ON system_metrics(metric_name);
```

## File-Based Schema

### Portfolio Configuration (YAML)

**Location**: `data/portfolios/{portfolio_name}.yaml`

```yaml
# Portfolio configuration schema
name: string                 # Portfolio display name
asset_class: string         # 'stocks', 'crypto', 'mixed'
strategy_prompt: string     # Complete AI agent strategy prompt
initial_amount: float       # Starting capital
num_initial_trades: int     # Number of trades for initial portfolio setup
trades_per_run: int         # Maximum trades per execution
run_frequency: string       # 'daily', 'weekly', 'monthly'
llm_provider: string        # 'openai', 'anthropic', 'ollama'
llm_model: string          # Specific model name
agent_mode: string         # 'simple', 'debate', 'langgraph'
scheduler_enabled: bool    # Whether automated execution is enabled
auto_apply_trades: bool    # Whether trades are auto-executed (false recommended)
risk_level: string         # 'conservative', 'moderate', 'aggressive'
max_position_size: float   # Maximum percentage per position (optional)
stop_loss_default: float  # Default stop loss percentage (optional)
take_profit_default: float # Default take profit percentage (optional)
```

**Example**:
```yaml
name: "Take-Private Arbitrage"
asset_class: "stocks"
strategy_prompt: |
  You are a merger arbitrage specialist focused on announced take-private deals.
  
  RESEARCH FOCUS:
  - Announced acquisition deals with defined terms
  - Regulatory approval progress
  - Deal completion probability
  - Spread analysis and risk assessment
  
  BUY SIGNALS:
  - Deal announced with attractive spread (>10%)
  - High completion probability
  - Regulatory progress positive
  - Management/board support confirmed
  
  SELL SIGNALS:
  - Deal spread compresses below 5%
  - Regulatory challenges emerge
  - Deal completion risk increases
  - Take profit at 95% of deal price

initial_amount: 10000.0
num_initial_trades: 3
trades_per_run: 3
run_frequency: "daily"
llm_provider: "openai"
llm_model: "gpt-4o"
agent_mode: "langgraph"
scheduler_enabled: false
auto_apply_trades: false
risk_level: "moderate"
max_position_size: 0.2
stop_loss_default: 0.15
take_profit_default: 0.25
```

### Portfolio State (JSON)

**Location**: `data/state/{portfolio_name}_state.json`

```json
{
  "portfolio_name": "string",
  "cash": "float",
  "initial_amount": "float", 
  "total_value": "float",
  "last_updated": "ISO timestamp",
  "holdings": [
    {
      "ticker": "string",
      "shares": "float",
      "avg_cost": "float",
      "total_cost": "float",
      "current_price": "float",
      "current_value": "float",
      "unrealized_pnl": "float",
      "unrealized_pnl_pct": "float",
      "first_purchased": "ISO timestamp",
      "last_updated": "ISO timestamp"
    }
  ],
  "pending_trades": [
    {
      "trade_id": "string",
      "ticker": "string",
      "action": "string",
      "shares": "float",
      "target_price": "float",
      "stop_loss_price": "float",
      "take_profit_price": "float",
      "reasoning": "string",
      "confidence": "float",
      "created_at": "ISO timestamp",
      "expires_at": "ISO timestamp"
    }
  ],
  "performance_metrics": {
    "total_return": "float",
    "total_return_pct": "float",
    "annualized_return": "float",
    "max_drawdown": "float",
    "sharpe_ratio": "float",
    "win_rate": "float",
    "total_trades": "int",
    "winning_trades": "int"
  }
}
```

**Example**:
```json
{
  "portfolio_name": "Take-Private Arbitrage",
  "cash": 8500.00,
  "initial_amount": 10000.00,
  "total_value": 11250.00,
  "last_updated": "2026-02-11T14:30:00Z",
  "holdings": [
    {
      "ticker": "VMW",
      "shares": 25.0,
      "avg_cost": 142.50,
      "total_cost": 3562.50,
      "current_price": 145.25,
      "current_value": 3631.25,
      "unrealized_pnl": 68.75,
      "unrealized_pnl_pct": 1.93,
      "first_purchased": "2026-02-10T10:30:00Z",
      "last_updated": "2026-02-11T14:30:00Z"
    }
  ],
  "pending_trades": [
    {
      "trade_id": "trade_456",
      "ticker": "ADBE",
      "action": "BUY",
      "shares": 15.0,
      "target_price": 485.00,
      "stop_loss_price": 460.00,
      "take_profit_price": 510.00,
      "reasoning": "Adobe acquisition rumors creating arbitrage opportunity...",
      "confidence": 0.78,
      "created_at": "2026-02-11T14:00:00Z",
      "expires_at": "2026-02-11T17:00:00Z"
    }
  ],
  "performance_metrics": {
    "total_return": 1250.00,
    "total_return_pct": 12.5,
    "annualized_return": 18.2,
    "max_drawdown": -3.2,
    "sharpe_ratio": 1.45,
    "win_rate": 65.0,
    "total_trades": 28,
    "winning_trades": 18
  }
}
```

## Pydantic Models

### Portfolio Models

```python
from typing import Dict, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field

class PortfolioConfig(BaseModel):
    """Portfolio configuration model."""
    name: str = Field(..., min_length=1, max_length=100)
    asset_class: Literal["stocks", "crypto", "mixed"] = "stocks"
    strategy_prompt: str = Field(..., min_length=50)
    initial_amount: float = Field(..., gt=0)
    num_initial_trades: int = Field(3, ge=1, le=10)
    trades_per_run: int = Field(3, ge=1, le=10)
    run_frequency: Literal["daily", "weekly", "monthly"] = "daily"
    llm_provider: Literal["openai", "anthropic", "ollama"] = "openai"
    llm_model: str = Field(..., min_length=1)
    agent_mode: Literal["simple", "debate", "langgraph"] = "simple"
    scheduler_enabled: bool = False
    auto_apply_trades: bool = False
    risk_level: Literal["conservative", "moderate", "aggressive"] = "moderate"
    max_position_size: Optional[float] = Field(None, gt=0, le=1.0)
    stop_loss_default: Optional[float] = Field(None, gt=0, le=0.5)
    take_profit_default: Optional[float] = Field(None, gt=0, le=2.0)

class Holding(BaseModel):
    """Portfolio holding model."""
    ticker: str
    shares: float = Field(..., gt=0)
    avg_cost: float = Field(..., gt=0)
    total_cost: float = Field(..., gt=0)
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None
    first_purchased: datetime
    last_updated: datetime

class PendingTrade(BaseModel):
    """Pending trade recommendation model."""
    trade_id: str
    ticker: str = Field(..., min_length=1, max_length=10)
    action: Literal["BUY", "SELL"]
    shares: float = Field(..., gt=0)
    target_price: Optional[float] = Field(None, gt=0)
    stop_loss_price: Optional[float] = Field(None, gt=0)
    take_profit_price: Optional[float] = Field(None, gt=0)
    reasoning: str = Field(..., min_length=10)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    created_at: datetime
    expires_at: Optional[datetime] = None

class PerformanceMetrics(BaseModel):
    """Portfolio performance metrics model."""
    total_return: float
    total_return_pct: float
    annualized_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    win_rate: Optional[float] = Field(None, ge=0, le=100)
    total_trades: int = Field(0, ge=0)
    winning_trades: int = Field(0, ge=0)

class PortfolioState(BaseModel):
    """Complete portfolio state model."""
    portfolio_name: str
    cash: float = Field(..., ge=0)
    initial_amount: float = Field(..., gt=0)
    total_value: float = Field(..., ge=0)
    last_updated: datetime
    holdings: List[Holding] = []
    pending_trades: List[PendingTrade] = []
    performance_metrics: PerformanceMetrics
```

### Execution and Trade Models

```python
class ExecutionLog(BaseModel):
    """Agent execution log model."""
    execution_id: str
    portfolio_name: str
    status: Literal["running", "completed", "failed", "timeout"]
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_seconds: Optional[int] = None
    llm_provider: str
    llm_model: str
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    user_guidance: Optional[str] = None
    recommendations_generated: int = 0
    recommendations_accepted: int = 0
    error_message: Optional[str] = None
    raw_llm_response: Optional[str] = None
    market_conditions: Optional[Dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Trade(BaseModel):
    """Trade history model."""
    trade_id: str
    execution_id: str
    portfolio_name: str
    ticker: str
    action: Literal["BUY", "SELL"]
    shares: float = Field(..., gt=0)
    target_price: Optional[float] = None
    executed_price: Optional[float] = None
    total_cost: Optional[float] = None
    fees: float = 0.0
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    reasoning: str
    status: Literal["pending", "executed", "cancelled", "expired"]
    created_at: datetime
    executed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

class DailyPerformance(BaseModel):
    """Daily portfolio performance snapshot."""
    portfolio_name: str
    date: datetime
    total_value: float
    cash_balance: float
    holdings_value: float
    daily_return_pct: Optional[float] = None
    cumulative_return_pct: Optional[float] = None
    benchmark_return_pct: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    volatility_pct: Optional[float] = None
    trade_count: int = 0
    win_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

## Database Migrations (Future)

### Production Database Schema

For production deployments, the system supports migration to PostgreSQL with the following enhanced schema:

```sql
-- Users and authentication (future feature)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);

-- Portfolios table (replaces YAML files)
CREATE TABLE portfolios (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    asset_class VARCHAR(20) NOT NULL,
    strategy_prompt TEXT NOT NULL,
    initial_amount DECIMAL(15,4) NOT NULL,
    current_cash DECIMAL(15,4) NOT NULL,
    total_value DECIMAL(15,4) NOT NULL,
    num_initial_trades INTEGER DEFAULT 3,
    trades_per_run INTEGER DEFAULT 3,
    run_frequency VARCHAR(20) DEFAULT 'daily',
    llm_provider VARCHAR(20) NOT NULL,
    llm_model VARCHAR(50) NOT NULL,
    agent_mode VARCHAR(20) DEFAULT 'simple',
    scheduler_enabled BOOLEAN DEFAULT FALSE,
    auto_apply_trades BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(20) DEFAULT 'moderate',
    max_position_size DECIMAL(3,2) NULL,
    stop_loss_default DECIMAL(3,2) NULL,
    take_profit_default DECIMAL(3,2) NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, name)
);

-- Holdings table (replaces JSON state)
CREATE TABLE holdings (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER REFERENCES portfolios(id),
    ticker VARCHAR(20) NOT NULL,
    shares DECIMAL(15,8) NOT NULL,
    avg_cost DECIMAL(10,4) NOT NULL,
    total_cost DECIMAL(15,4) NOT NULL,
    first_purchased TIMESTAMP NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(portfolio_id, ticker)
);

-- Enhanced indexes for production
CREATE INDEX idx_portfolios_user_id ON portfolios(user_id);
CREATE INDEX idx_portfolios_active ON portfolios(is_active);
CREATE INDEX idx_holdings_portfolio_id ON holdings(portfolio_id);
CREATE INDEX idx_holdings_ticker ON holdings(ticker);
```

## Data Access Layer

### Service Classes

```python
from sqlalchemy.orm import Session
from typing import List, Optional

class PortfolioService:
    """Portfolio data access service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_portfolio(self, config: PortfolioConfig) -> Portfolio:
        """Create new portfolio."""
        # Implementation here
        pass
    
    async def get_portfolio(self, name: str) -> Optional[Portfolio]:
        """Get portfolio by name."""
        # Implementation here
        pass
    
    async def update_portfolio_value(self, name: str, new_value: float):
        """Update portfolio total value."""
        # Implementation here
        pass

class TradeService:
    """Trade data access service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_trade(self, trade: Trade) -> Trade:
        """Record new trade."""
        # Implementation here
        pass
    
    async def get_pending_trades(self, portfolio_name: str) -> List[Trade]:
        """Get pending trades for portfolio."""
        # Implementation here
        pass
    
    async def execute_trade(self, trade_id: str, execution_price: float) -> Trade:
        """Mark trade as executed."""
        # Implementation here
        pass
```

## Performance Considerations

### Indexing Strategy

1. **Primary Lookups**: Portfolio name, trade ID, execution ID
2. **Time-based Queries**: Created/executed timestamps
3. **Filtering**: Status, ticker, portfolio combinations
4. **Analytics**: Date ranges for performance calculations

### Optimization Techniques

1. **Connection Pooling**: SQLAlchemy connection pool for concurrent access
2. **Query Optimization**: Eager loading for related data
3. **Caching**: Redis for frequently accessed portfolio states
4. **Batch Operations**: Bulk inserts for market data updates
5. **Archiving**: Historical data retention policies

### Cache Strategy

```python
# Cache keys
PORTFOLIO_STATE_KEY = "portfolio:{name}:state"
MARKET_DATA_KEY = "market:{ticker}:data"
PERFORMANCE_KEY = "portfolio:{name}:performance:{period}"

# TTL settings
PORTFOLIO_TTL = 300      # 5 minutes
MARKET_DATA_TTL = 3600   # 1 hour
PERFORMANCE_TTL = 1800   # 30 minutes
```

## Backup and Recovery

### Backup Strategy

1. **Database Backups**: Automated daily SQLite dumps
2. **File Backups**: Portfolio configs and state files
3. **Log Retention**: Execution logs with configurable retention
4. **Recovery Procedures**: Point-in-time recovery capabilities

### Data Integrity

1. **Foreign Key Constraints**: Referential integrity enforcement
2. **Validation**: Pydantic model validation at API boundaries
3. **Transactions**: ACID compliance for critical operations
4. **Audit Trail**: Complete audit log of all changes

This database schema provides a robust foundation for the FinTradeAgent platform, supporting both the current hybrid file-based approach and future migration to full database solutions for production deployments.