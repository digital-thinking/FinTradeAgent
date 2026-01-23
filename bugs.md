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
- [ ] **Error: Insufficient cash: trades require...**
    - If a trade combines sell and buy, the total value is not considered correctly
    - The behavior should be:
      - if the SELL order is selected as included, the cash from this sell order should be considered as available for the buy options
      - SELL order are executed first in the log so that everything works out

