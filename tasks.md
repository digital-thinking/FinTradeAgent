# Implementation Tasks

Detailed implementation plans for ROADMAP.md features.

---

## Phase 1: Experiment Infrastructure

### 1.2 Portfolio Cloning & Reset

**Status:** Completed

**Goal:** Enable A/B testing of strategies by cloning portfolios and resetting them to initial state.

#### Implementation Plan

**1. Add clone/reset functions to PortfolioService** (`src/fin_trade/services/portfolio.py`)

```python
def clone_portfolio(self, source_name: str, new_name: str, include_state: bool = False) -> PortfolioConfig:
    """
    Clone a portfolio configuration.
    - Copy YAML config with new name
    - If include_state=True, also copy the state JSON
    - If include_state=False, new portfolio starts fresh (no state file)
    """

def reset_portfolio(self, name: str, archive: bool = True) -> None:
    """
    Reset portfolio to initial state.
    - If archive=True, move current state to data/state/archive/{name}_{timestamp}.json
    - Delete or recreate state file (cash = initial_amount, holdings = [], trades = [])
    """
```

**2. Add UI controls** (`src/fin_trade/pages/portfolio_detail.py`)

- Add "Clone" button in portfolio header area
  - Opens modal/expander with:
    - Text input for new name (validate: no duplicates, valid filename)
    - Checkbox: "Include current state (holdings & trades)"
    - Clone button
  - On success: redirect to new portfolio detail page

- Add "Reset" button (with warning styling)
  - Opens confirmation dialog
  - Shows what will be lost: X trades, Y holdings, $Z current value
  - Checkbox: "Archive current state before reset" (default: checked)
  - Reset button

**3. Archive directory structure**

```
data/
├── state/
│   ├── archive/                    # New directory
│   │   └── {name}_{timestamp}.json # Archived states
│   └── {name}.json                 # Active states
```

**4. Add tests** (`tests/test_portfolio_service.py`)

- `test_clone_portfolio_config_only` - Clone without state
- `test_clone_portfolio_with_state` - Clone with state
- `test_clone_portfolio_duplicate_name_error` - Reject duplicate names
- `test_reset_portfolio_with_archive` - Reset and verify archive created
- `test_reset_portfolio_no_archive` - Reset without archiving
- `test_reset_portfolio_preserves_config` - Config unchanged after reset

#### Files to Modify

| File | Changes |
|------|---------|
| `src/fin_trade/services/portfolio.py` | Add `clone_portfolio()`, `reset_portfolio()` |
| `src/fin_trade/pages/portfolio_detail.py` | Add Clone/Reset UI controls |
| `tests/test_portfolio_service.py` | Add clone/reset tests |

#### Edge Cases

- Clone name conflicts with existing portfolio
- Clone/reset while portfolio has pending (unapplied) trades in execution log
- Reset portfolio that has never been executed (no state file exists)
- Invalid characters in clone name (spaces, special chars)

---

### 2.1 Strategy Benchmarking

**Status:** Completed

**Goal:** Compare portfolio performance against S&P 500 and other portfolios.

#### Implementation Plan

**1. Add benchmark data fetching** (`src/fin_trade/services/stock_data.py`)

```python
def get_benchmark_performance(self, symbol: str = "SPY", start_date: date, end_date: date) -> pd.DataFrame:
    """
    Get benchmark total return series.
    Returns DataFrame with columns: date, price, cumulative_return
    Uses existing caching infrastructure.
    """
```

**2. Add portfolio comparison service** (`src/fin_trade/services/comparison.py` - new file)

```python
class ComparisonService:
    def get_normalized_returns(self, portfolio_names: list[str], start_date: date = None) -> pd.DataFrame:
        """
        Get normalized (rebased to 100) return series for multiple portfolios.
        Aligns to common start date (latest first trade across all portfolios).
        """

    def calculate_metrics(self, portfolio_name: str, benchmark_symbol: str = "SPY") -> dict:
        """
        Calculate comparison metrics:
        - Alpha (excess return vs benchmark)
        - Beta (correlation with benchmark)
        - Sharpe ratio (return / volatility)
        - Max drawdown
        - Win rate (% of trades profitable)
        """
```

