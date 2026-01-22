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

- [ ] **Dependency Injection for LLM Providers**
    - Create `LLMProvider` abstract base class.
    - Implement `OpenAIProvider` and `AnthropicProvider`.
    - Refactor `AgentService` to use these providers instead of hardcoded logic.
- [ ] **Centralized Prompt Management**
    - Create a `prompts` module or directory.
    - Move all hardcoded prompts (from `agent.py`, `nodes/*.py`) into templates (Jinja2 or simple strings).

## 📦 Package B: UI Foundation (Components & Style)
*Focus: Visual consistency, reusable components, and basic UI elements.*
*Primary Files: `src/fin_trade/components/`, `src/fin_trade/pages/` (visual tweaks), `src/fin_trade/app.py` (CSS)*

- [x] **Extract Reusable Components**
    - Create shared components for Status Badges, Trade Action colors, and Portfolio Metrics.
    - Refactor `overview.py` and `portfolio_detail.py` to use them.
- [ ] **Consistent Button Hierarchy**
    - Define and apply primary/secondary/danger button styles consistently across the app.
- [ ] **Loading Skeletons**
    - Create a skeleton loader component.
    - Replace blank states with skeletons during data fetching.
- [ ] **Use Dataframes for Tables**
    - Replace divider-based row layouts in Holdings and Trade History with `st.dataframe()` for sorting/scanning.
- [ ] **Improve Mobile Layout**
    - Refactor fixed column grids to be responsive.

## 📦 Package C: Advanced Features (New Modules)
*Focus: New business logic and capabilities.*
*Primary Files: `src/fin_trade/services/risk.py` (new), `src/fin_trade/services/backtest.py` (new), `src/fin_trade/services/research.py` (refactor)*

- [ ] **Risk Management Module**
    - Create `RiskService`.
    - Implement rules: Max sector allocation, Stop-loss/Take-profit checks.
    - Integrate into `validate_node`.
- [ ] **Vector Database for Research**
    - Implement a simple vector store (e.g., ChromaDB or simple file-based embeddings).
    - Cache research summaries to reduce redundant web searches.
- [ ] **Backtesting Capability**
    - Create a backtesting engine to replay historical data.
    - Use cached `StockDataService` data to simulate agent performance.

## 📦 Package D: Dashboard & Navigation
*Focus: High-level application structure and portfolio management views.*
*Primary Files: `src/fin_trade/pages/overview.py`, `src/fin_trade/pages/dashboard.py` (new), `src/fin_trade/app.py`*

- [ ] **Summary Dashboard**
    - Create a new tab/view showing total value across all strategies.
    - Show best/worst performers and upcoming scheduled runs.
- [ ] **Portfolio Comparison**
    - Add a view to overlay performance charts of multiple portfolios.
- [ ] **Portfolio Filtering & Sorting**
    - Add controls to filter by status (overdue/current) and sort by value/return.
- [ ] **Ticker Correction UI**
    - Improve the UI for handling unknown tickers (move from expander to inline).
- [ ] **Keyboard Shortcuts**
    - Add shortcuts for common actions (New Portfolio, Run Agent, Back).

## 📦 Package E: Agent Interaction Flow
*Focus: The user experience of running agents and reviewing results.*
*Primary Files: `src/fin_trade/pages/portfolio_detail.py`, `src/fin_trade/agents/`, `src/fin_trade/services/agent.py`*

- [ ] **User Feedback Loop**
    - Add UI to inject user feedback *during* the debate or before generation.
    - Update agent graph to accept user input node.
- [ ] **Improve Agent Execution Feedback**
    - Enhance the "Running..." status display.
    - Add collapsible summary for debate transcripts with key points highlighted.
- [ ] **Detailed Transaction Logs**
    - Store execution logs (tokens, latency, model) in SQLite.
    - Create a view to inspect these logs (System Health/Cost Analysis).
- [ ] **Paginate Trade History**
    - Add pagination or "Load More" to the trade history tab.

## 📦 Package F: Testing & Optimization
*Focus: Quality assurance, performance, and stability.*
*Primary Files: `tests/`, `src/fin_trade/services/stock_data.py`, `src/fin_trade/app.py`*

- [ ] **Unit & Integration Tests**
    - Create `tests/` directory.
    - Add tests for `PortfolioService` and `validate_node`.
    - Create mocks for `SecurityService` and LLM calls.
- [x] **UI Caching**
    - Add `@st.cache_data` to expensive calculations (`calculate_value`, `calculate_gain`).
- [ ] **Asynchronous Execution**
    - Optimize backend processing to ensure UI responsiveness.
