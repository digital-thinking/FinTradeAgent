# FinTradeAgent - AI-Powered Trading Intelligence Platform

An experimental platform for AI-powered trading agents that analyze markets and recommend trades using LLM reasoning capabilities. **Now featuring a modern Vue.js web interface with a high-performance FastAPI backend.**

## 🚀 Vue.js Migration Complete

FinTradeAgent has been fully migrated from Streamlit to a modern tech stack:
- **Frontend**: Vue 3 + Vite + Tailwind CSS + Pinia
- **Backend**: FastAPI + WebSocket support 
- **Architecture**: Decoupled SPA with RESTful API
- **Real-time**: WebSocket integration for live execution updates
- **Performance**: Optimized for production deployment

## What This Is

This is **not** a portfolio management system. There are plenty of those.

This is a platform for running **AI trading agents** - each with a distinct strategy persona - that:
- Research markets using web search for real-time data
- Analyze opportunities based on their programmed strategy
- Recommend specific trades with reasoning
- Learn from the context of past decisions

Portfolio tracking exists solely to give agents the context they need: "What do I own? What's my cash? What did I do before?" The AI needs this history to make informed decisions.

## 🏗️ Architecture Overview

### Frontend (Vue.js)
```
frontend/
├── src/
│   ├── components/     # Reusable Vue components
│   ├── pages/         # Page components (Dashboard, Portfolio, etc.)
│   ├── stores/        # Pinia state management
│   ├── services/      # API service layer
│   ├── composables/   # Vue composition functions
│   └── router/        # Vue Router configuration
├── tests/             # Unit and E2E tests
└── public/            # Static assets
```

### Backend (FastAPI)
```
backend/
├── routers/           # API route handlers
│   ├── portfolios.py  # Portfolio CRUD operations
│   ├── agents.py      # Agent execution + WebSocket
│   ├── trades.py      # Trade management
│   ├── analytics.py   # Dashboard analytics
│   └── system.py      # System health monitoring
├── services/          # Business logic services
├── models/            # Data models and schemas
├── middleware/        # Performance and caching middleware
└── utils/             # Database and optimization utilities
```

## 🌟 Key Features

### 🧠 Multi-Agent Architectures
The platform supports different modes of agent reasoning:
- **Simple Mode**: A single agent analyzes the portfolio and market data to make decisions.
- **Debate Mode**: Three agents (Bull, Bear, Neutral) debate the strategy before a Moderator makes the final decision.
- **LangGraph Mode**: A structured workflow where agents perform specific sub-tasks (Research → Analyze → Decide).

### 🔎 Real-Time Market Research
Agents aren't limited to training data. They actively use **web search** to fetch:
- Current stock prices and technical indicators
- Recent news and earnings reports
- Analyst ratings and sentiment
- Macroeconomic data

### 📊 Modern Web Interface
- **Dashboard**: Real-time portfolio overview with performance charts
- **Portfolio Management**: Create, edit, and manage AI trading strategies
- **Live Execution**: WebSocket-powered real-time execution monitoring
- **Trade Review**: Interactive trade recommendation review interface
- **System Health**: Comprehensive monitoring and analytics dashboard

### 🛡️ Human-in-the-Loop Control
AI suggests, you decide.
- **Review Interface**: Inspect every recommended trade, reasoning, and price data before execution
- **Ticker Correction**: Fix hallucinated or incorrect ticker symbols on the fly
- **Guidance**: Inject specific context or instructions (e.g., "Avoid tech stocks today") before the agent runs

### 📈 Interactive Analytics
- **Performance Charts**: Real-time Chart.js visualizations tracking portfolio value over time
- **Holdings Breakdown**: Detailed views of current positions, cost basis, and unrealized gains
- **Trade History**: Searchable, paginated history of all executed transactions
- **Execution Logs**: Full visibility into LLM prompts and responses for debugging

### ⚙️ System Health & Observability
- **Real-time Metrics**: Live system performance monitoring
- **Recommendation Tracking**: Monitor acceptance rates of agent suggestions
- **Cost & Latency**: Track token usage and execution times
- **Error Monitoring**: Comprehensive error tracking and debugging

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm/yarn
- Python 3.10+
- Poetry (for Python dependency management)

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/FinTradeAgent.git
cd FinTradeAgent
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.production .env

# Configure API keys
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
BRAVE_SEARCH_API_KEY=your-brave-search-key

# Database and cache configuration
DATABASE_URL=sqlite:///./fintrade.db
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-here
```

### 3. Backend Setup
```bash
# Install Python dependencies
poetry install

# Run database migrations
poetry run alembic upgrade head

# Start FastAPI backend (development)
poetry run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 5. Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🐳 Docker Deployment

### Development Environment
```bash
# Start development stack
docker-compose -f docker-compose.dev.yml up -d

# Access services
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# Monitoring: http://localhost:3001 (Grafana)
```

### Production Environment
```bash
# Build and start production stack
docker-compose -f docker-compose.production.yml up -d

# Includes:
# - Nginx reverse proxy with SSL
# - Redis caching
# - Monitoring with Grafana + Prometheus
# - Automated backups
```

## 📋 API Documentation

### Core Endpoints

#### Portfolios
```
GET    /api/portfolios/           # List all portfolios
POST   /api/portfolios/           # Create portfolio
GET    /api/portfolios/{name}     # Get portfolio details
PUT    /api/portfolios/{name}     # Update portfolio
DELETE /api/portfolios/{name}     # Delete portfolio
```

