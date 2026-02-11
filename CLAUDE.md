# Claude Code Instructions
## Development

Do not commit on your own to git, only if prompted by the user
Don't overengineer: Simple beats complex
Don't mock and make up things aside from tests
No fallbacks: One correct path, no alternatives
One way: One way to do things, not many
Clarity over compatibility: Clear code beats backward compatibility
Throw errors: Fail fast when preconditions aren't met
No backups: Trust the primary mechanism
Separation of concerns: Each function should have a single responsibility

## Development Methodology

Evidence-based debugging: Add minimal, targeted logging
Fix root causes: Address the underlying issue, not just symptoms
Simple > Complex: Let Python's type hints catch errors instead of excessive runtime checks
Collaborative process: Work with user to identify most efficient solution

## Testing
Add Unit tests, if they are missing



## Project Overview

This is **Agentic Trade Assistant** - a modern web application for managing AI-powered stock portfolios with LLM trading recommendations based on the "Semantic Alpha" framework.

## Tech Stack

- **Python 3.12+** with Poetry for dependency management
- **FastAPI** for the backend API
- **Vue.js 3** for the frontend UI
- **OpenAI/Anthropic** APIs for LLM-powered trade recommendations
- **yfinance** for stock data fetching
- **pandas/plotly** for data processing and charts

## Project Structure

```
backend/fin_trade/
├── models/                   # Dataclasses (Holding, Trade, PortfolioConfig, etc.)
└── services/
    ├── stock_data.py         # Yahoo Finance integration
    ├── portfolio.py          # Portfolio CRUD and calculations
    └── agent.py              # LLM invocation and prompt building

backend/                      # FastAPI application
├── main.py                   # FastAPI entry point
├── routers/                  # API route handlers
├── services/                 # Backend API services
└── models/                   # Pydantic data models

frontend/                     # Vue.js application
├── src/
├── components/               # Vue components
└── views/                    # Vue pages

data/
├── portfolios/               # Portfolio YAML configs (strategy prompts)
├── state/                    # Portfolio state JSON (holdings, trades)
├── logs/                     # Agent prompt/response logs for debugging
└── stock_data/               # Stock price CSV cache
```

## Key Commands

```bash
# Install dependencies
poetry install

# Run the backend
cd backend && python main.py
# Backend runs on http://localhost:8000

# Run the frontend (separate terminal)
cd frontend && npm run dev
# Frontend runs on http://localhost:3000
```

## Configuration

- API keys are stored in `.env` file
- Portfolios are defined in `data/portfolios/*.yaml`
- Each portfolio has a `strategy_prompt` that defines the LLM's trading persona

## Key Design Decisions

1. **LLMs choose stocks freely** - No hardcoded stock list. LLMs recommend any ticker symbol.
2. **rebalancing** - Strategies are designed for configurable execution cadence.(daily, weekly, monthly)
3. **Human-in-the-loop** - Agent generates recommendations, user accepts/rejects.
4. **Logging** - All LLM prompts and responses are logged to `data/logs/` for debugging.

## Common Tasks

### Adding a new portfolio strategy
Create a new YAML file in `data/portfolios/` with:
```yaml
name: "Strategy Name"
strategy_prompt: |
  Your detailed strategy prompt...
initial_amount: 10000.0
num_initial_trades: 5
trades_per_run: 3
run_frequency: weekly
llm_provider: openai
llm_model: gpt-4o
```

### Debugging LLM responses
Check `data/logs/` for timestamped log files containing full prompts and responses.

### Modifying the agent prompt
Edit `backend/fin_trade/services/agent.py` - the `_build_prompt()` method constructs the system prompt.

## Windows Notes

- This project is developed on Windows
- Use forward slashes in Python Path operations
- The `.env` file is loaded via `python-dotenv`



