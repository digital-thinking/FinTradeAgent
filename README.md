# Agentic Trade Assistant

A Streamlit application for managing agentic stock portfolios with LLM-powered trading recommendations based on the **Semantic Alpha** framework.

## Overview

This application exploits "interpretive latency" - the time it takes for market consensus to fully digest nuanced qualitative information. Unlike high-frequency strategies that require colocation and proprietary data feeds, these strategies leverage LLM reasoning capabilities to identify pricing inefficiencies in unstructured data.

## Features

- **Portfolio Management**: Create and manage multiple portfolios with different strategies
- **LLM-Powered Analysis**: OpenAI (GPT-4o) by default, with Anthropic (Claude) support
- **Real-Time Stock Data**: Yahoo Finance integration with local caching
- **Interactive UI**: Portfolio overview, holdings tracking, performance charts, trade history
- **Execution Tracking**: Visual indicators for overdue portfolios, trade acceptance workflow

## Installation

```bash
# Install dependencies
poetry install
```

## Configuration

Create a `.env` file in the project root (copy from `.env.example`):

```ini
# OpenAI API Key (required - used by default)
OPENAI_API_KEY=your-openai-api-key-here

# Anthropic API Key (optional - for Claude-based strategies)
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

Get your API keys:
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/

## Usage

```bash
poetry run streamlit run src/fin_trade/app.py
```

## Trading Strategies

The application implements five distinct strategies from the Semantic Alpha research framework:

### 1. Buffett-Graham Value Moat

**File**: `data/portfolios/conservative.yaml`

Mechanizes Warren Buffett and Benjamin Graham's investment philosophy using Chain-of-Thought reasoning:

- **Step 1**: Moat Assessment (Pricing Power, Switching Costs, Network Effects, Cost Advantage)
- **Step 2**: Financial Fortress Inspection (Debt levels, FCF consistency, Red Flags)
- **Step 3**: Management & Capital Allocation (Candor Test, Diworsification check)
- **Step 4**: Valuation Logic (Wonderful Company at Fair Price vs Fair Company at Wonderful Price)

**Best for**: Conservative investors seeking capital preservation with steady income.

### 2. Sentiment Drift Alpha (PEAD)

**File**: `data/portfolios/growth.yaml`

Exploits Post-Earnings Announcement Drift by analyzing market underreaction to complex news:

- **Unexpectedness**: Surprise factor relative to consensus
- **Fundamental Impact**: DCF model implications
- **Linguistic Clarity**: Ambiguity assessment (complex good news = longer drift window)

**Key Insight**: Targets "Hidden Bullish" situations where markets sell on headlines but fundamentals are positive.

### 3. Forensic Tech Analyst

**File**: `data/portfolios/tech_focus.yaml`

Psycho-linguistic analysis to detect management credibility through:

- **Evasion Detection**: Vague responses to specific questions
- **Sentiment Divergence**: Q&A tone vs prepared remarks
- **Keyword Density**: Defensive words (headwinds, uncertainty) vs Offensive words (growth, acceleration)
- **Executive Credibility Scoring**: 0-100 scale determining trade signals

**Special Focus**: Critical for high-valuation growth stocks where executive hesitation signals multiple compression risk.

### 4. Adversarial Investment Committee

**File**: `data/portfolios/adversarial_debate.yaml`

Multi-agent simulation to eliminate cognitive biases (Confirmation Bias, Anchoring, Overconfidence):

| Persona | Role | Focus |
|---------|------|-------|
| **Aggressive Bull** | Portfolio Manager | Growth, TAM, Innovation, Upside optionality |
| **Forensic Bear** | Risk Officer | Valuation, Accounting, Macro risks, Capital preservation |
| **CIO** | Final Decision | Asymmetric risk/reward synthesis |

**Debate Protocol**: 4 rounds (Pitch → Attack → Rebuttal → Verdict)

### 5. Macro Regime Navigator

**File**: `data/portfolios/macro_regime.yaml`

Top-down sector rotation based on the Investment Clock framework:

| Phase | Conditions | Bullish Sectors | Bearish Sectors |
|-------|------------|-----------------|-----------------|
| **Reflation** | Growth↑ Inflation↓ | Tech, Consumer Discretionary | Defensives, Cash |
| **Overheat** | Growth↑ Inflation↑ | Commodities, Energy, Financials | Long-duration Tech |
| **Stagflation** | Growth↓ Inflation↑ | Cash, Energy, Staples | Growth, Discretionary |
| **Deflation** | Growth↓ Inflation↓ | Quality Tech, Bonds, Utilities | Cyclicals, Banks |

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
│   └── agent.py              # LLM invocation (Anthropic/OpenAI)
├── pages/
│   ├── overview.py           # Portfolio tiles grid
│   └── portfolio_detail.py   # Holdings, Performance, Agent Execution, History
└── components/
    ├── portfolio_tile.py     # Reusable portfolio card
    └── trade_display.py      # Trade recommendation UI

data/
├── portfolios/               # Portfolio YAML configurations
├── state/                    # Portfolio state JSON (holdings, trades)
└── stock_data/               # Stock price CSV cache
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
llm_provider: openai   # openai (default) or anthropic
llm_model: gpt-4o      # gpt-4o, gpt-4-turbo, claude-sonnet-4-20250514, etc.
```

## Available Stocks

The application supports 20 pre-mapped ISINs:

| ISIN | Ticker | Company |
|------|--------|---------|
| US0378331005 | AAPL | Apple |
| US5949181045 | MSFT | Microsoft |
| US02079K3059 | GOOGL | Alphabet |
| US0231351067 | AMZN | Amazon |
| US88160R1014 | TSLA | Tesla |
| US67066G1040 | NVDA | NVIDIA |
| US30303M1027 | META | Meta |
| US4781601046 | JNJ | Johnson & Johnson |
| US91324P1021 | UNH | UnitedHealth |
| US7427181091 | PG | Procter & Gamble |
| US4592001014 | IBM | IBM |
| US1912161007 | KO | Coca-Cola |
| US7170811035 | PFE | Pfizer |
| US2546871060 | DIS | Disney |
| US0970231058 | BA | Boeing |
| US46625H1005 | JPM | JPMorgan Chase |
| US0605051046 | BAC | Bank of America |
| US92826C8394 | V | Visa |
| US5801351017 | MCD | McDonald's |
| US2855121099 | LLY | Eli Lilly |

## Theoretical Foundation

This application is based on the **Semantic Alpha** research framework:

- **Lopez-Lira & Tang (2023)**: Demonstrated GPT-4's ability to predict stock returns from sentiment analysis
- **Li et al. (2024)**: Validated LLM performance against human analysts
- **AlphaAgents (2025)**: Multi-agent debate frameworks for bias elimination

**Key Insight**: The next frontier of alpha generation lies not in speed of data transmission, but in depth of data reasoning. LLMs can process unstructured textual data (earnings calls, filings, news) to identify pricing inefficiencies before market absorption.

## Risk Management

- **Human-in-the-Loop**: AI generates signals, human verifies and executes
- **Zero-Calc Rule**: Never ask LLMs to calculate complex ratios - use them for reasoning only
- **Verification**: All prompts designed to cite sources for hallucination detection
- **Position Sizing**: Based on conviction levels from analysis

## Dependencies

- `streamlit` - Web UI framework
- `yfinance` - Stock data fetching
- `openai` - OpenAI API (default)
- `anthropic` - Claude API (optional)
- `python-dotenv` - Environment configuration
- `pyyaml` - Configuration parsing
- `plotly` - Interactive charts
- `pandas` - Data manipulation

## License

MIT
