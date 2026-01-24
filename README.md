# Agentic Trade Assistant

An experimental platform for AI-powered trading agents that analyze markets and recommend trades using LLM reasoning capabilities.

## What This Is

This is **not** a portfolio management system. There are plenty of those.

This is a platform for running **AI trading agents** - each with a distinct strategy persona - that:
- Research markets using web search for real-time data
- Analyze opportunities based on their programmed strategy
- Recommend specific trades with reasoning
- Learn from the context of past decisions

Portfolio tracking exists solely to give agents the context they need: "What do I own? What's my cash? What did I do before?" The AI needs this history to make informed decisions.

## Core Concept

Each agent is defined by a **strategy prompt** - a detailed persona that tells the LLM how to think about markets. The agent then:

1. Receives current portfolio state (holdings, cash, trade history)
2. Uses web search to gather real-time market data
3. Applies its strategy logic to identify opportunities
4. Returns structured trade recommendations with reasoning
5. Human reviews and accepts/rejects

This is **human-in-the-loop AI trading research**, not automated execution.

## Key Features

### 🧠 Multi-Agent Architectures
The platform supports different modes of agent reasoning:
- **Simple Mode**: A single agent analyzes the portfolio and market data to make decisions.
- **Debate Mode**: Three agents (Bull, Bear, Neutral) debate the strategy before a Moderator makes the final decision.
- **LangGraph Mode**: A structured workflow where agents perform specific sub-tasks (Research -> Analyze -> Decide).

### 🔎 Real-Time Market Research
Agents aren't limited to training data. They actively use **web search** to fetch:
- Current stock prices and technical indicators.
- Recent news and earnings reports.
- Analyst ratings and sentiment.
- Macroeconomic data.

### 📊 Portfolio Dashboard
A centralized command center to monitor all your active strategies:
- **Total AUM & Performance**: Aggregated metrics across all portfolios.
- **Leaderboard**: Instantly see which strategies are outperforming.
- **Schedule**: Track upcoming execution times for each agent.

### 🛡️ Human-in-the-Loop Control
AI suggests, you decide.
- **Review Interface**: Inspect every recommended trade, reasoning, and price data before execution.
- **Ticker Correction**: Fix hallucinated or incorrect ticker symbols on the fly.
- **Guidance**: Inject specific context or instructions (e.g., "Avoid tech stocks today") before the agent runs.

### 📈 Interactive Analytics
- **Performance Charts**: Zoomable, interactive Plotly charts tracking portfolio value over time.
- **Holdings Breakdown**: Detailed views of current positions, cost basis, and unrealized gains.
- **Trade History**: Searchable, paginated history of all executed transactions.

### ⚙️ System Health & Observability
- **Execution Logs**: Full visibility into LLM prompts and responses for debugging.
- **Recommendation Tracking**: Monitor acceptance rates of agent suggestions.
- **Cost & Latency**: Track token usage and execution times.

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

## Quick Start

```bash
# Install
poetry install

# Configure API keys in .env
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key

# Run
poetry run streamlit run src/fin_trade/app.py
```

## Creating an Agent

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
llm_model: gpt-5.2
```

The `strategy_prompt` is everything. It defines the agent's personality, research methodology, and decision framework.

## Web Search

Agents have access to real-time data via LLM web search:

**OpenAI**: Models automatically mapped to search variants
- `gpt-4o` → `gpt-4o-search-preview`
- `gpt-5.2` → `gpt-5-search-api`

**Anthropic**: Web search tool enabled automatically
- Uses `web_search_20250305` capability

This means agents can research current prices, news, SEC filings, earnings dates, deal status - whatever their strategy requires.

## How It Works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Agent Config   │────▶│   LLM + Search  │────▶│ Recommendations │
│  (Strategy +    │     │   (Reasoning +  │     │ (Trades with    │
│   Context)      │     │    Research)    │     │  Reasoning)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │  Human Review   │
                                                │  Accept/Reject  │
                                                └─────────────────┘
```

## Project Structure

```
src/fin_trade/
├── services/
│   ├── agent.py          # LLM invocation, web search, prompt building
│   ├── security.py       # Ticker/price resolution
│   ├── portfolio.py      # State management (for agent context)
│   └── llm_provider.py   # Abstracted LLM provider logic
├── components/
│   ├── trade_display.py  # Recommendation UI with validation
│   ├── skeleton.py       # Loading state components
│   └── status_badge.py   # UI badges
├── pages/
│   ├── dashboard.py      # Summary dashboard
│   ├── portfolio_detail.py # Agent execution interface
│   └── system_health.py  # System monitoring
└── style.css             # Global styling (Matrix theme)

data/
├── portfolios/           # Agent configurations (YAML)
├── state/               # Portfolio state (JSON) - agent context
└── logs/                # All LLM prompts/responses for debugging
```

## Debugging Agents

Every agent interaction is logged to `data/logs/`:
- Full prompt sent to LLM
- Complete response received
- Timestamp, model, provider

Use these logs to understand why an agent made specific recommendations and iterate on your strategy prompts.

---

## Why This Exists

Traditional quant strategies compete on speed - microsecond execution, colocation, proprietary data feeds. That game is won.

The next edge is **reasoning depth** - the ability to process unstructured information (earnings calls, news, filings) and extract insights before market consensus forms. LLMs excel at this.

This platform is for experimenting with that idea.

## License

MIT
