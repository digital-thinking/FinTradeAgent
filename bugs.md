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

- [x] **Pending Trades: Missing ticker correction UI** ✅ Fixed
    - When a ticker is invalid/not found (e.g., wrong symbol, regional variant like "BASF" vs "BAS.DE"), the Pending Trades page cannot execute the trade
    - The portfolio detail page has a ticker correction UI that allows users to:
      - Correct the ticker symbol
      - Add the ISIN manually
    - This UI should be available in the Pending Trades page as well
    - **Implementation notes:**
      - Extract the ticker correction UI from `components/trade_display.py` into a reusable component
      - Use the component in both `trade_display.py` and `pages/pending_trades.py`
      - The component should handle: ticker input, verify button, ISIN input, price lookup feedback
    - **Primary Files:** `backend/fin_trade/components/ticker_correction.py` (new), `backend/fin_trade/components/trade_display.py`, `backend/fin_trade/pages/pending_trades.py`
    - **Resolution:** Created `ticker_correction.py` component with `render_ticker_correction()`, `apply_isin_corrections()`, and `clear_ticker_corrections()` functions. Integrated into `pending_trades.py`.

- [x] **Error messages disappear too quickly** ✅ Fixed
    - When an error occurs (e.g., ticker not found, trade execution fails), the error message flashes briefly and disappears almost instantly
    - Users don't have time to read the error message
    - The error should persist until the user takes action or navigates away
    - **Implementation notes:**
      - Likely caused by `st.rerun()` being called after showing the error
      - Consider storing errors in session state and displaying them persistently
      - Or remove/delay the rerun to let users see the message
    - **Primary Files:** `backend/fin_trade/pages/pending_trades.py`, potentially other pages with similar issues
    - **Resolution:** Store messages in session state before `st.rerun()` and display them via `_display_persistent_messages()` at the top of each page. Applied to both `pending_trades.py` and `system_health.py`.

- [x] **Pending Trades: Cannot delete trades** ✅ Fixed
    - Users should be able to delete/reject pending trades that they do not wish to execute.
    - Currently, trades just sit in the "Pending" state until executed.
    - **Implementation notes:**
      - Add a "Delete" or "Reject" button next to each pending trade in the list.
      - Upon clicking, remove the trade from the `PortfolioState.pending_trades` list.
      - Save the updated state.
    - **Primary Files:** `backend/fin_trade/pages/pending_trades.py`, `backend/fin_trade/services/portfolio.py`
    - **Resolution:** Added a delete button to the pending trades UI. Implemented `_reject_trade` function to mark trades as rejected in the execution log, effectively removing them from the pending list.
