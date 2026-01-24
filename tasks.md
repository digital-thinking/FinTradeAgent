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

## 📦 Package G: Data & Intelligence (New)
*Focus: Expanding data sources and agent intelligence.*
*Primary Files: `src/fin_trade/services/stock_data.py`, `src/fin_trade/services/agent.py`*

- [ ] **Data Source Expansion**
    - **Earnings**: Integrate an earnings calendar API to warn agents of upcoming volatility.
    - **SEC Filings**: Fetch recent 8-K/10-Q summaries for held companies.
    - **Sentiment**: Scrape and aggregate sentiment scores from news headlines.
