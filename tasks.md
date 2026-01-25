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

## 📦 Package B: UI Foundation (Components & Style)
*Focus: Visual consistency, reusable components, and basic UI elements.*
*Primary Files: `src/fin_trade/components/`, `src/fin_trade/pages/` (visual tweaks), `src/fin_trade/app.py` (CSS)*

- [x] **Improve the Performance chart**
    - Fully rework it
    - Make it more interactive

## 📦 Package D: Dashboard & Navigation
*Focus: High-level application structure and portfolio management views.*
*Primary Files: `src/fin_trade/pages/overview.py`, `src/fin_trade/pages/dashboard.py` (new), `src/fin_trade/app.py`*

- [x] **Performance Attribution**
    - Create a new analysis module to calculate contribution to return by sector and ticker.
    - Visualize attribution in the dashboard (e.g., "Tech sector +5%, Energy -2%").
    - Use the industry/sector information from the already existent json of the ISIN stock data

## 📦 Package E: Agent Interaction Flow
*Focus: The user experience of running agents and reviewing results.*
*Primary Files: `src/fin_trade/pages/portfolio_detail.py`, `src/fin_trade/agents/`, `src/fin_trade/services/agent.py`*

- [x] **Stop-Loss & Take-Profit**
    - Update `TradeRecommendation` model to include `stop_loss_price` and `take_profit_price`.
    - Update agent prompts to require these fields for every BUY order.
    - Visualize these levels on the trade review card.

## 📦 Package F: Testing & Optimization
*Focus: Quality assurance, performance, and stability.*
*Primary Files: `tests/`, `src/fin_trade/services/stock_data.py`, `src/fin_trade/app.py`*

- [ ] **Asynchronous Execution**
    - Optimize backend processing to ensure UI responsiveness.

## 📦 Package G: Data & Intelligence (New) - IN PROGRESS
*Focus: Expanding data sources and agent intelligence.*
*Primary Files: `src/fin_trade/services/market_data.py` (new), `src/fin_trade/services/agent.py`, `src/fin_trade/prompts/simple_agent.py`*

### Implementation Plan

This package implements the **Data & Integrations** section from ROADMAP.md:
- Macro-Economic Data (CPI, GDP, unemployment, Fed rates)
- SEC Filings (8-K, 10-Q, 10-K alerts/summaries)
- Earnings Calendar (upcoming earnings dates and results)
- Insider Trading Data (buy/sell activity)

#### Task 1: Create MarketDataService
- [x] Create `src/fin_trade/services/market_data.py` with a new `MarketDataService` class
- [x] Implement earnings calendar fetching using yfinance `.calendar` property
- [x] Implement insider transactions fetching using yfinance `.insider_transactions`
- [x] Cache data appropriately (24h for earnings, 24h for insider trades)

#### Task 2: Add SEC Filings Integration
- [x] Use yfinance `.sec_filings` to fetch recent SEC filings (8-K, 10-Q, 10-K)
- [x] Parse and format filing data for agent consumption

#### Task 3: Add Macro-Economic Data
- [x] Fetch major market indices (S&P 500, Nasdaq, Dow Jones) for market context
- [x] Fetch Treasury yields (10Y, 2Y) for interest rate context using yfinance

#### Task 4: Integrate Data into Agent Context
- [x] Update `_build_prompt()` in `agent.py` to include market data
- [x] Add new prompt sections for earnings, filings, insider trades, and macro data
- [x] Update `SIMPLE_AGENT_PROMPT` to reference and use the new data

#### Task 5: Add Unit Tests
- [x] Create `tests/test_market_data_service.py` with tests for MarketDataService (22 tests)
- [x] Mock yfinance calls to ensure reliable test execution
