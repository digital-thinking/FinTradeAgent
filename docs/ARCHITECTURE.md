# FinTradeAgent Architecture Documentation

## Overview

FinTradeAgent is built using a modern, decoupled architecture with Vue.js frontend and FastAPI backend. This document provides detailed information about the system architecture, data flow, and integration patterns.

## System Architecture

### High-Level Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│                     │    │                     │    │                     │
│   Vue.js Frontend   │◄──►│   FastAPI Backend   │◄──►│   External APIs     │
│                     │    │                     │    │                     │
│  - Vue 3 + Vite     │    │  - RESTful API      │    │  - Market Data      │
│  - Tailwind CSS     │    │  - WebSocket        │    │  - LLM Providers    │
│  - Pinia Stores     │    │  - SQLite/Postgres  │    │  - Web Search       │
│  - Chart.js         │    │  - Redis Cache      │    │                     │
│                     │    │                     │    │                     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
       Port: 3000                 Port: 8000
```

### Technology Stack

#### Frontend Stack
- **Framework**: Vue 3 with Composition API
- **Build Tool**: Vite for fast development and optimized builds
- **Styling**: Tailwind CSS for utility-first styling
- **State Management**: Pinia for reactive state management
- **HTTP Client**: Axios for API communications
- **Charts**: Chart.js for data visualization
- **Testing**: Vitest + Playwright for unit and E2E testing
- **TypeScript**: Optional, but recommended for type safety

#### Backend Stack
- **Framework**: FastAPI for high-performance async API
- **Database**: SQLite for development, PostgreSQL for production
- **Caching**: Redis for session and query caching
- **WebSockets**: FastAPI WebSocket support for real-time updates
- **Authentication**: JWT-based authentication (future enhancement)
- **ORM**: SQLAlchemy with Alembic migrations
- **Testing**: pytest with comprehensive test coverage
- **Documentation**: Auto-generated OpenAPI/Swagger docs

#### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Nginx for production deployment
- **Monitoring**: Grafana + Prometheus for metrics collection
- **Deployment**: Production-ready Docker orchestration

## Frontend Architecture

### Component Structure

```
frontend/src/
├── components/           # Reusable UI components
│   ├── common/          # Generic components (Button, Modal, etc.)
│   ├── charts/          # Chart components
│   ├── forms/           # Form components
│   └── tables/          # Table components
├── pages/               # Route-level page components
│   ├── Dashboard.vue    # Main dashboard
│   ├── Portfolio/       # Portfolio management pages
│   ├── Trades/          # Trade management pages
│   └── System/          # System health pages
├── layouts/             # Layout components
│   └── DefaultLayout.vue
├── stores/              # Pinia state management
│   ├── portfolio.js     # Portfolio state
│   ├── trades.js        # Trade state
│   ├── system.js        # System state
│   └── websocket.js     # WebSocket state
├── services/            # API service layer
│   ├── api.js           # Base API configuration
│   ├── portfolio.js     # Portfolio API calls
│   ├── trades.js        # Trade API calls
│   └── websocket.js     # WebSocket service
├── composables/         # Reusable composition functions
│   ├── useApi.js        # API composable
│   ├── useWebSocket.js  # WebSocket composable
│   └── useCharts.js     # Chart composable
├── router/              # Vue Router configuration
│   └── index.js
└── utils/               # Utility functions
    ├── formatters.js    # Data formatting
    ├── validators.js    # Form validation
    └── constants.js     # Application constants
```

### State Management with Pinia

```javascript
// stores/portfolio.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { portfolioApi } from '@/services/portfolio'

