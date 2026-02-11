# Roadmap

The Agentic Trade Assistant is a playground for experimenting with AI-driven trading strategies. This roadmap focuses on features that strengthen that experimentation loop: run strategies, observe outcomes, compare results, iterate. Features are evaluated critically -- each includes honest trade-offs.

**Guiding principles:**
- No external paid services beyond the LLM APIs already in use
- No broker integrations -- this is a simulation environment
- The application provides the playground; users provide the strategies
- If a feature doesn't help users learn something about their strategies, it doesn't belong here

---

## Phase 1: Experiment Infrastructure

Features that make the core experimentation loop faster and more reliable.

### 1.1 Scheduled Execution

Auto-run strategies on their configured cadence (daily/weekly/monthly) without requiring the UI to be open.

**What it involves:**
- Background scheduler (APScheduler or similar) that persists across app restarts
- Auto-apply mode vs. queue-for-review mode per portfolio
- Simple start/stop controls in the UI
- Execution history visible in dashboard

**Pros:**
- Strategies can accumulate real track records over weeks/months unattended
- The `run_frequency` field in portfolio configs already exists but does nothing -- this makes it functional
- Essential for any meaningful long-term strategy comparison

**Cons:**
- Requires proper background task management with FastAPI and worker processes
- Users may forget it's running and accumulate unexpected API costs
- Error handling for unattended runs needs to be robust (network failures, API rate limits, invalid tickers)

---

### 1.2 Portfolio Cloning & Reset

Clone an existing portfolio (config + optionally state) and reset a portfolio to its initial state.

**What it involves:**
- "Clone" button that duplicates a portfolio YAML with a new name
- Option to clone with or without current state (holdings/trades)
- "Reset" button that wipes state back to initial cash, zero holdings
- Confirmation dialogs to prevent accidental data loss

**Pros:**
- Fundamental for A/B testing -- clone a strategy, tweak the prompt, compare outcomes
- Reset enables re-running experiments from a clean slate
- Trivial to implement given the YAML/JSON file-based architecture

**Cons:**
- Clone with state could confuse users (two portfolios with identical holdings diverging over time)
- No undo for reset -- once state is wiped, trade history is gone (could archive instead of delete)

---

## Phase 2: Comparison & Analysis

Features that help users draw conclusions from their experiments.

### 2.1 Strategy Benchmarking

Compare portfolio performance against a benchmark index (S&P 500) and against each other on normalized charts.

**What it involves:**
- Overlay S&P 500 total return on each portfolio's performance chart
- Normalized comparison view: pick 2+ portfolios, align start dates, show relative performance
- Key metrics table: alpha, beta, Sharpe ratio, max drawdown, win rate side by side

**Pros:**
- Without benchmarking, it's impossible to know if a strategy is actually good or just riding a bull market
- Cross-strategy comparison is the core value proposition of running multiple strategies
- S&P 500 data is already available via yfinance at no cost

**Cons:**
- Statistical metrics (Sharpe, alpha, beta) need sufficient trade history to be meaningful -- showing them too early may mislead
- Normalized comparison only works well when portfolios start around the same time
- Risk of users over-fitting to metrics that look good on small samples

---

### 2.2 Execution Replay

Browse past agent executions with full context: what the agent saw, what it recommended, what was applied, and what happened after.

**What it involves:**
- Timeline view of all executions per portfolio
- For each execution: show the prompt context, research gathered, recommendations made, which trades were applied/rejected
- Show post-execution outcome: did the recommended trades go up or down after execution?

**Pros:**
- Critical for understanding *why* strategies succeed or fail
- Data already exists in SQLite logs and markdown files -- this is primarily a UI feature
- Post-execution outcome tracking turns every execution into a learning opportunity

**Cons:**
- Post-execution outcome calculation requires matching recommendations to subsequent price movements, which adds complexity
- UI could become cluttered with too much historical data -- needs good filtering/search
- Users may anchor on individual decisions rather than statistical patterns

---

## Phase 3: Broader Model Support

Features that expand what users can experiment with.

### 3.1 Local LLM Support (Ollama)

Run strategies against local models via Ollama for zero-cost experimentation.

