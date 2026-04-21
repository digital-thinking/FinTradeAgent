# Implementation Tasks

## Conventions

- Each task lists the Primary Files it touches and the BUGS.md IDs it resolves.
- Commit after each task (atomic commits, per CLAUDE.md). Do not bundle unrelated
  fixes into one commit.
- New unit tests are required for any task that changes a numeric calculation.
- "Deferred" bugs are listed at the bottom of the phase with the reason they are
  not being addressed in this pass.

---

## Deferred (not fixed)

| Bug     | Reason for deferral                                                                                    |
|---------|--------------------------------------------------------------------------------------------------------|
| BUG-F07 | Multi-currency FX engine is a project in its own right: needs FX-rate service, reporting-currency setting on portfolio, separate FX P/L attribution, UI changes across three pages. Addressing it as a one-off risks a half-built implementation. Track as its own phase once the performance layer is trustworthy. |
| BUG-F10 (TWR portion) | TWR requires sub-periodizing around every external cash flow and recording deposits/withdrawals as first-class events. The realized-P/L half of F10 is included in Task 1.9; the TWR half is deferred until we introduce a Deposit/Withdrawal model. |
| BUG-F21 | Transaction costs, slippage, and margin interest are configurable modelling choices, not bugs. Deciding on a default commission model, spread model, and cash-rate schedule is a product call — revisit after Phase 1. |
| BUG-F25 | Aggregate return displayed on the dashboard/overview is a labelling/product question (which denominator; annualized vs. since-inception; AUM-weighting). Not a correctness fix — revisit once the per-portfolio numbers are trustworthy post-Phase-1. |
| BUG-F24 (price-history tz portion) | Task 1.21 makes trade timestamps UTC-aware. Fully standardizing yfinance DataFrame indexes to UTC-aware through every consumer requires a broader sweep; defer until a concrete tz-bug is reported after 1.21 lands. |