#### Agent Execution
```
POST   /api/agents/{name}/execute # Execute agent for portfolio
WS     /api/agents/{name}/ws      # WebSocket for live updates
```

#### Trade Management
```
GET    /api/trades/pending        # Get pending trades
POST   /api/trades/{id}/apply     # Apply trade
DELETE /api/trades/{id}           # Cancel trade
```

#### Analytics
```
GET    /api/analytics/dashboard   # Dashboard summary data
GET    /api/analytics/execution-logs # Execution history
```

#### System Health
```
GET    /api/system/health         # System health status
GET    /api/system/scheduler      # Scheduler status
GET    /api/system/metrics        # Performance metrics
```

For complete API documentation with examples, visit `/docs` when running the backend.

## 🎯 Creating an Agent

Create a YAML file in `data/portfolios/`:

```yaml
name: "Your Agent Name"
strategy_prompt: |
  You are a [STRATEGY TYPE] specialist. Your goal is to [OBJECTIVE].

  WHAT TO RESEARCH:
  - [Data points the agent should look for]

  DECISION LOGIC:
  - BUY SIGNAL: [Conditions]
  - SELL SIGNAL: [Conditions]

  Always use web search to verify current data before recommending.

initial_amount: 10000.0
num_initial_trades: 3
trades_per_run: 3
run_frequency: daily
llm_provider: openai
llm_model: gpt-4o
```

The `strategy_prompt` is everything. It defines the agent's personality, research methodology, and decision framework.

## 📖 Documentation

- **[Technical Architecture](docs/ARCHITECTURE.md)** - Detailed system architecture
- **[API Documentation](docs/API.md)** - Complete API reference
- **[Database Schema](docs/DATABASE_SCHEMA.md)** - Data model documentation
- **[WebSocket Guide](docs/WEBSOCKET.md)** - Real-time integration guide
- **[User Guide](docs/USER_GUIDE.md)** - Portfolio and agent management
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Development setup and workflows
- **[Deployment Guide](docs/PRODUCTION_DEPLOYMENT.md)** - Production deployment procedures
- **[Performance Guide](docs/PERFORMANCE_OPTIMIZATION.md)** - Optimization strategies
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

## 🧪 Testing

### Frontend Testing
```bash
cd frontend

# Unit tests
npm run test

# E2E tests with Playwright
npm run test:e2e

# Test coverage
npm run test:coverage

# Run all tests
npm run test:all
```

### Backend Testing
```bash
# Unit tests
poetry run pytest

# Integration tests
poetry run pytest tests/integration/

# Test coverage
poetry run pytest --cov=backend --cov-report=html
```

## Example Agents

### Take-Private Arbitrage Agent
Hunts for merger arbitrage opportunities in announced take-private deals. Calculates spreads, scores deal completion probability, assesses downside risk.

### Earnings Momentum Agent
Identifies "Double Surprise" events - companies that beat estimates AND raised guidance. Scores CEO confidence from earnings calls.

### Squeeze Hunter Agent
Finds potential short squeeze setups based on short interest, days to cover, and catalyst identification.

### Insider Conviction Agent
Tracks insider buying patterns to identify high-conviction opportunities from people who know the company best.

See `data/portfolios/` for all agent configurations.

## 🔍 How It Works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Agent Config   │────▶│   LLM + Search  │────▶│ Recommendations │
│  (Strategy +    │     │   (Reasoning +  │     │ (Trades with    │
│   Context)      │     │    Research)    │     │  Reasoning)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vue.js UI     │◄────│   FastAPI       │◄────│  Human Review   │
│  (Live Updates) │     │   (WebSocket)   │     │  Accept/Reject  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 🛠️ Development

### Frontend Development
```bash
cd frontend
npm run dev        # Start dev server with hot reload
npm run build      # Production build
npm run preview    # Preview production build
```

### Backend Development
```bash
poetry run uvicorn backend.main:app --reload  # Auto-reload on changes
poetry run pytest --watch                     # Watch mode testing
```

### Code Quality
```bash
# Frontend
npm run lint       # ESLint
npm run format     # Prettier

# Backend
poetry run black backend/     # Code formatting
poetry run isort backend/     # Import sorting
poetry run mypy backend/      # Type checking
```

## 🚢 Production Considerations

### Performance Optimizations
- Frontend code splitting and lazy loading
- Backend caching with Redis
- Database query optimization
- WebSocket connection pooling
- CDN for static assets

### Security
- CORS configuration
- Rate limiting
- Input validation and sanitization
- Environment variable security
- SSL/TLS encryption

### Monitoring
- Application performance monitoring
- Error tracking and alerting
- System metrics collection
- Log aggregation and analysis

## 📚 Why This Exists

Traditional quant strategies compete on speed - microsecond execution, colocation, proprietary data feeds. That game is won.

The next edge is **reasoning depth** - the ability to process unstructured information (earnings calls, news, filings) and extract insights before market consensus forms. LLMs excel at this.

This platform is for experimenting with that idea, now with a modern, scalable web architecture.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for detailed contribution guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` folder for detailed guides
- **Issues**: Open an issue on GitHub for bugs or feature requests
- **API Docs**: Visit `/docs` endpoint when running the backend
- **Community**: Join our discussions on GitHub

---

**Built with ❤️ using Vue.js, FastAPI, and AI reasoning capabilities.**