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

## Agent Workflow (Detailed)

When you click "Run Agent", a comprehensive data collection and analysis pipeline executes before the LLM receives the prompt.

### Data Collection Pipeline

```
AgentService.execute()
├── _build_prompt()
│   ├── StockDataService.format_holdings_for_prompt()
│   │   └── get_price_context() [per holding]
│   │       ├── SecurityService stored data (52w range, MAs, short interest)
│   │       └── yfinance.history() → cached CSV (24h)
│   │
│   ├── MarketDataService.get_full_context_for_holdings()
│   │   ├── get_macro_data() → S&P 500, NASDAQ, DOW, VIX, Treasury yields
│   │   ├── get_earnings_info() [per holding] → upcoming earnings dates
│   │   ├── get_sec_filings() [per holding] → recent 8-K, 10-Q, 10-K
│   │   └── get_insider_trades() [per holding] → insider transactions
│   │
│   └── ReflectionService.analyze_performance()
│       ├── _find_completed_trades() → FIFO match buys with sells
│       ├── _calculate_metrics() → win rate, avg gain/loss, holding days
│       ├── _analyze_biases() → patterns, warnings, themes
│       └── _generate_insights() → actionable recommendations
│
├── LLMProvider.generate(prompt, model)
├── _parse_response() → AgentRecommendation
└── _save_log() → data/logs/{portfolio}_{timestamp}.md
```

### 1. Holdings Context (StockDataService)

For each holding in the portfolio, the system fetches:

| Data Point | Source | Purpose |
|------------|--------|---------|
| Current price | yfinance (cached 24h) | Position valuation |
| 5-day change | Calculated from history | Short-term momentum |
| 30-day change | Calculated from history | Medium-term trend |
| 52-week high/low | SecurityService stored data | Range position |
| RSI-14 | Calculated from price history | Overbought/oversold |
| Volume vs 20-day avg | Calculated | Unusual activity detection |
| 20-day & 50-day MAs | SecurityService or calculated | Trend analysis |
| Short interest | SecurityService (if >10%) | Squeeze potential |
| P/L from avg price | Calculated | Position performance |

**Caching**: Price data is cached to CSV files in `data/stock_data/{TICKER}_prices.csv` for 24 hours. SecurityService stores ticker metadata in `{TICKER}_data.json` to minimize API calls.

### 2. Market Data Context (MarketDataService)

**Macro Data** (always fetched):
- S&P 500, NASDAQ, DOW: price and daily % change
- VIX: volatility index
- Treasury yields: 2-year and 10-year

**Per-Holding Data** (only when holdings exist):

| Data Type | Source | What's Included |
|-----------|--------|-----------------|
| Earnings | yfinance calendar | Date, EPS estimate, revenue estimate, days until |
| SEC Filings | yfinance sec_filings | Recent 8-K, 10-Q, 10-K with titles and dates |
| Insider Trades | yfinance insider_transactions | Name, position, shares, value, transaction type |

All market data is cached in memory for 24 hours.

### 3. Reflection Context (ReflectionService)

The reflection system analyzes past trade performance to help the agent learn from history. This runs **before every execution** with no external API calls.

**Completed Trade Matching** (FIFO):
- Groups trades by ticker
- Matches BUYs with subsequent SELLs using first-in-first-out
- Handles partial fills (buy 10, sell 5+5 = two completed trades)

**Metrics Calculated**:
- Win/loss count and win rate
- Average gain per winner, average loss per loser
- Average holding days (winners vs losers)
- Total realized P/L
- Best and worst trades with reasoning

**Bias Detection**:
| Bias | Detection Logic |
|------|-----------------|
| Quick trades | Held < 7 days |
| Early profit-taking | Winners held < 50% of average |
| Loss aversion | Losers held > 150% of average |
| FOMO | Keyword detection in buy reasoning |
| Overtrading | > 50% quick trades |

**Generated Warnings**:
- Low win rate (< 40% with 5+ trades)
- Poor risk/reward ratio (avg loss > avg gain)
- Pattern-based warnings (cutting winners, holding losers)

**Actionable Insights**:
- Win rate assessment
- Risk/reward analysis
- Holding period recommendations
- Theme diversity suggestions

### 4. Prompt Assembly

All collected data is injected into the prompt template:

```
SYSTEM PROMPT
├── Strategy definition (from portfolio YAML)
├── Current state: cash balance, initial amount
├── Holdings info (with all price context above)
├── Trade history (all executed trades)
├── Market intelligence:
│   ├── Macro data
│   ├── Upcoming earnings
│   ├── SEC filings
│   └── Insider trades
├── Self-reflection (metrics, biases, insights)
└── Constraints:
    ├── Max trades per run
    ├── Real tickers only
    ├── No duplicate tickers
    ├── 1% transaction cost assumption
    └── BUY orders require stop_loss and take_profit
```

### 5. LLM Invocation

Single call to the configured LLM provider (OpenAI or Anthropic) with the complete prompt. The response must be valid JSON containing:
- `summary`: Overall market assessment
- `trades`: Array of recommendations with ticker, action, quantity, reasoning
- BUY orders include `stop_loss_price` and `take_profit_price`

### 6. Logging

Every execution saves a full log to `data/logs/{portfolio_name}_{timestamp}.md`:
- Complete prompt sent
- Raw LLM response
- Useful for debugging and strategy iteration

### Data Flow Timeline

1. **User clicks "Run Agent"** → Optional user guidance captured
2. **Load config/state** from YAML/JSON files
3. **Parallel data collection** (cached when possible):
   - Holdings price history
   - Market macro data
   - Earnings, filings, insider trades per holding
4. **Reflection analysis** (instant, local data only)
5. **Prompt assembly** with all context
6. **Single LLM call** with complete prompt
7. **Parse response** → structured recommendations
8. **Save log** for debugging
9. **Return to UI** for human review

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
