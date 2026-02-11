# FinTradeAgent Developer Guide

## Overview

This comprehensive guide covers everything developers need to know to contribute to, extend, and maintain the FinTradeAgent platform. Whether you're fixing bugs, adding features, or optimizing performance, this guide will help you work effectively with the codebase.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Architecture](#project-architecture)
3. [Contributing Guidelines](#contributing-guidelines)
4. [Development Workflows](#development-workflows)
5. [Testing Strategies](#testing-strategies)
6. [Performance Optimization](#performance-optimization)
7. [Debugging and Troubleshooting](#debugging-and-troubleshooting)
8. [Adding New Features](#adding-new-features)
9. [Code Quality Standards](#code-quality-standards)
10. [Deployment and Release Process](#deployment-and-release-process)

## Development Environment Setup

### Prerequisites

Before starting development, ensure you have:

- **Node.js**: Version 18+ for frontend development
- **Python**: Version 3.10+ for backend development
- **Poetry**: For Python dependency management
- **Git**: For version control
- **Docker**: For containerized development (optional but recommended)
- **Redis**: For caching (development setup)

### Local Development Setup

#### 1. Clone Repository

```bash
git clone https://github.com/yourusername/FinTradeAgent.git
cd FinTradeAgent
```

#### 2. Backend Setup

```bash
# Install Python dependencies
poetry install

# Install development dependencies
poetry install --with dev

# Setup environment variables
cp .env.production .env.local
# Edit .env.local with your API keys and settings

# Run database migrations (if using database)
poetry run alembic upgrade head

# Start backend development server
poetry run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Frontend Setup

```bash
cd frontend

# Install Node.js dependencies
npm install

# Start development server
npm run dev

# Frontend will be available at http://localhost:3000
```

#### 4. Development with Docker

For a consistent development environment:

```bash
# Start full development stack
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop stack
docker-compose -f docker-compose.dev.yml down
```

### IDE Configuration

#### VS Code Setup

Recommended extensions:
- **Python**: Microsoft Python extension
- **Vue Language Features (Volar)**: Vue 3 support
- **Tailwind CSS IntelliSense**: CSS class completion
- **ESLint**: JavaScript/TypeScript linting
- **Prettier**: Code formatting
- **REST Client**: API testing

VS Code settings (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "./backend/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "vue.server.hybridMode": true,
  "tailwindCSS.includeLanguages": {
    "vue": "html"
  }
}
```

#### PyCharm/WebStorm Setup

- Configure Python interpreter to use Poetry virtual environment
- Enable Vue.js plugin for frontend development
- Setup code style to match project conventions
- Configure test runner for pytest

## Project Architecture

### High-Level Structure

```
FinTradeAgent/
├── backend/                 # FastAPI backend
│   ├── config/             # Configuration management
│   ├── middleware/         # Custom middleware
│   ├── models/             # Pydantic models
│   ├── routers/            # API route handlers
│   ├── services/           # Business logic
│   ├── utils/              # Utilities and helpers
│   └── main.py             # FastAPI application entry
├── frontend/               # Vue.js frontend
│   ├── public/             # Static assets
│   ├── src/                # Source code
│   │   ├── components/     # Reusable components
│   │   ├── composables/    # Vue composition functions
│   │   ├── layouts/        # Layout components
│   │   ├── pages/          # Page components
│   │   ├── router/         # Vue Router config
│   │   ├── services/       # API services
│   │   ├── stores/         # Pinia state management
│   │   └── utils/          # Frontend utilities
│   ├── tests/              # Frontend tests
│   └── package.json        # Node.js dependencies
├── docs/                   # Documentation
├── tests/                  # Backend tests
├── data/                   # Data storage
├── scripts/                # Development scripts
└── docker-compose.*.yml    # Docker configurations
```

### Backend Architecture Patterns

#### Service Layer Pattern

```python
# backend/services/portfolio_service.py
from typing import List, Optional
from backend.models.portfolio import Portfolio, PortfolioCreate
from backend.utils.database import get_db_session

class PortfolioService:
    """Business logic for portfolio operations."""
    
    def __init__(self, db_session=None):
        self.db = db_session or get_db_session()
    
    async def create_portfolio(self, portfolio_data: PortfolioCreate) -> Portfolio:
        """Create new portfolio with validation."""
        # Business logic here
        pass
    
    async def get_portfolio(self, name: str) -> Optional[Portfolio]:
        """Retrieve portfolio by name."""
        # Implementation here
        pass
```

#### Repository Pattern

```python
# backend/repositories/portfolio_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional

class PortfolioRepository(ABC):
    """Abstract repository interface."""
    
    @abstractmethod
    async def create(self, portfolio: Portfolio) -> Portfolio:
        pass
    
    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Portfolio]:
        pass
    
    @abstractmethod
    async def list_all(self) -> List[Portfolio]:
        pass

class FilePortfolioRepository(PortfolioRepository):
    """File-based portfolio repository implementation."""
    
    async def create(self, portfolio: Portfolio) -> Portfolio:
        # Save to YAML file
        pass
```

### Frontend Architecture Patterns

#### Composition API Pattern

```javascript
// composables/usePortfolio.js
import { ref, computed, onMounted } from 'vue'
import { portfolioApi } from '@/services/api'

export function usePortfolio(portfolioName) {
  const portfolio = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const totalValue = computed(() => {
    return portfolio.value?.total_value || 0
  })

  async function loadPortfolio() {
    loading.value = true
    error.value = null
    
    try {
      portfolio.value = await portfolioApi.getPortfolio(portfolioName)
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    if (portfolioName) {
      loadPortfolio()
    }
  })

  return {
    portfolio,
    loading,
    error,
    totalValue,
    loadPortfolio
  }
}
```

#### Store Pattern with Pinia

```javascript
// stores/portfolio.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { portfolioApi } from '@/services/api'

export const usePortfolioStore = defineStore('portfolio', () => {
  // State
  const portfolios = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const totalAUM = computed(() => {
    return portfolios.value.reduce((sum, p) => sum + p.total_value, 0)
  })

  const activePortfolios = computed(() => {
    return portfolios.value.filter(p => p.is_active)
  })

  // Actions
  async function fetchPortfolios() {
    loading.value = true
    try {
      portfolios.value = await portfolioApi.getAllPortfolios()
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function createPortfolio(portfolioData) {
    const newPortfolio = await portfolioApi.createPortfolio(portfolioData)
    portfolios.value.push(newPortfolio)
    return newPortfolio
  }

  return {
    portfolios,
    loading,
    error,
    totalAUM,
    activePortfolios,
    fetchPortfolios,
    createPortfolio
  }
})
```

## Contributing Guidelines

### Code of Conduct

We are committed to fostering a welcoming and inclusive community. Please:

- Be respectful and constructive in all interactions
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Use welcoming and inclusive language
- Be collaborative and patient

### Getting Started with Contributions

#### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/yourusername/FinTradeAgent.git
cd FinTradeAgent

# Add upstream remote
git remote add upstream https://github.com/originalowner/FinTradeAgent.git
```

#### 2. Create Feature Branch

```bash
# Create and switch to feature branch
git checkout -b feature/your-feature-name

# Keep branch up to date
git fetch upstream
git rebase upstream/main
```

#### 3. Make Changes

- Follow coding standards and conventions
- Write comprehensive tests for new features
- Update documentation as needed
- Ensure all tests pass

#### 4. Commit Guidelines

Use conventional commit messages:

```
feat: add real-time WebSocket updates to portfolio page
fix: resolve CORS issue in development environment
docs: update API documentation for trade endpoints
test: add integration tests for agent execution
refactor: improve error handling in market data service
perf: optimize database queries for portfolio loading
```

Format:
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **test**: Adding or updating tests
- **refactor**: Code refactoring
- **perf**: Performance improvements
- **style**: Code style changes
- **chore**: Build system or dependency updates

#### 5. Pull Request Process

1. **Create Pull Request**: Use GitHub PR template
2. **Describe Changes**: Provide clear description of what was changed and why
3. **Link Issues**: Reference any related GitHub issues
4. **Request Review**: Ask for code review from maintainers
5. **Address Feedback**: Respond to review comments promptly
6. **Merge**: Once approved, maintainer will merge the PR

### Pull Request Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review of code completed
- [ ] Documentation has been updated
- [ ] Tests have been added/updated
- [ ] No new warnings introduced
```

### Issue Reporting

When reporting issues, include:

1. **Environment Information**:
   - OS and version
   - Python/Node.js versions
   - Browser (for frontend issues)
   - Docker version (if using containers)

2. **Steps to Reproduce**:
   - Clear, numbered steps
   - Expected vs actual behavior
   - Screenshots or logs (if applicable)

3. **Context**:
   - Portfolio configurations
   - API keys configuration status
   - Recent changes made

## Development Workflows

### Daily Development Workflow

#### 1. Start Development Session

```bash
# Pull latest changes
git checkout main
git pull upstream main

# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Or start services manually:
# Backend: poetry run uvicorn backend.main:app --reload
# Frontend: cd frontend && npm run dev
```

#### 2. Feature Development

```bash
# Create feature branch
git checkout -b feature/new-agent-mode

# Make changes and commit frequently
git add .
git commit -m "feat: add initial structure for new agent mode"

# Run tests regularly
poetry run pytest  # Backend tests
cd frontend && npm run test  # Frontend tests
```

#### 3. End of Day

```bash
# Push changes to your fork
git push origin feature/new-agent-mode

# Stop development environment
docker-compose -f docker-compose.dev.yml down
```

### Hot Reload and Live Development

#### Backend Hot Reload

FastAPI with `--reload` flag automatically reloads on file changes:

```bash
poetry run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Watch for changes in:
- Python source files (`.py`)
- Configuration files
- Template files

#### Frontend Hot Module Replacement

Vite provides instant hot module replacement:

```bash
cd frontend
npm run dev
```

Features:
- Instant updates for Vue components
- CSS changes without page refresh
- Preserves component state during updates
- Error overlay for debugging

### Database Development

#### Migrations with Alembic

```bash
# Generate migration
poetry run alembic revision --autogenerate -m "Add user authentication tables"

# Apply migration
poetry run alembic upgrade head

# Downgrade migration
poetry run alembic downgrade -1

# View migration history
poetry run alembic history
```

#### Development Database Reset

```bash
# Reset development database
rm data/state/execution_logs.db

# Recreate with migrations
poetry run alembic upgrade head

# Seed with sample data
poetry run python scripts/seed_dev_data.py
```

## Testing Strategies

### Backend Testing

#### Unit Testing with pytest

```python
# tests/test_portfolio_service.py
import pytest
from backend.services.portfolio_service import PortfolioService
from backend.models.portfolio import PortfolioCreate

class TestPortfolioService:
    
    @pytest.fixture
    def portfolio_service(self):
        return PortfolioService()
    
    @pytest.fixture
    def sample_portfolio_data(self):
        return PortfolioCreate(
            name="Test Portfolio",
            initial_amount=10000.0,
            llm_provider="openai",
            llm_model="gpt-4o"
        )
    
    async def test_create_portfolio(self, portfolio_service, sample_portfolio_data):
        """Test portfolio creation."""
        portfolio = await portfolio_service.create_portfolio(sample_portfolio_data)
        
        assert portfolio.name == "Test Portfolio"
        assert portfolio.initial_amount == 10000.0
        assert portfolio.current_cash == 10000.0
    
    async def test_get_nonexistent_portfolio(self, portfolio_service):
        """Test retrieving non-existent portfolio returns None."""
        portfolio = await portfolio_service.get_portfolio("nonexistent")
        assert portfolio is None
```

#### Integration Testing

```python
# tests/integration/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

class TestPortfolioAPI:
    
    def test_create_portfolio_endpoint(self):
        """Test POST /api/portfolios/"""
        portfolio_data = {
            "name": "Integration Test Portfolio",
            "initial_amount": 10000.0,
            "llm_provider": "openai",
            "llm_model": "gpt-4o",
            "strategy_prompt": "Test strategy prompt"
        }
        
        response = client.post("/api/portfolios/", json=portfolio_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] == True
        assert data["data"]["name"] == "Integration Test Portfolio"
    
    def test_get_portfolio_endpoint(self):
        """Test GET /api/portfolios/{name}"""
        response = client.get("/api/portfolios/Integration Test Portfolio")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
```

#### WebSocket Testing

```python
# tests/test_websocket.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

def test_portfolio_websocket():
    """Test portfolio WebSocket connection."""
    client = TestClient(app)
    
    with client.websocket_connect("/api/agents/test-portfolio/ws") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "connection_established"
        assert data["data"]["portfolio_name"] == "test-portfolio"

def test_websocket_execution_updates():
    """Test WebSocket receives execution updates."""
    client = TestClient(app)
    
    with client.websocket_connect("/api/agents/test-portfolio/ws") as websocket:
        # Trigger execution (mock)
        # ... trigger execution logic
        
        # Should receive execution_started message
        message = websocket.receive_json()
        assert message["type"] == "execution_started"
```

#### Test Configuration

```python
# tests/conftest.py
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config.database import Base

# Test database
TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def test_db():
    """Create test database."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)
```

### Frontend Testing

#### Unit Testing with Vitest

```javascript
// tests/unit/components/PortfolioCard.test.js
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PortfolioCard from '@/components/PortfolioCard.vue'

describe('PortfolioCard', () => {
  const mockPortfolio = {
    name: 'Test Portfolio',
    total_value: 15000,
    total_return: 5000,
    total_return_pct: 50.0
  }

  it('renders portfolio information correctly', () => {
    const wrapper = mount(PortfolioCard, {
      props: { portfolio: mockPortfolio }
    })

    expect(wrapper.text()).toContain('Test Portfolio')
    expect(wrapper.text()).toContain('$15,000')
    expect(wrapper.text()).toContain('+$5,000')
    expect(wrapper.text()).toContain('+50.0%')
  })

  it('applies correct CSS classes for positive returns', () => {
    const wrapper = mount(PortfolioCard, {
      props: { portfolio: mockPortfolio }
    })

    const returnElement = wrapper.find('[data-testid="return-amount"]')
    expect(returnElement.classes()).toContain('text-green-500')
  })

  it('emits click event when card is clicked', async () => {
    const wrapper = mount(PortfolioCard, {
      props: { portfolio: mockPortfolio }
    })

    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeTruthy()
  })
})
```

#### Component Testing with Testing Library

```javascript
// tests/unit/components/TradeRecommendation.test.js
import { render, screen, fireEvent } from '@testing-library/vue'
import TradeRecommendation from '@/components/TradeRecommendation.vue'

describe('TradeRecommendation', () => {
  const mockRecommendation = {
    ticker: 'AAPL',
    action: 'BUY',
    shares: 10,
    target_price: 150.00,
    confidence: 0.85,
    reasoning: 'Strong earnings beat with positive guidance'
  }

  it('displays trade recommendation details', () => {
    render(TradeRecommendation, {
      props: { recommendation: mockRecommendation }
    })

    expect(screen.getByText('AAPL')).toBeInTheDocument()
    expect(screen.getByText('BUY')).toBeInTheDocument()
    expect(screen.getByText('10 shares')).toBeInTheDocument()
    expect(screen.getByText('85%')).toBeInTheDocument()
  })

  it('handles apply trade button click', async () => {
    const { emitted } = render(TradeRecommendation, {
      props: { recommendation: mockRecommendation }
    })

    const applyButton = screen.getByRole('button', { name: /apply trade/i })
    await fireEvent.click(applyButton)

    expect(emitted().apply).toBeTruthy()
  })
})
```

#### E2E Testing with Playwright

```javascript
// tests/e2e/portfolio-management.spec.js
import { test, expect } from '@playwright/test'

test.describe('Portfolio Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should create new portfolio', async ({ page }) => {
    // Navigate to portfolio creation
    await page.click('text=Portfolios')
    await page.click('button:has-text("Create Portfolio")')

    // Fill in portfolio form
    await page.fill('[data-testid="portfolio-name"]', 'E2E Test Portfolio')
    await page.fill('[data-testid="initial-amount"]', '10000')
    await page.fill('[data-testid="strategy-prompt"]', 'Test strategy for E2E testing')
    await page.selectOption('[data-testid="llm-provider"]', 'openai')

    // Submit form
    await page.click('button:has-text("Create")')

    // Verify success
    await expect(page.locator('text=Portfolio created successfully')).toBeVisible()
    await expect(page.locator('text=E2E Test Portfolio')).toBeVisible()
  })

  test('should execute agent and show real-time updates', async ({ page }) => {
    // Assume portfolio exists
    await page.goto('/portfolios/test-portfolio')

    // Start execution
    await page.click('button:has-text("Execute Agent")')

    // Wait for execution to start
    await expect(page.locator('[data-testid="execution-progress"]')).toBeVisible()

    // Check for progress updates
    await expect(page.locator('text=Data collection')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=LLM processing')).toBeVisible({ timeout: 30000 })

    // Wait for completion
    await expect(page.locator('text=Execution completed')).toBeVisible({ timeout: 60000 })
  })
})
```

### Test Automation

#### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
    
    - name: Install dependencies
      run: poetry install
    
    - name: Run tests
      run: |
        poetry run pytest --cov=backend --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  frontend-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json
    
    - name: Install dependencies
      run: |
        cd frontend
        npm ci
    
    - name: Run unit tests
      run: |
        cd frontend
        npm run test:run
    
    - name: Run E2E tests
      run: |
        cd frontend
        npm run test:e2e

  integration-tests:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up test environment
      run: |
        docker-compose -f docker-compose.test.yml up -d
        sleep 30  # Wait for services to be ready
    
    - name: Run integration tests
      run: |
        docker-compose -f docker-compose.test.yml exec -T backend poetry run pytest tests/integration/
    
    - name: Cleanup
      run: |
        docker-compose -f docker-compose.test.yml down
```

## Performance Optimization

### Backend Performance

#### Database Optimization

```python
# Efficient query patterns
from sqlalchemy.orm import selectinload, joinedload

# Bad: N+1 query problem
portfolios = db.query(Portfolio).all()
for portfolio in portfolios:
    print(portfolio.holdings)  # Triggers separate query

# Good: Eager loading
portfolios = db.query(Portfolio).options(
    selectinload(Portfolio.holdings)
).all()

# Use indexes for common queries
CREATE INDEX idx_portfolio_name ON portfolios(name);
CREATE INDEX idx_trade_history_portfolio_date ON trade_history(portfolio_name, created_at);
```

#### Caching Strategy

```python
# backend/utils/cache.py
import redis
import json
from typing import Any, Optional
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(ttl: int = 3600):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get cached result
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result, default=str))
            
            return result
        return wrapper
    return decorator

# Usage
@cache_result(ttl=1800)  # Cache for 30 minutes
async def get_market_data(ticker: str):
    # Expensive API call
    return await fetch_from_api(ticker)
```

#### Async Optimization

```python
# Use async for I/O operations
import asyncio
import aiohttp

async def fetch_multiple_tickers(tickers: List[str]) -> Dict[str, dict]:
    """Fetch market data for multiple tickers concurrently."""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_ticker_data(session, ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            ticker: result for ticker, result in zip(tickers, results)
            if not isinstance(result, Exception)
        }

async def fetch_ticker_data(session: aiohttp.ClientSession, ticker: str) -> dict:
    """Fetch data for a single ticker."""
    url = f"https://api.example.com/ticker/{ticker}"
    async with session.get(url) as response:
        return await response.json()
```

#### Memory Management

```python
# Use generators for large datasets
def process_large_trade_history(portfolio_name: str):
    """Process trade history without loading everything into memory."""
    for batch in get_trade_batches(portfolio_name, batch_size=1000):
        yield process_batch(batch)

# Implement pagination for API endpoints
from fastapi import Query

@router.get("/trades/history")
async def get_trade_history(
    portfolio_name: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    offset = (page - 1) * size
    trades = await trade_service.get_trades(
        portfolio_name=portfolio_name,
        offset=offset,
        limit=size
    )
    return trades
```

### Frontend Performance

#### Component Optimization

```javascript
// Use computed properties for expensive calculations
import { computed, ref } from 'vue'

export default {
  setup() {
    const trades = ref([])
    
    // Good: Cached computation
    const tradeStats = computed(() => {
      const totalTrades = trades.value.length
      const winningTrades = trades.value.filter(t => t.pnl > 0).length
      const winRate = totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0
      
      return {
        totalTrades,
        winningTrades,
        winRate: winRate.toFixed(2)
      }
    })
    
    return { trades, tradeStats }
  }
}
```

#### Lazy Loading

```javascript
// Lazy load heavy components
import { defineAsyncComponent } from 'vue'

const PerformanceChart = defineAsyncComponent(() => 
  import('@/components/PerformanceChart.vue')
)

// Route-based lazy loading
const routes = [
  {
    path: '/portfolios/:name',
    component: () => import('@/pages/PortfolioDetail.vue')
  }
]
```

#### Virtual Scrolling for Large Lists

```vue
<!-- Use virtual scrolling for large trade history -->
<template>
  <div class="trade-history">
    <VirtualList
      :data="trades"
      :height="400"
      :item-height="60"
    >
      <template #default="{ item, index }">
        <TradeRow :trade="item" :key="item.id" />
      </template>
    </VirtualList>
  </div>
</template>

<script setup>
import VirtualList from '@/components/VirtualList.vue'
import TradeRow from '@/components/TradeRow.vue'
</script>
```

#### Bundle Optimization

```javascript
// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia'],
          charts: ['chart.js', 'vue-chartjs'],
          utils: ['axios', 'date-fns']
        }
      }
    },
    chunkSizeWarningLimit: 1000
  }
})
```

### Monitoring and Profiling

#### Backend Profiling

```python
# Performance monitoring middleware
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log slow requests
        if process_time > 1.0:
            logger.warning(f"Slow request: {request.url} took {process_time:.2f}s")
        
        return response

# Memory profiling
import tracemalloc
import asyncio

async def profile_memory_usage():
    tracemalloc.start()
    
    # Your code here
    await expensive_operation()
    
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
    print(f"Peak memory usage: {peak / 1024 / 1024:.1f} MB")
    
    tracemalloc.stop()
```

#### Frontend Performance Monitoring

```javascript
// Performance measurement
function measurePerformance(name, fn) {
  return async (...args) => {
    const start = performance.now()
    const result = await fn(...args)
    const end = performance.now()
    
    console.log(`${name} took ${end - start} milliseconds`)
    
    // Send to monitoring service
    if (end - start > 1000) {
      analytics.track('slow_operation', {
        operation: name,
        duration: end - start
      })
    }
    
    return result
  }
}

// Usage
const fetchPortfolioData = measurePerformance('fetchPortfolioData', async (name) => {
  return await api.get(`/portfolios/${name}`)
})
```

## Debugging and Troubleshooting

### Backend Debugging

#### Logging Configuration

```python
# backend/config/logging.py
import logging
from logging.handlers import RotatingFileHandler
import sys

def setup_logging():
    # Create logger
    logger = logging.getLogger("fintrade")
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # File handler
    file_handler = RotatingFileHandler(
        'logs/app.log', 
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Usage in code
logger = logging.getLogger("fintrade")

async def execute_agent(portfolio_name: str):
    logger.info(f"Starting agent execution for {portfolio_name}")
    try:
        result = await agent_service.execute(portfolio_name)
        logger.info(f"Agent execution completed successfully")
        return result
    except Exception as e:
        logger.error(f"Agent execution failed: {str(e)}", exc_info=True)
        raise
```

#### Error Handling Patterns

```python
# Custom exceptions
class FinTradeException(Exception):
    """Base exception for FinTradeAgent."""
    pass

class PortfolioNotFoundError(FinTradeException):
    """Portfolio not found exception."""
    pass

class LLMTimeoutError(FinTradeException):
    """LLM request timeout exception."""
    pass

# Global exception handler
from fastapi import HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(FinTradeException)
async def fintrade_exception_handler(request: Request, exc: FinTradeException):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc)
            }
        }
    )
```

#### Database Debugging

```python
# SQL query logging
import logging

# Enable SQLAlchemy logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
logging.getLogger('sqlalchemy.dialects').setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)

# Query performance monitoring
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    if total > 0.1:  # Log slow queries (>100ms)
        logger.warning(f"Slow query: {total:.2f}s - {statement[:100]}...")
```

### Frontend Debugging

#### Vue DevTools Integration

```javascript
// Enable Vue DevTools in development
if (import.meta.env.DEV) {
  const { createApp } = await import('vue')
  const app = createApp(App)
  
  // Enable Vue DevTools
  app.config.devtools = true
}
```

#### Error Boundary Component

```vue
<!-- ErrorBoundary.vue -->
<template>
  <div v-if="error" class="error-boundary">
    <h2>Something went wrong</h2>
    <details>
      <summary>Error details</summary>
      <pre>{{ error.stack }}</pre>
    </details>
    <button @click="retry">Retry</button>
  </div>
  <slot v-else />
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'

const error = ref(null)

onErrorCaptured((err, instance, info) => {
  error.value = err
  console.error('Error captured by boundary:', err)
  
  // Send error to monitoring service
  analytics.track('component_error', {
    error: err.message,
    stack: err.stack,
    info
  })
  
  return false  // Prevent error from propagating
})

function retry() {
  error.value = null
}
</script>
```

#### Network Request Debugging

```javascript
// Axios interceptor for debugging
import axios from 'axios'

// Request interceptor
axios.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor
axios.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('Response error:', error.response?.status, error.config?.url)
    return Promise.reject(error)
  }
)
```

### Common Issues and Solutions

#### CORS Issues

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### WebSocket Connection Issues

```javascript
// Frontend WebSocket debugging
class DebugWebSocket extends WebSocket {
  constructor(url, protocols) {
    super(url, protocols)
    
    this.addEventListener('open', () => {
      console.log('WebSocket connected:', url)
    })
    
    this.addEventListener('close', (event) => {
      console.log('WebSocket closed:', event.code, event.reason)
    })
    
    this.addEventListener('error', (error) => {
      console.error('WebSocket error:', error)
    })
  }
}

// Use debug WebSocket in development
if (import.meta.env.DEV) {
  window.WebSocket = DebugWebSocket
}
```

#### LLM API Issues

```python
# Retry logic for LLM requests
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def call_llm_with_retry(prompt: str, model: str):
    try:
        response = await llm_client.generate(prompt, model)
        return response
    except TimeoutError:
        logger.warning("LLM request timed out, retrying...")
        raise
    except RateLimitError:
        logger.warning("LLM rate limit hit, waiting...")
        await asyncio.sleep(60)
        raise
```

## Adding New Features

### Feature Development Process

#### 1. Planning Phase

1. **Create GitHub Issue**: Describe the feature with user stories
2. **Design Review**: Discuss architecture and implementation approach
3. **Break Down Tasks**: Create sub-tasks and estimate effort
4. **Create Feature Branch**: `feature/feature-name`

#### 2. Implementation Guidelines

**Backend Feature Addition**:

```python
# 1. Create new router
# backend/routers/new_feature.py
from fastapi import APIRouter, Depends
from backend.services.new_feature_service import NewFeatureService

router = APIRouter()

@router.post("/new-endpoint")
async def create_new_resource(
    data: CreateResourceRequest,
    service: NewFeatureService = Depends()
):
    return await service.create_resource(data)

# 2. Create service layer
# backend/services/new_feature_service.py
class NewFeatureService:
    async def create_resource(self, data: CreateResourceRequest):
        # Implementation here
        pass

# 3. Add models
# backend/models/new_feature.py
from pydantic import BaseModel

class CreateResourceRequest(BaseModel):
    name: str
    description: str

# 4. Register router in main.py
from backend.routers import new_feature
app.include_router(new_feature.router, prefix="/api/new-feature", tags=["new-feature"])
```

**Frontend Feature Addition**:

```javascript
// 1. Create new page component
// frontend/src/pages/NewFeature.vue
<template>
  <div class="new-feature-page">
    <h1>New Feature</h1>
    <!-- Implementation -->
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useNewFeatureStore } from '@/stores/newFeature'

const store = useNewFeatureStore()
// Component logic
</script>

// 2. Add route
// frontend/src/router/index.js
{
  path: '/new-feature',
  name: 'NewFeature',
  component: () => import('@/pages/NewFeature.vue')
}

// 3. Create store
// frontend/src/stores/newFeature.js
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNewFeatureStore = defineStore('newFeature', () => {
  const data = ref([])
  
  async function fetchData() {
    // API calls
  }
  
  return { data, fetchData }
})

// 4. Add to navigation
// frontend/src/layouts/DefaultLayout.vue
<router-link to="/new-feature">New Feature</router-link>
```

#### 3. Testing New Features

```python
# Backend tests
# tests/test_new_feature.py
class TestNewFeature:
    async def test_create_resource(self):
        # Test implementation
        pass

# Integration test
def test_new_feature_api(client):
    response = client.post("/api/new-feature/", json={"name": "test"})
    assert response.status_code == 201
```

```javascript
// Frontend tests
// tests/unit/NewFeature.test.js
import { render, screen } from '@testing-library/vue'
import NewFeature from '@/pages/NewFeature.vue'

describe('NewFeature', () => {
  it('renders correctly', () => {
    render(NewFeature)
    expect(screen.getByText('New Feature')).toBeInTheDocument()
  })
})
```

### Feature Documentation

Create documentation for new features:

```markdown
# New Feature Documentation

## Overview
Brief description of the feature and its purpose.

## Usage
How to use the feature with examples.

## API Reference
Document any new API endpoints.

## Configuration
Any new configuration options.

## Migration Guide
If the feature requires migration steps.
```

## Code Quality Standards

### Python Code Standards

#### Style Guide

Follow PEP 8 with these additions:

```python
# Use type hints for all functions
from typing import List, Optional, Dict, Any

async def get_portfolio(name: str) -> Optional[Portfolio]:
    """Get portfolio by name.
    
    Args:
        name: Portfolio name
        
    Returns:
        Portfolio instance or None if not found
        
    Raises:
        ValidationError: If name is invalid
    """
    pass

# Use dataclasses for simple data structures
from dataclasses import dataclass

@dataclass
class MarketData:
    ticker: str
    price: float
    volume: int
    timestamp: datetime

# Use enums for constants
from enum import Enum

class TradeAction(Enum):
    BUY = "BUY"
    SELL = "SELL"

# Use context managers for resources
async def process_portfolio_data(name: str):
    async with get_db_session() as db:
        portfolio = await get_portfolio(db, name)
        # Process portfolio
```

#### Code Quality Tools

```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py310']

[tool.isort]
profile = "black"
multi_line_output = 3

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pylint]
max-line-length = 88
disable = [
    "missing-docstring",
    "too-few-public-methods",
]
```

### JavaScript/Vue Code Standards

#### Style Guide

```javascript
// Use consistent naming conventions
const portfolioName = 'test-portfolio'  // camelCase for variables
const MARKET_CLOSE_TIME = '16:00'       // UPPER_CASE for constants

// Use destructuring
const { name, totalValue, holdings } = portfolio

// Use template literals
const message = `Portfolio ${name} has total value of $${totalValue}`

// Use async/await over promises
async function fetchPortfolioData(name) {
  try {
    const response = await api.get(`/portfolios/${name}`)
    return response.data
  } catch (error) {
    console.error('Failed to fetch portfolio:', error)
    throw error
  }
}

// Use composition API consistently
import { ref, computed, onMounted } from 'vue'

export default {
  setup() {
    const portfolios = ref([])
    const loading = ref(false)
    
    const totalValue = computed(() => {
      return portfolios.value.reduce((sum, p) => sum + p.total_value, 0)
    })
    
    onMounted(() => {
      loadPortfolios()
    })
    
    return {
      portfolios,
      loading,
      totalValue
    }
  }
}
```

#### ESLint Configuration

```json
// .eslintrc.json
{
  "extends": [
    "@vue/standard",
    "@vue/typescript/recommended"
  ],
  "rules": {
    "no-console": "warn",
    "no-debugger": "error",
    "vue/no-unused-vars": "error",
    "vue/require-default-prop": "off",
    "@typescript-eslint/no-unused-vars": "error"
  }
}
```

### Documentation Standards

#### Code Comments

```python
# Good: Explain WHY, not WHAT
def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float) -> float:
    """Calculate Sharpe ratio for a series of returns.
    
    Uses the standard formula: (mean_return - risk_free_rate) / std_deviation
    Risk-free rate should be in the same frequency as returns (e.g., daily).
    """
    # Convert to numpy for efficient calculation
    returns_array = np.array(returns)
    excess_returns = returns_array - risk_free_rate
    
    return np.mean(excess_returns) / np.std(excess_returns)

# Bad: Explains obvious things
def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float) -> float:
    # Convert returns to numpy array
    returns_array = np.array(returns)
    # Subtract risk free rate from returns
    excess_returns = returns_array - risk_free_rate
    # Return mean divided by standard deviation
    return np.mean(excess_returns) / np.std(excess_returns)
```

#### API Documentation

Use OpenAPI/Swagger annotations:

```python
@router.post("/portfolios/", response_model=PortfolioResponse, status_code=201)
async def create_portfolio(
    portfolio: PortfolioCreate,
    service: PortfolioService = Depends()
) -> PortfolioResponse:
    """Create a new trading portfolio.
    
    Creates a new portfolio with the specified configuration. The portfolio
    will be initialized with the given cash amount and ready for trading.
    
    Args:
        portfolio: Portfolio configuration data
        
    Returns:
        Created portfolio with generated metadata
        
    Raises:
        400: Portfolio name already exists
        422: Invalid portfolio configuration
    """
    return await service.create_portfolio(portfolio)
```

## Deployment and Release Process

### Release Workflow

#### 1. Version Management

Use semantic versioning (MAJOR.MINOR.PATCH):

```bash
# Update version in multiple files
# backend/pyproject.toml
# frontend/package.json
# docker-compose files

# Create version tag
git tag -a v2.1.0 -m "Release v2.1.0: Add real-time WebSocket updates"
git push origin v2.1.0
```

#### 2. Release Process

```bash
# 1. Create release branch
git checkout -b release/v2.1.0

# 2. Update version numbers
# Update CHANGELOG.md
# Update documentation

# 3. Run full test suite
./scripts/run-tests.sh

# 4. Build and test containers
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
# Run integration tests against containers

# 5. Create pull request to main
# 6. After approval, merge and tag
# 7. Deploy to production
```

#### 3. Deployment Scripts

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

echo "Starting deployment process..."

# Pull latest changes
git pull origin main

# Build containers
docker-compose -f docker-compose.production.yml build

# Run database migrations
docker-compose -f docker-compose.production.yml run --rm backend poetry run alembic upgrade head

# Deploy with zero downtime
docker-compose -f docker-compose.production.yml up -d

# Wait for health check
echo "Waiting for services to be ready..."
sleep 30

# Run health check
curl -f http://localhost/api/system/health || exit 1

echo "Deployment completed successfully!"
```

### Continuous Integration

#### GitHub Actions Workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: ./scripts/run-tests.sh

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker images
        run: |
          docker build -t fintrade-frontend ./frontend
          docker build -t fintrade-backend ./backend
      
      - name: Push to registry
        run: |
          docker tag fintrade-frontend ${{ secrets.REGISTRY }}/fintrade-frontend:${GITHUB_REF#refs/tags/}
          docker tag fintrade-backend ${{ secrets.REGISTRY }}/fintrade-backend:${GITHUB_REF#refs/tags/}
          docker push ${{ secrets.REGISTRY }}/fintrade-frontend:${GITHUB_REF#refs/tags/}
          docker push ${{ secrets.REGISTRY }}/fintrade-backend:${GITHUB_REF#refs/tags/}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          # Deployment commands
          ssh ${{ secrets.DEPLOY_HOST }} "cd /app && ./scripts/deploy.sh"
```

This comprehensive developer guide provides all the information needed to effectively contribute to and maintain the FinTradeAgent platform. Regular updates to this guide ensure it remains current with evolving development practices and platform changes.