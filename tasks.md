# Parallel Development Task Packages

**INSTRUCTIONS FOR AGENTS:**
1.  **Select a single package** to work on. Do not mix tasks from different packages to avoid merge conflicts.
2.  **Scope isolation**: Try to limit your changes to the files listed in the "Primary Files" section of your package.
3.  **Shared Resources**: If you must modify shared files (e.g., `app.py`, `services/__init__.py`), check if other active agents are modifying them.
4.  **New Files**: Prefer creating new files/modules over heavily modifying existing large files.
5.  **Marking Progress**: When you start a package, assume you own it until completion.
6.  **Atomic Commits**: After completing each individual task (bullet point) within a package, ask the user to commit the changes before moving to the next task. Do not accumulate multiple features in a single commit.

---

## 📦 Package A: Backend Architecture (Refactoring)
*Focus: Code structure, maintainability, and resilience.*
*Primary Files: `src/fin_trade/services/agent.py`, `src/fin_trade/services/llm_provider.py` (new), `src/fin_trade/prompts/` (new)*

- [ ] **Scheduled Execution**
    - Implement background job runner (e.g., APScheduler) to run agents automatically at defined intervals (daily/weekly).
    - Create a `SchedulerService` to manage job persistence and execution.
    - Add UI controls to enable/disable auto-execution per portfolio.

## 📦 Package F: Testing & Optimization
*Focus: Quality assurance, performance, and stability.*
*Primary Files: `tests/`, `src/fin_trade/services/stock_data.py`, `src/fin_trade/app.py`*

- [ ] **Asynchronous Execution**
    - Optimize backend processing to ensure UI responsiveness.


## 📦 Package I: Enhanced Holdings Context
*Focus: Improve agent decision quality by providing richer context about current holdings.*
*Primary Files: `src/fin_trade/services/stock_data.py`, `src/fin_trade/agents/nodes/`, `src/fin_trade/prompts/`*

### Problem Analysis (from Short Squeeze Hunter execution log)

The current agent context is missing critical information for making informed decisions:

1. **Holdings lack price history**: Only shows `current $1.74 (+0.0%)` - no trend data or chart context
2. **Research node gets minimal ticker context**: Just ticker symbols, no price levels or performance
3. **BUY candidates missing current prices**: Agent couldn't calculate position sizes because prices weren't provided
4. **No technical indicators**: RSI, volume trends, moving averages not available
5. **Short squeeze specific data missing**: Short interest %, days-to-cover, borrow fees not auto-fetched

### Implementation Plan

#### Task 1: Add Price History to Holdings Context
- [x] Extend `StockDataService` to fetch 30-day price history with daily OHLCV
- [x] Calculate key metrics: 5-day change, 30-day change, 52-week high/low distance
- [x] Format as compact chart summary for agent consumption (e.g., "↗ trending up 15% over 5 days")

#### Task 2: Add Technical Indicators
- [x] Calculate RSI (14-day) for holdings and watch candidates
- [x] Add volume analysis (avg volume, recent volume vs avg ratio)
- [x] Include moving average context (price vs 20-day MA, 50-day MA)
- [x] Add 52-week range position (e.g., "trading at 15% of 52-week range")

#### Task 3: Fetch Current Prices for BUY Candidates
- [x] ~~Moved to Package J Task 6~~

#### Task 5: Update Prompts with Rich Context
- [x] Update holdings section in prompts to show price history summary
- [x] Add technical indicator section when relevant to strategy

#### Task 6: Add Unit Tests
- [x] Test price history formatting
- [x] Test technical indicator calculations

---

## 📦 Package J: Consolidate yfinance Data Fetching & Remove ISINs
*Focus: Eliminate redundant API calls, reuse stored data, and simplify storage to use ticker symbols only.*
*Primary Files: `src/fin_trade/services/security.py`, `src/fin_trade/services/stock_data.py`, `src/fin_trade/services/market_data.py`, `src/fin_trade/models/`*

### Problem Analysis

**Issue 1: Redundant API Calls**
The codebase has **9 separate `yf.Ticker()` calls** across 3 services. Meanwhile, stored data files contain rich data that's largely unused.

**Issue 2: ISIN-based Storage is Unnecessary**
- Files are stored as `{ISIN}_data.json` but ISINs add complexity without benefit
- Many tickers have `UNKNOWN-{ticker}` ISINs anyway
- Tickers are the primary lookup key everywhere in the codebase
- yfinance uses tickers, not ISINs

**Stored but not being used:**
- `sharesShort`, `shortRatio`, `shortPercentOfFloat` - Short squeeze data
- `fiftyTwoWeekHigh`, `fiftyTwoWeekLow` - Already calculated 52w range
- `fiftyDayAverage`, `twoHundredDayAverage` - Moving averages
- `earningsTimestamp` - Earnings date
- `averageVolume`, `averageVolume10days` - Volume data
- `targetMeanPrice`, `recommendationKey` - Analyst ratings