export const usePortfolioStore = defineStore('portfolio', () => {
  // State
  const portfolios = ref([])
  const currentPortfolio = ref(null)
  const loading = ref(false)

  // Getters
  const totalValue = computed(() => {
    return portfolios.value.reduce((sum, p) => sum + p.total_value, 0)
  })

  // Actions
  async function fetchPortfolios() {
    loading.value = true
    try {
      portfolios.value = await portfolioApi.getAll()
    } catch (error) {
      console.error('Failed to fetch portfolios:', error)
    } finally {
      loading.value = false
    }
  }

  return {
    portfolios,
    currentPortfolio,
    loading,
    totalValue,
    fetchPortfolios
  }
})
```

### Vue Router Configuration

```javascript
// router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/pages/Dashboard.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/portfolios',
    name: 'Portfolios',
    component: () => import('@/pages/Portfolio/PortfolioList.vue')
  },
  {
    path: '/portfolios/:name',
    name: 'PortfolioDetail',
    component: () => import('@/pages/Portfolio/PortfolioDetail.vue'),
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

## Backend Architecture

### FastAPI Application Structure

```
backend/
├── main.py              # Application entry point
├── config/              # Configuration management
│   ├── __init__.py
│   ├── settings.py      # App settings
│   └── database.py      # Database configuration
├── models/              # SQLAlchemy models
│   ├── __init__.py
│   ├── portfolio.py     # Portfolio model
│   ├── trade.py         # Trade model
│   └── execution.py     # Execution log model
├── routers/             # API route handlers
│   ├── __init__.py
│   ├── portfolios.py    # Portfolio CRUD operations
│   ├── agents.py        # Agent execution + WebSocket
│   ├── trades.py        # Trade management
│   ├── analytics.py     # Dashboard analytics
│   └── system.py        # System health
├── services/            # Business logic layer
│   ├── __init__.py
│   ├── portfolio_service.py
│   ├── agent_service.py
│   ├── trade_service.py
│   └── market_service.py
├── middleware/          # Custom middleware
│   ├── __init__.py
│   ├── performance.py   # Performance monitoring
│   ├── cache.py         # Caching middleware
│   └── cors.py          # CORS configuration
├── utils/               # Utility modules
│   ├── __init__.py
│   ├── database.py      # Database utilities
│   ├── cache.py         # Cache utilities
│   └── validators.py    # Input validation
└── schemas/             # Pydantic schemas
    ├── __init__.py
    ├── portfolio.py     # Portfolio schemas
    ├── trade.py         # Trade schemas
    └── response.py      # Response schemas
```

### FastAPI Application Initialization

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend.routers import portfolios, agents, trades, analytics, system
from backend.middleware.performance import PerformanceMiddleware
from backend.middleware.cache import CacheMiddleware

app = FastAPI(
    title="FinTradeAgent API",
    description="AI-powered trading intelligence platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(PerformanceMiddleware)
app.add_middleware(CacheMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(portfolios.router, prefix="/api/portfolios", tags=["portfolios"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
```

### Database Models

```python
# backend/models/portfolio.py
from sqlalchemy import Column, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Portfolio(Base):
    __tablename__ = "portfolios"

    name = Column(String, primary_key=True, index=True)
    strategy_prompt = Column(Text, nullable=False)
    initial_amount = Column(Float, nullable=False)
    current_cash = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    num_initial_trades = Column(Integer, default=3)
    trades_per_run = Column(Integer, default=3)
    run_frequency = Column(String, default="daily")
    llm_provider = Column(String, default="openai")
    llm_model = Column(String, default="gpt-4o")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
```

### Service Layer Pattern

```python
# backend/services/portfolio_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.portfolio import Portfolio
from backend.schemas.portfolio import PortfolioCreate, PortfolioUpdate

class PortfolioService:
    def __init__(self, db: Session):
        self.db = db

    async def create_portfolio(self, portfolio_data: PortfolioCreate) -> Portfolio:
        """Create a new portfolio."""
        db_portfolio = Portfolio(**portfolio_data.dict())
        self.db.add(db_portfolio)
        self.db.commit()
        self.db.refresh(db_portfolio)
        return db_portfolio

    async def get_portfolio(self, name: str) -> Optional[Portfolio]:
        """Get portfolio by name."""
        return self.db.query(Portfolio).filter(Portfolio.name == name).first()

    async def list_portfolios(self) -> List[Portfolio]:
        """List all active portfolios."""
        return self.db.query(Portfolio).filter(Portfolio.is_active == True).all()

    async def update_portfolio(self, name: str, portfolio_data: PortfolioUpdate) -> Optional[Portfolio]:
        """Update existing portfolio."""
        db_portfolio = await self.get_portfolio(name)
        if not db_portfolio:
            return None
        
        for key, value in portfolio_data.dict(exclude_unset=True).items():
            setattr(db_portfolio, key, value)
        
        self.db.commit()
        self.db.refresh(db_portfolio)
        return db_portfolio
```

## WebSocket Integration

### Backend WebSocket Handler

```python
# backend/routers/agents.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, portfolio_name: str):
        await websocket.accept()
        if portfolio_name not in self.active_connections:
            self.active_connections[portfolio_name] = set()
        self.active_connections[portfolio_name].add(websocket)

    def disconnect(self, websocket: WebSocket, portfolio_name: str):
        if portfolio_name in self.active_connections:
            self.active_connections[portfolio_name].discard(websocket)

    async def send_message(self, portfolio_name: str, message: dict):
        if portfolio_name in self.active_connections:
            dead_connections = set()
            for websocket in self.active_connections[portfolio_name]:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    dead_connections.add(websocket)
            
            # Clean up dead connections
            for conn in dead_connections:
                self.active_connections[portfolio_name].discard(conn)

manager = ConnectionManager()

@router.websocket("/ws/{portfolio_name}")
async def websocket_endpoint(websocket: WebSocket, portfolio_name: str):
    await manager.connect(websocket, portfolio_name)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, portfolio_name)
```

### Frontend WebSocket Service

```javascript
// services/websocket.js
export class WebSocketService {
  constructor() {
    this.connections = new Map()
  }

  connect(portfolioName, callbacks = {}) {
    if (this.connections.has(portfolioName)) {
      return this.connections.get(portfolioName)
    }

    const ws = new WebSocket(`ws://localhost:8000/api/agents/ws/${portfolioName}`)
    
    ws.onopen = () => {
      console.log(`WebSocket connected for ${portfolioName}`)
      callbacks.onOpen?.(portfolioName)
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      callbacks.onMessage?.(data)
    }

    ws.onclose = () => {
      console.log(`WebSocket closed for ${portfolioName}`)
      this.connections.delete(portfolioName)
      callbacks.onClose?.(portfolioName)
    }

    ws.onerror = (error) => {
      console.error(`WebSocket error for ${portfolioName}:`, error)
      callbacks.onError?.(error)
    }

    this.connections.set(portfolioName, ws)
    return ws
  }

  disconnect(portfolioName) {
    const ws = this.connections.get(portfolioName)
    if (ws) {
      ws.close()
      this.connections.delete(portfolioName)
    }
  }
}

export const wsService = new WebSocketService()
```

## Data Flow

### Agent Execution Flow

```
1. User clicks "Execute Agent" in Vue.js UI
   ↓
2. Frontend sends POST /api/agents/{name}/execute
   ↓
3. Backend validates request and starts execution
   ↓
4. AgentService collects portfolio context:
   - Current holdings and positions
   - Market data from external APIs
   - Historical performance analysis
   ↓
5. LLM Provider (OpenAI/Anthropic) processes strategy
   ↓
6. Real-time updates sent via WebSocket:
   - Execution started
   - Data collection progress
   - LLM processing
   - Recommendations generated
   ↓
7. Frontend receives recommendations via WebSocket
   ↓
8. User reviews and accepts/rejects trades
   ↓
9. Trade execution updates portfolio state
   ↓
10. Dashboard updates with new performance data
```

### Caching Strategy

```python
# backend/utils/cache.py
import redis
import json
from typing import Any, Optional
from datetime import timedelta

class CacheService:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        try:
            value = self.redis.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: timedelta = timedelta(hours=1)):
        """Set cached value with TTL."""
        try:
            self.redis.setex(key, ttl, json.dumps(value))
        except Exception:
            pass  # Fail silently, don't break application

    async def delete(self, key: str):
        """Delete cached value."""
        try:
            self.redis.delete(key)
        except Exception:
            pass

cache = CacheService()
```

## Performance Optimizations

### Frontend Optimizations
- **Code Splitting**: Route-based lazy loading
- **Component Lazy Loading**: Large components loaded on demand
- **Image Optimization**: Responsive images with lazy loading
- **Bundle Analysis**: Regular bundle size monitoring
- **Service Worker**: Caching for offline functionality

### Backend Optimizations
- **Database Query Optimization**: Indexed queries and eager loading
- **Response Caching**: Redis-based caching for expensive operations
- **Connection Pooling**: Database connection pool management
- **Async Operations**: Non-blocking I/O for all external API calls
- **Middleware Optimization**: Gzip compression and performance monitoring

### Infrastructure Optimizations
- **CDN**: Static asset delivery via CDN
- **Load Balancing**: Multiple backend instances for high availability
- **Database Optimization**: Query optimization and indexing strategies
- **Monitoring**: Real-time performance metrics and alerting

## Security Considerations

### Frontend Security
- **Input Validation**: Client-side validation with server-side verification
- **XSS Prevention**: Proper data sanitization
- **HTTPS Enforcement**: All production traffic over HTTPS
- **Content Security Policy**: Strict CSP headers

### Backend Security
- **Input Validation**: Pydantic schema validation
- **SQL Injection Prevention**: SQLAlchemy ORM usage
- **Rate Limiting**: API rate limiting per client
- **CORS Configuration**: Restricted origin policies
- **Environment Variables**: Secure secret management

## Deployment Architecture

### Development Environment
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=sqlite:///./fintrade.db
      - REDIS_URL=redis://redis:6379

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### Production Environment
```yaml
# docker-compose.production.yml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./ssl:/etc/ssl/certs

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    expose:
      - "80"

  backend:
    build: ./backend
    expose:
      - "8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379

  redis:
    image: redis:alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: fintrade
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  redis_data:
  postgres_data:
```

## Integration with External Services

### LLM Provider Integration
- **OpenAI**: GPT-4o with web search capabilities
- **Anthropic**: Claude with web search tool integration
- **Provider Abstraction**: Unified interface for multiple LLM providers
- **Rate Limiting**: Intelligent rate limiting and retry mechanisms
- **Cost Tracking**: Token usage monitoring and cost optimization

### Market Data Integration
- **Yahoo Finance**: Real-time stock price data
- **SEC EDGAR**: Filing and insider trading data
- **Web Search**: Real-time news and market sentiment
- **Caching Strategy**: Intelligent caching to minimize API calls

This architecture provides a scalable, maintainable foundation for the FinTradeAgent platform, enabling real-time trading intelligence with modern web technologies.