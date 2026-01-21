# Agentic Trade Assistant

A Streamlit application for managing AI-powered stock portfolios with LLM trading recommendations based on the **Semantic Alpha** framework.

## Overview

This application exploits "interpretive latency" - the time it takes for market consensus to fully digest nuanced qualitative information. Unlike high-frequency strategies that require colocation and proprietary data feeds, these strategies leverage LLM reasoning capabilities to identify pricing inefficiencies in unstructured data.

## Features

- **Portfolio Management**: Create and manage multiple portfolios with different strategies
- **LLM-Powered Analysis**: OpenAI (GPT-4o, GPT-5.x) and Anthropic (Claude) support
- **Web Search Integration**: Real-time market data access via LLM web search capabilities
- **Real-Time Stock Data**: Yahoo Finance integration for price fetching
- **Security Management**: Automatic ticker/ISIN resolution with persistent storage
- **Trade Validation**: Pre-execution validation for cash availability and holdings
- **Interactive UI**: Portfolio overview, holdings tracking, performance charts, trade history
- **Execution Tracking**: Visual indicators for overdue portfolios, trade acceptance workflow
- **Debug Logging**: All LLM prompts and responses logged for analysis

## Installation

```bash
# Install dependencies
poetry install
```

## Configuration

Create a `.env` file in the project root:

```ini
# OpenAI API Key (required for OpenAI-based strategies)
OPENAI_API_KEY=your-openai-api-key-here

# Anthropic API Key (required for Claude-based strategies)
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

Get your API keys:
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/

## Usage

```bash
poetry run streamlit run src/fin_trade/app.py
```

The app runs on http://localhost:8501 by default.

## Trading Strategies

The application includes six distinct portfolio strategies:

### 1. Earnings Beat & Raise (PEAD)

**File**: `data/portfolios/earnings_momentum.yaml`

Exploits Post-Earnings Announcement Drift by identifying "Double Surprise" events:
- Beat estimates on revenue AND earnings
- Raised forward guidance
- CEO confidence scoring from earnings call analysis

**Signal**: Buy when Beat + Raise + High CEO Confidence; Sell on lowered guidance.

### 2. Insider Conviction

**File**: `data/portfolios/insider_conviction.yaml`

Tracks insider trading patterns to identify high-conviction opportunities:
- Cluster buying detection (multiple insiders buying simultaneously)
- Dollar amount significance analysis
- Filtering noise from routine transactions

### 3. Overreaction Arbitrage

**File**: `data/portfolios/overreaction_arbitrage.yaml`

Identifies market overreactions to news events:
- Gap analysis after significant price moves
- Sentiment vs fundamentals divergence
- Mean reversion opportunities

### 4. Seasonal Rotation

**File**: `data/portfolios/seasonal_rotation.yaml`

Sector rotation based on historical seasonal patterns:
- Monthly sector performance analysis
- Tax-loss harvesting opportunities
- Holiday/event-driven patterns

### 5. Squeeze Hunter

**File**: `data/portfolios/squeeze_hunter.yaml`

Identifies potential short squeeze candidates:
- High short interest analysis
- Days to cover calculations
- Catalyst identification

### 6. Take-Private Arbitrage

**File**: `data/portfolios/takeover_arbitrage.yaml`

Merger arbitrage focused on announced take-private/delisting deals:
- Spread calculation (offer price vs current price)
- Deal completion probability scoring (financing, regulatory, shareholder approval)
- Downside risk assessment if deal fails
- Uses web search to verify current deal status

**Signal**: Buy when spread > 3% with probability > 7/10; Sell when deal closes or concerns emerge.

## Project Structure

```
src/fin_trade/
├── app.py                    # Main Streamlit entry point
├── models/
│   ├── portfolio.py          # Holding, Trade, PortfolioConfig, PortfolioState
│   └── agent.py              # TradeRecommendation, AgentRecommendation
├── services/
│   ├── stock_data.py         # Yahoo Finance integration with caching
│   ├── portfolio.py          # Portfolio CRUD and calculations
│   ├── security.py           # Ticker/ISIN management and price fetching
│   ├── isin_lookup.py        # ISIN lookup interface
│   └── agent.py              # LLM invocation with web search support
├── pages/
│   ├── overview.py           # Portfolio tiles grid
│   └── portfolio_detail.py   # Holdings, Performance, Agent Execution, History
└── components/
    ├── portfolio_tile.py     # Reusable portfolio card with mini charts
    └── trade_display.py      # Trade recommendation UI with validation

data/
├── portfolios/               # Portfolio YAML configurations
├── state/                    # Portfolio state JSON (holdings, trades)
├── stock_data/               # Security data JSON cache (ticker, ISIN, name)
└── logs/                     # Agent prompt/response logs for debugging
```

## Portfolio Configuration

Create a YAML file in `data/portfolios/`:

```yaml
name: "Strategy Name"
strategy_prompt: |
  Your detailed strategy prompt here...
  Use Chain-of-Thought reasoning...
