# Parallel Development Task Bugs

**INSTRUCTIONS FOR AGENTS:**
1.  **Select a single bug** to work on. Do not mix tasks from different bugs to avoid merge conflicts.
2.  **Scope isolation**: Try to limit your changes to the files listed in the "Primary Files" section of your bug.
3.  **Shared Resources**: If you must modify shared files (e.g., `app.py`, `services/__init__.py`), check if other active agents are modifying them.
4.  **New Files**: Prefer creating new files/modules over heavily modifying existing large files.
5.  **Marking Progress**: When you start a bug, assume you own it until completion.
6.  **Atomic Commits**: After completing each individual task (bullet point) within a bug, ask the user to commit the changes before moving to the next task. Do not accumulate multiple features in a single commit.

---

## 📦 Bugs:
- [x] **Error: Insufficient cash: trades require...**
    - If a trade combines sell and buy, the total value is not considered correctly
    - The behavior should be:
      - if the SELL order is selected as included, the cash from this sell order should be considered as available for the buy options
      - SELL order are executed first in the log so that everything works out
    - **Fixed:** validate_node now accounts for SELL proceeds when checking BUY cash requirements.
      trade_display.py processes SELL orders first to calculate available cash.
      on_accept in portfolio_detail.py executes SELL orders before BUY orders.
- [x] **Portfolio Charts**
    - The Portfolio Overview and the Performance Tab should show the chart as a stacked chart
    - The stacked chart consists of:
      - The cash holding
      - The stock holdings
      - All correctly over time
    - The Performance tab, of course, stays more detailed with Buy/Sell Indicators (...)
    - **Fixed:** Both the Portfolio Overview mini charts and the Performance Tab now use stacked area charts
      showing cash (green) and holdings (blue) over time. Trade markers preserved on Performance tab.
  