**3. Update performance chart** (`src/fin_trade/pages/portfolio_detail.py`)

- Add toggle: "Show S&P 500 benchmark"
- When enabled, overlay SPY normalized return on the chart
- Add secondary y-axis or normalize both to percentage returns

**4. Add comparison page** (`src/fin_trade/pages/comparison.py` - new file)

- Multi-select: choose 2+ portfolios to compare
- Normalized performance chart (all rebased to 100 at start)
- Metrics table side-by-side:
  | Metric | Portfolio A | Portfolio B | S&P 500 |
  |--------|-------------|-------------|---------|
  | Total Return | +15% | +8% | +12% |
  | Sharpe Ratio | 1.2 | 0.8 | 1.0 |
  | Max Drawdown | -8% | -15% | -10% |
  | Win Rate | 65% | 45% | N/A |

**5. Update navigation** (`src/fin_trade/app.py`)

- Add "Compare" page to sidebar navigation

#### Files to Create/Modify

| File | Changes |
|------|---------|
| `src/fin_trade/services/stock_data.py` | Add `get_benchmark_performance()` |
| `src/fin_trade/services/comparison.py` | New file: ComparisonService |
| `src/fin_trade/pages/portfolio_detail.py` | Add benchmark overlay toggle |
| `src/fin_trade/pages/comparison.py` | New file: comparison page |
| `src/fin_trade/app.py` | Add comparison page to navigation |
| `tests/test_comparison_service.py` | New file: comparison tests |

#### Edge Cases