**Current yf.Ticker() calls (redundant):**
1. `security.py:135` - lookup_ticker()
2. `security.py:200` - get_stock_info()
3. `security.py:236` - refresh_security_data()
4. `stock_data.py:97` - update_data() (fetches 365 days to calculate 52w range)
5. `market_data.py:160` - get_earnings_info()
6. `market_data.py:225` - get_insider_trades()
7. `market_data.py:295` - get_sec_filings()
8. `market_data.py:365,381` - get_macro_data()

### Implementation Plan

#### Task 0: Migrate Storage from ISIN to Ticker-based
- [ ] Rename data files from `{ISIN}_data.json` to `{TICKER}_data.json`
- [ ] Write migration script to rename existing files (preserve data)
- [ ] Update `SecurityService._get_data_file_path()` to use ticker instead of ISIN
- [ ] Update `SecurityService._load_persisted_securities()` to load by ticker
- [ ] Update `SecurityService._save_security_data()` to save by ticker
- [ ] Remove `_by_isin` cache dict (keep only `_by_ticker`)
- [ ] Remove `get_by_isin()` method
- [ ] Update `Holding` model: remove `isin` field (ticker is sufficient)
- [ ] Update `Trade` model: remove `isin` field
- [ ] Update `PortfolioService` to not require ISIN
- [ ] Update price CSV files to use `{TICKER}_prices.csv` (already does this)
- [ ] Clean up any ISIN references in UI components

#### Task 1: Extend SecurityService with Rich Data Methods
- [ ] Add `get_short_interest(ticker)` → returns {shares_short, short_ratio, short_percent_float}
- [ ] Add `get_52w_range(ticker)` → returns {high_52w, low_52w}
- [ ] Add `get_moving_averages(ticker)` → returns {ma_50, ma_200}
- [ ] Add `get_analyst_data(ticker)` → returns {target_price, recommendation}
- [ ] Add `get_volume_data(ticker)` → returns {avg_volume, avg_volume_10d}
- [ ] Add `get_earnings_timestamp(ticker)` → returns datetime from earningsTimestamp
- [ ] Add `is_data_stale(ticker, max_age_hours=24)` → checks _saved_at timestamp

#### Task 2: Update StockDataService to Use Stored Data
- [ ] Modify `get_price_context()` to accept SecurityService parameter
- [ ] Use stored 52w range instead of calculating from 365 days of data
- [ ] Use stored MAs (50d, 200d) when available
- [ ] Reduce history fetch from 365 days to 30 days (for RSI and recent changes only)
- [ ] Add short interest fields to PriceContext dataclass

#### Task 3: Add Short Squeeze Context to PriceContext
- [ ] Add `shares_short`, `short_ratio`, `short_percent_float` to PriceContext
- [ ] Update `to_context_string()` to show SI% and days-to-cover for high SI stocks
- [ ] Format: "SI: 36.5% (5.4 days to cover)" when SI > 10%

#### Task 4: Update MarketDataService to Check Stored Data First
- [ ] Modify `get_earnings_info()` to check SecurityService.get_earnings_timestamp() first
- [ ] Only call yf.Ticker().calendar if earnings not in stored data
- [ ] Consider file-based caching for insider trades and SEC filings

#### Task 5: Wire Up Services in Agent Nodes
- [ ] Update `analysis.py` to pass SecurityService to StockDataService methods
- [ ] Update `debate.py` to pass SecurityService to _format_holdings()
- [ ] Update `agent.py` (simple agent) to use SecurityService for stored data

#### Task 6: Fetch Current Prices for BUY Candidates (from Package I Task 3)
- [ ] During research/analysis phase, fetch current prices for tickers agent is considering
- [ ] Store fetched BUY candidate data in `{TICKER}_data.json` for reuse
- [ ] Provide bid/ask spread context when available (from stored `bid`, `ask` fields)
- [ ] Include current price in generate_trades prompt so agent can calculate quantities

#### Task 7: Add Unit Tests
- [ ] Test SecurityService rich data methods
- [ ] Test StockDataService using stored 52w/MA data
- [ ] Test short interest formatting in PriceContext
- [ ] Test data staleness checking

### Expected Benefits
- **Simplified data model**: Ticker-only storage, no more ISIN complexity
- **Cleaner file naming**: `AAPL_data.json` instead of `US0378331005_data.json`
- **Reduced yfinance API calls**: 365→30 day history fetch
- **Short squeeze data**: Automatically in prompts (SI%, days-to-cover)
- **Faster agent execution**: Less network I/O
- **Single source of truth**: One file per ticker for all static data