initial_amount: 10000.0
num_initial_trades: 5
trades_per_run: 3
run_frequency: weekly  # daily/weekly/monthly
llm_provider: openai   # openai or anthropic
llm_model: gpt-4o      # gpt-4o, gpt-5.2, claude-sonnet-4-20250514, etc.
```

## Supported Models

### OpenAI
- `gpt-4o` → automatically uses `gpt-4o-search-preview` for web access
- `gpt-4o-mini` → automatically uses `gpt-4o-mini-search-preview`
- `gpt-5`, `gpt-5.1`, `gpt-5.2` → automatically uses `gpt-5-search-api`

### Anthropic
- `claude-sonnet-4-20250514`
- `claude-3-5-sonnet-20241022`
- Web search enabled via `web_search_20250305` tool

## Stock Support

The application supports **any publicly traded stock**:
- Enter ticker symbols (AAPL, MSFT, GOOGL, etc.)
- ISINs are automatically resolved via yfinance when available
- User can manually provide ISINs when not found
- Security data (ticker, ISIN, name) is persisted to JSON files

## Key Design Decisions

1. **LLMs Choose Stocks Freely**: No hardcoded stock list - agents recommend any ticker
2. **Web Search Enabled**: Agents can access real-time market data, news, and prices
3. **Human-in-the-Loop**: Agent generates recommendations, user accepts/rejects
4. **Trade Validation**: Validates cash availability and holdings before execution
5. **Persistent Storage**: Security info and portfolio state stored in JSON files
6. **Debug Logging**: All LLM interactions logged to `data/logs/`

## Risk Management

- **Human-in-the-Loop**: AI generates signals, human verifies and executes
- **Pre-Trade Validation**: Insufficient cash/holdings flagged before execution
- **Zero-Calc Rule**: LLMs used for reasoning, not complex calculations
- **Verification**: Prompts designed to cite sources for hallucination detection

## Dependencies

- `streamlit` - Web UI framework
- `yfinance` - Stock data fetching
- `openai` - OpenAI API
- `anthropic` - Claude API
- `python-dotenv` - Environment configuration
- `pyyaml` - Configuration parsing
- `plotly` - Interactive charts
- `pandas` - Data manipulation
- `requests` - HTTP client

---

## Future Improvements and Ideas

### Short-Term Enhancements

- [ ] **Backtesting Framework**: Add ability to backtest strategies against historical data
- [ ] **Portfolio Analytics Dashboard**: Sharpe ratio, max drawdown, beta, sector allocation charts
- [ ] **Trade Journaling**: Notes and tags for each trade decision
- [ ] **Alert System**: Email/push notifications for overdue portfolios or significant price moves
- [ ] **CSV/Excel Export**: Export trade history and portfolio performance data

### Strategy Improvements

- [ ] **Multi-Timeframe Analysis**: Combine daily/weekly/monthly signals
- [ ] **Sentiment Scoring**: Track sentiment over time for trending analysis
- [ ] **News Aggregation**: Dedicated news feed per portfolio/stock
- [ ] **Earnings Calendar Integration**: Automatic alerts before earnings dates
- [ ] **Options Strategy Support**: Covered calls, protective puts for hedging

### Technical Enhancements

- [ ] **Real ISIN Lookup**: Integrate with paid ISIN database (OpenFIGI Pro, Bloomberg)
- [ ] **Multi-Currency Support**: Handle EUR, GBP portfolios with FX conversion
- [ ] **Fractional Shares**: Support partial share quantities
- [ ] **Broker Integration**: Connect to Interactive Brokers, Alpaca for live execution
- [ ] **Rate Limiting**: Respect API rate limits for yfinance and LLM providers
- [ ] **Caching Layer**: Redis/SQLite for better performance with large portfolios

### Agent Improvements

- [ ] **Multi-Agent Debates**: Implement adversarial bull/bear analysis
- [ ] **Chain-of-Thought Logging**: Store intermediate reasoning steps
- [ ] **Confidence Scoring**: Agent provides confidence level for each trade
- [ ] **Position Sizing Recommendations**: Kelly criterion or risk-parity suggestions
- [ ] **Stop-Loss Suggestions**: Automatic stop-loss levels based on volatility

### UI/UX Improvements

- [ ] **Dark Mode**: Theme toggle for the interface
- [ ] **Mobile Responsive**: Better mobile/tablet layout
- [ ] **Drag-and-Drop Reordering**: Reorder portfolios on overview page
- [ ] **Keyboard Shortcuts**: Quick actions for power users
- [ ] **Portfolio Comparison**: Side-by-side performance comparison

### Data & Analytics

- [ ] **Correlation Matrix**: Cross-portfolio correlation analysis
- [ ] **Risk Metrics**: VaR, Expected Shortfall calculations
- [ ] **Benchmark Comparison**: Compare against S&P 500, NASDAQ
- [ ] **Tax Lot Tracking**: FIFO/LIFO cost basis for tax reporting
- [ ] **Dividend Tracking**: Track and reinvest dividends

### Advanced Features

- [ ] **Paper Trading Mode**: Simulated execution without real money
- [ ] **Strategy Marketplace**: Share/import community strategies
- [ ] **LLM Fine-Tuning**: Custom models trained on financial data
- [ ] **Webhook Support**: Trigger agents via external events
- [ ] **Multi-User Support**: Authentication and user-specific portfolios

### Research Ideas

- [ ] **Sentiment History Charts**: Visualize LLM sentiment over time
- [ ] **Trade Attribution**: Analyze which strategy aspects drive returns
- [ ] **Regime Detection**: Automatic market regime classification
- [ ] **Alternative Data**: Social media sentiment, satellite data, web traffic
- [ ] **Reinforcement Learning**: Agent learns from past trade outcomes

---

## Theoretical Foundation

This application is based on the **Semantic Alpha** research framework:

- **Lopez-Lira & Tang (2023)**: Demonstrated GPT-4's ability to predict stock returns from sentiment analysis
- **Li et al. (2024)**: Validated LLM performance against human analysts
- **AlphaAgents (2025)**: Multi-agent debate frameworks for bias elimination

**Key Insight**: The next frontier of alpha generation lies not in speed of data transmission, but in depth of data reasoning. LLMs can process unstructured textual data (earnings calls, filings, news) to identify pricing inefficiencies before market absorption.

## License

MIT
