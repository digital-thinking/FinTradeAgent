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

- [ ] **Pending Trades: Missing ticker correction UI**
    - When a ticker is invalid/not found (e.g., wrong symbol, regional variant like "BASF" vs "BAS.DE"), the Pending Trades page cannot execute the trade
    - The portfolio detail page has a ticker correction UI that allows users to:
      - Correct the ticker symbol
      - Add the ISIN manually
    - This UI should be available in the Pending Trades page as well
    - **Implementation notes:**
      - Extract the ticker correction UI from `components/trade_display.py` into a reusable component
      - Use the component in both `trade_display.py` and `pages/pending_trades.py`
      - The component should handle: ticker input, verify button, ISIN input, price lookup feedback
    - **Primary Files:** `src/fin_trade/components/ticker_correction.py` (new), `src/fin_trade/components/trade_display.py`, `src/fin_trade/pages/pending_trades.py`

- [ ] **Error messages disappear too quickly**
    - When an error occurs (e.g., ticker not found, trade execution fails), the error message flashes briefly and disappears almost instantly
    - Users don't have time to read the error message
    - The error should persist until the user takes action or navigates away
    - **Implementation notes:**
      - Likely caused by `st.rerun()` being called after showing the error
      - Consider storing errors in session state and displaying them persistently
      - Or remove/delay the rerun to let users see the message
    - **Primary Files:** `src/fin_trade/pages/pending_trades.py`, potentially other pages with similar issues