- Portfolio with no trades yet (can't calculate metrics)
- Portfolios with very different start dates (normalization challenges)
- Benchmark data unavailable for date range
- Division by zero in Sharpe calculation (zero volatility)

---

### 2.2 Execution Replay

**Status:** Not Started

**Goal:** Browse past executions with full context and post-execution outcomes.

#### Implementation Plan

**1. Enhance ExecutionLogService** (`src/fin_trade/services/execution_log.py`)

```python
def get_execution_with_context(self, execution_id: int) -> dict:
    """
    Get full execution record including:
    - Original recommendations
    - Which were applied/rejected
    - Portfolio state at time of execution
    - Market context (from log file if available)
    """

def get_recommendation_outcomes(self, execution_id: int) -> list[dict]:
    """
    For each recommendation in an execution:
    - Get the recommended ticker and action
    - Get price at recommendation time
    - Get current price (or price at sell if position closed)
    - Calculate hypothetical P/L if recommendation was followed
    - Calculate actual P/L if recommendation was applied
    """
```

**2. Add execution history tab** (`src/fin_trade/pages/portfolio_detail.py`)

- New tab: "Execution History" (rename current "Trade History" to "Trade Log")
- Timeline view of executions:
  - Date/time
  - Model used
  - # recommendations made
  - # applied / # rejected
  - Quick outcome indicator (green/red based on subsequent performance)

**3. Execution detail view** (expandable or modal)

- Show for each execution:
  - Full agent reasoning
  - Each recommendation with:
    - Ticker, action, quantity
    - Price at recommendation
    - Current/exit price
    - Outcome: +X% / -X%
    - Status: Applied / Rejected
  - Debate transcript (if debate mode)
  - Research gathered
  - Tokens used, duration

**4. Parse markdown logs** (`src/fin_trade/services/execution_log.py`)

- The markdown log files contain rich context not in SQLite
- Add function to parse and extract sections from log files:
  - Research results
  - Analysis/debate transcript
  - Full prompt

#### Files to Modify

| File | Changes |
|------|---------|
| `src/fin_trade/services/execution_log.py` | Add context and outcome functions |
| `src/fin_trade/pages/portfolio_detail.py` | Add execution history tab and detail view |
| `tests/test_execution_log.py` | Add tests for new functions |

#### Edge Cases

- Log file missing or corrupted
- Recommendation for ticker that no longer exists
- Price data unavailable for outcome calculation
- Very old executions where log format may differ

---

### 3.1 Local LLM Support (Ollama)

**Status:** Not Started

**Goal:** Enable zero-cost experimentation with local models.

#### Implementation Plan

**1. Add Ollama provider** (`src/fin_trade/services/llm_provider.py`)

```python
class OllamaProvider(LLMProvider):
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.client = OpenAI(base_url=f"{base_url}/v1", api_key="ollama")  # Ollama uses OpenAI-compatible API

    def generate(self, messages: list[dict], **kwargs) -> LLMResponse:
        # Same as OpenAI provider but:
        # - No web search support
        # - Different token counting
        # - Handle connection errors gracefully (Ollama not running)

    @property
    def supports_web_search(self) -> bool:
        return False
```

**2. Update provider factory** (`src/fin_trade/services/llm_provider.py`)

```python
def create_provider(provider_name: str, model: str, **kwargs) -> LLMProvider:
    if provider_name == "ollama":
        base_url = kwargs.get("ollama_base_url", "http://localhost:11434")
        return OllamaProvider(model=model, base_url=base_url)
    # ... existing providers
```

**3. Update portfolio config model** (`src/fin_trade/models/portfolio.py`)

```python
@dataclass
class PortfolioConfig:
    # ... existing fields
    ollama_base_url: str = "http://localhost:11434"  # Only used if llm_provider == "ollama"
```

**4. Handle no web search in agents** (`src/fin_trade/agents/nodes/research.py`)

- Check if provider supports web search
- If not, skip web search step and use only:
  - Cached market data
  - Technical indicators
  - Holdings context
- Add warning in UI that research capabilities are limited

**5. Add Ollama health check** (`src/fin_trade/services/llm_provider.py`)

```python
def check_ollama_status(base_url: str = "http://localhost:11434") -> dict:
    """
    Check if Ollama is running and list available models.
    Returns: {"status": "ok"|"error", "models": [...], "error": "..."}
    """
```

**6. UI for Ollama setup** (`src/fin_trade/pages/system_health.py`)

- Show Ollama connection status
- List available local models
- Link to Ollama installation instructions if not running

#### Files to Modify

| File | Changes |
|------|---------|
| `src/fin_trade/services/llm_provider.py` | Add OllamaProvider, health check |
| `src/fin_trade/models/portfolio.py` | Add ollama_base_url field |
| `src/fin_trade/agents/nodes/research.py` | Handle no web search |
| `src/fin_trade/pages/system_health.py` | Add Ollama status display |
| `tests/test_llm_provider.py` | Add Ollama provider tests (mocked) |

#### Edge Cases

- Ollama not installed or not running
- Model not downloaded locally
- Connection timeout (slow inference)
- Model doesn't support the message format
- Very long responses from verbose local models

---

### 4.2 Execution Notes & Annotations

**Status:** Not Started

**Goal:** Let users attach notes to executions and time periods.

#### Implementation Plan

**1. Add notes table to SQLite** (`src/fin_trade/services/execution_log.py`)

```sql
CREATE TABLE IF NOT EXISTS execution_notes (
    id INTEGER PRIMARY KEY,
    execution_id INTEGER,           -- NULL if note is standalone (date-based)
    portfolio_name TEXT NOT NULL,
    note_date DATE NOT NULL,
    note_text TEXT NOT NULL,
    tags TEXT,                      -- JSON array of tags
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES execution_logs(id)
);
```

**2. Add note service methods** (`src/fin_trade/services/execution_log.py`)

```python
def add_note(self, portfolio_name: str, note_text: str,
             execution_id: int = None, note_date: date = None,
             tags: list[str] = None) -> int:
    """Add a note to an execution or date."""

def get_notes(self, portfolio_name: str,
              start_date: date = None, end_date: date = None) -> list[dict]:
    """Get notes for a portfolio, optionally filtered by date range."""

def update_note(self, note_id: int, note_text: str = None, tags: list[str] = None):
    """Update an existing note."""

def delete_note(self, note_id: int):
    """Delete a note."""
```

**3. Add note UI in execution history** (`src/fin_trade/pages/portfolio_detail.py`)

- "Add Note" button next to each execution
- Expandable text area for note content
- Tag input (comma-separated or chip-style)
- Common tags as quick-select: "Earnings", "Fed Decision", "Market Correction", "Strategy Tweak"

**4. Show notes on performance chart** (`src/fin_trade/pages/portfolio_detail.py`)

- Add markers/annotations on the chart at note dates
- Hover to see note preview
- Click to expand full note

**5. Notes panel in portfolio detail**

- Collapsible sidebar or tab showing all notes
- Filter by tag
- Search notes

#### Files to Modify

| File | Changes |
|------|---------|
| `src/fin_trade/services/execution_log.py` | Add notes table and CRUD methods |
| `src/fin_trade/pages/portfolio_detail.py` | Add note UI in execution history and chart |
| `tests/test_execution_log.py` | Add note CRUD tests |

#### Edge Cases

- Note on date with no execution
- Very long notes (truncate in display, show full on expand)
- Special characters in notes/tags
- Migration: existing databases need new table

---

### 3.3 Cryptocurrency Support

**Status:** Completed

**Goal:** Enable crypto-only portfolios as a separate asset class (no mixing with stocks).

#### Implementation Plan

**1. Add asset class to portfolio config** (`src/fin_trade/models/portfolio.py`)

```python
from enum import Enum

class AssetClass(str, Enum):
    STOCKS = "stocks"
    CRYPTO = "crypto"

@dataclass
class PortfolioConfig:
    # ... existing fields
    asset_class: AssetClass = AssetClass.STOCKS
```

**2. Update Holding model for fractional units** (`src/fin_trade/models/portfolio.py`)

```python
@dataclass
class Holding:
    ticker: str
    name: str
    quantity: float  # Change from int to float for fractional crypto
    avg_price: float
    # ... existing fields
```

**3. Add crypto ticker validation** (`src/fin_trade/services/security.py`)

```python
CRYPTO_SUFFIXES = ["-USD", "-EUR", "-GBP"]

def is_crypto_ticker(self, ticker: str) -> bool:
    """Check if ticker is a cryptocurrency (e.g., BTC-USD, ETH-USD)."""
    return any(ticker.upper().endswith(suffix) for suffix in CRYPTO_SUFFIXES)

def validate_ticker_for_asset_class(self, ticker: str, asset_class: AssetClass) -> bool:
    """Ensure ticker matches portfolio's asset class. Raises ValueError if mismatch."""
    is_crypto = self.is_crypto_ticker(ticker)
    if asset_class == AssetClass.CRYPTO and not is_crypto:
        raise ValueError(f"Ticker {ticker} is not a crypto ticker. Use format like BTC-USD.")
    if asset_class == AssetClass.STOCKS and is_crypto:
        raise ValueError(f"Ticker {ticker} is a crypto ticker. This portfolio only allows stocks.")
    return True
```

**4. Skip stock-specific market data for crypto** (`src/fin_trade/services/market_data.py`)

```python
def get_holdings_context(self, holdings: list, asset_class: AssetClass) -> dict:
    """
    Get market context appropriate for the asset class.
    - Stocks: earnings, SEC filings, insider trades
    - Crypto: skip all (not applicable)
    """
    if asset_class == AssetClass.CRYPTO:
        return {}  # No fundamental data for crypto
    # ... existing stock logic
```

**5. Separate prompt template for crypto** (`src/fin_trade/prompts/crypto_agent.py` - new file)

```python
CRYPTO_SYSTEM_PROMPT = """
You are a cryptocurrency trading agent.

IMPORTANT RULES:
- Only trade cryptocurrencies (BTC-USD, ETH-USD, SOL-USD, etc.)
- Always use the -USD suffix for tickers
- No fundamental analysis available (no earnings, no SEC filings)
- Focus on: technical analysis, market sentiment, news, on-chain metrics

{strategy_prompt}

Current Holdings:
{holdings_context}

Available Cash: ${cash:.2f}
"""
```

**6. Add appropriate benchmark for crypto** (`src/fin_trade/services/comparison.py`)

```python
def get_default_benchmark(self, asset_class: AssetClass) -> str:
    """Return appropriate benchmark for asset class."""
    if asset_class == AssetClass.CRYPTO:
        return "BTC-USD"
    return "SPY"
```

**7. Update UI for crypto portfolios** (`src/fin_trade/pages/portfolio_detail.py`)

```python
def get_unit_label(asset_class: AssetClass) -> str:
    return "units" if asset_class == AssetClass.CRYPTO else "shares"

def format_quantity(quantity: float, asset_class: AssetClass) -> str:
    if asset_class == AssetClass.CRYPTO:
        return f"{quantity:.8f}".rstrip('0').rstrip('.')
    return str(int(quantity))
```

**8. Add crypto portfolio example** (`data/portfolios/crypto_momentum.yaml`)

```yaml
name: "Crypto Momentum"
asset_class: crypto
strategy_prompt: |
  You are a cryptocurrency momentum trader.

  TARGET: Large-cap cryptocurrencies (BTC, ETH, SOL, AVAX, etc.)

  SIGNALS:
    - BUY: Breaking resistance with volume, positive sentiment shift
    - SELL: Breaking support, momentum reversal, negative news

  Always use -USD suffix (e.g., BTC-USD, ETH-USD).

initial_amount: 10000.0
num_initial_trades: 3
trades_per_run: 2
run_frequency: daily
llm_provider: openai
llm_model: gpt-5.2
agent_mode: langgraph
```

#### Files to Create/Modify

| File | Changes |
|------|---------|
| `src/fin_trade/models/portfolio.py` | Add `AssetClass` enum, change `quantity` to float |
| `src/fin_trade/services/security.py` | Add `is_crypto_ticker()`, `validate_ticker_for_asset_class()` |
| `src/fin_trade/services/market_data.py` | Skip stock-specific data for crypto |
| `src/fin_trade/services/comparison.py` | Add `get_default_benchmark()` |
| `src/fin_trade/prompts/crypto_agent.py` | New file: crypto-specific prompt template |
| `src/fin_trade/pages/portfolio_detail.py` | Update UI labels and quantity formatting |
| `data/portfolios/crypto_momentum.yaml` | New example crypto strategy |
| `tests/test_security_service.py` | Add crypto validation tests |

#### Edge Cases

- Agent outputs ticker without -USD suffix (validation should catch and reject)
- Extremely small quantities (0.00000001 BTC) -- display formatting
- 24/7 market means "daily" execution timing is arbitrary
- Stablecoins (USDT-USD, USDC-USD) -- technically crypto but effectively cash

#### Migration Considerations

- Existing portfolios default to `asset_class: stocks` (backward compatible)
- Existing holdings with integer quantities still work (float accepts int)
- No database migration needed (state is JSON)

---

## Implementation Priority

Recommended order based on value and dependencies:

1. **1.2 Portfolio Cloning & Reset** - Quick win, enables experimentation
2. **2.1 Strategy Benchmarking** - Core value for understanding performance
3. **3.3 Cryptocurrency Support** - Expands experimentation surface, low effort (yfinance already works)
4. **3.1 Local LLM Support (Ollama)** - Enables free experimentation
5. **2.2 Execution Replay** - Deep insight into agent decisions
6. **4.2 Execution Notes** - Nice-to-have, low priority