**What it involves:**
- New LLM provider that targets the Ollama API (OpenAI-compatible)
- Configurable endpoint URL
- Model selection from locally available models
- No web search capability (local models don't have this)

**Pros:**
- Zero marginal cost per execution -- users can run hundreds of experiments freely
- Enables experimentation on strategy prompts without burning API credits
- Ollama's API is OpenAI-compatible, so implementation is straightforward
- Interesting research question: can smaller local models match cloud models for trading?

**Cons:**
- Local models (7B-70B) are significantly less capable than GPT-4o or Claude -- strategies may produce poor results and users may blame the app
- No web search means agents can't access current market news -- a major limitation for trading
- Requires users to install and manage Ollama separately
- Hardware requirements may be prohibitive for some users (need decent GPU for usable inference speed)

---

### 3.2 Multi-Provider Strategy Comparison

Run the same strategy prompt across different LLM providers/models simultaneously and compare recommendations.

**What it involves:**
- "Compare Models" action that runs the same portfolio context through 2-3 different models
- Side-by-side display of recommendations from each model
- Track which model's recommendations the user applies and their subsequent performance
- Over time, build a model leaderboard per strategy type

**Pros:**
- Directly answers "which model is best for my strategy?" -- a question every user has
- Surfaces interesting divergences in model reasoning
- Leverages existing multi-provider architecture

**Cons:**
- Multiplies API costs by the number of models compared
- Models may produce different ticker formats or reasoning structures, making comparison noisy
- The "better model" may depend heavily on the specific strategy prompt, so results may not generalize

---

### 3.3 Cryptocurrency Support

Enable crypto-only portfolios as a separate asset class (no mixing with stocks).

**What it involves:**
- yfinance already supports crypto tickers (`BTC-USD`, `ETH-USD`, etc.) -- no new data source needed
- Add `asset_class` field to portfolio config: `stocks` or `crypto` (no mixed mode)
- Crypto portfolios use crypto-specific prompts, UI labels ("units" not "shares"), and benchmarks (BTC not S&P 500)
- Skip stock-specific context (earnings, SEC filings, insider trades) for crypto portfolios

**Pros:**
- Clean separation avoids complexity of mixed portfolios
- Expands experimentation surface -- crypto markets behave very differently than equities
- Zero additional infrastructure cost (yfinance provides the data)
- Interesting test case for LLM strategies: can they handle 24/7 volatile markets?

**Cons:**
- Crypto lacks fundamental data (no P/E, no earnings, no SEC filings) -- agents have less context
- Higher volatility may cause strategies to look worse (larger drawdowns, more noise)
- Need separate prompt templates for crypto strategies
- Fractional unit handling (0.00001 BTC display formatting)

---

## Phase 4: Collaboration & Persistence

Features for users who want to share findings or run longer experiments.

### 4.2 Execution Notes & Annotations

Let users attach notes to specific executions, trades, or time periods.

**What it involves:**
- Free-text note field on execution log entries
- Ability to tag time periods ("Fed rate decision", "earnings season")
- Notes visible in execution replay and performance charts

**Pros:**
- Turns the app into a proper research journal
- Helps users correlate strategy performance with external events
- Lightweight -- just a text field on existing data structures

**Cons:**
- Users rarely write notes unless forced to -- feature may go unused
- Annotations on charts add UI complexity for marginal benefit
- Qualitative notes don't help with quantitative analysis

---

## Explicitly Not on This Roadmap

Features considered and rejected, with reasoning.

### Backtesting
LLMs are not deterministic snapshots. You cannot meaningfully execute an LLM "as of March 2024" -- it will use its current knowledge regardless. Any backtest would test the LLM's ability to pretend it doesn't know the future, not its actual predictive capability. The results would be misleading.

### Broker Integration
The application is a simulation playground. Real money execution introduces regulatory, liability, and reliability requirements that fundamentally change the project's nature. Users who want to act on signals can do so manually through their own broker.

### Real-Time Streaming / WebSocket Data
yfinance provides delayed data for free. Real-time feeds cost money and are unnecessary for strategies that operate on daily/weekly/monthly cadences. The juice isn't worth the squeeze.

### Social Features (User Accounts, Leaderboards, Forums)
This is a local application. Adding multi-user infrastructure (auth, database, hosting) to support social features would be a different product entirely.

### Custom Technical Indicators
The current RSI/MA/volume indicators give agents sufficient technical context. Users who want exotic indicators are better served by specialized tools. Adding a custom indicator builder would be scope creep.

### Agentic Strategy Templates
Strategy design is the user's responsibility. Pre-built "winning strategies" would bias experimentation and set false expectations. The existing example portfolios are sufficient starting points.

### Mobile App
The Vue.js frontend is fully responsive with mobile-first design and works excellently on mobile browsers. A native mobile app would be a massive investment for an application that's fundamentally about reading dense financial data on a screen.
