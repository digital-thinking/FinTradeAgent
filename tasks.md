# Implementation Tasks

## Conventions

- Each task lists the Primary Files it touches and the BUGS.md IDs it resolves.
- Commit after each task (atomic commits, per CLAUDE.md). Do not bundle unrelated
  fixes into one commit.
- New unit tests are required for any task that changes a numeric calculation.
- "Deferred" bugs are listed at the bottom of the phase with the reason they are
  not being addressed in this pass.

---

## Phase 1 — Finance Audit Fixes (BUGS.md, 2026-04-20)

Goal: restore numerical correctness of the performance page, accounting state,
and context signals that feed the LLM, based on the finance SME review in
`BUGS.md`. Fixes are sequenced so later tasks can rely on primitives built in
earlier tasks (e.g. mark-to-market value series, daily return series).

### Task 1.1 — Mark-to-market historical value series
**Resolves:** BUG-F01
**Primary Files:**
- `src/fin_trade/services/comparison.py` (`_build_portfolio_value_series`)
- `src/fin_trade/pages/portfolio_detail.py` (`_calculate_performance_data`)
- `src/fin_trade/services/stock_data.py` (add helper to fetch aligned daily closes
  for a set of tickers over a date range)

**Actions:**
- Replace `Σ(qty * avg_price)` with `Σ(qty * close_i(t))` at every timestamp.
- Add a helper `StockDataService.get_closes(tickers, start, end) -> DataFrame`
  returning adjusted closes (see Task 1.7) aligned on a daily DatetimeIndex.
- For the equity curve, emit one row per trading day between the first trade
  and now (forward-fill closes over weekends/holidays), not just one row per
  trade — this becomes the input to volatility/Sharpe.
- Unit test: synthetic state with 1 BUY at t0, then close rises 10% over 5
  days → value at t0+5d equals `cash + qty * 1.10 * buy_price`, not cost basis.

### Task 1.2 — Correct beta from daily return covariance
**Resolves:** BUG-F02
**Primary Files:**
- `src/fin_trade/services/comparison.py` (`calculate_metrics`)

**Actions:**
- Align portfolio daily returns (from Task 1.1) and benchmark daily returns on a
  common business-day index.
- Compute `beta = Cov(r_p, r_m) / Var(r_m)` using `numpy`.
- Guard `Var(r_m) == 0` → beta = None.
- Unit test: portfolio that literally tracks the benchmark → beta ≈ 1.0; a
  constant-value portfolio (cash only) → beta ≈ 0.0.

### Task 1.3 — Jensen's alpha + relabel fallback
**Resolves:** BUG-F03
**Primary Files:**
- `src/fin_trade/services/comparison.py` (`calculate_metrics`, `get_comparison_table`)

**Actions:**
- With corrected beta (Task 1.2) and annualized returns, compute
  `alpha = R_p − [R_f + β · (R_m − R_f)]` annualized.
- If beta is None, fall back to `R_p − R_m` but label the column
  "Excess Return" rather than "Alpha" in `get_comparison_table`.
- Unit test: perfect-benchmark portfolio → alpha ≈ 0%; portfolio with +5%
  risk-adjusted return → alpha ≈ +5%.

### Task 1.4 — Volatility from daily-resampled returns
**Resolves:** BUG-F04
**Primary Files:**
- `src/fin_trade/services/comparison.py` (`calculate_metrics`)

**Actions:**
- Feed `std()` the daily return series produced in Task 1.1 (not the per-trade
  series).
- Keep the `√252` annualization factor.
- Unit test: portfolio with known daily return std → matches hand-calculated
  annualized volatility.

### Task 1.5 — Relabel 3-month yield, stop calling it 2-year
**Resolves:** BUG-F05
**Primary Files:**
- `src/fin_trade/services/market_data.py` (`MacroData` dataclass, `get_macro_data`,
  yield-curve spread line, recession signal)
- Any consumers in prompt builders or UI that render `treasury_2y` /
  "10Y − 2Y" text.

**Actions:**
- Rename field `treasury_2y` → `treasury_3m` everywhere.
- Relabel the spread as "10Y − 3M" in the MacroData string and anywhere the
  LLM/UI renders it.
- Update the recession-signal comment to note 3M−10Y inversion vs. 2Y−10Y.
- FRED integration for a true 2Y yield is out of scope for this phase
  (see Deferred).

### Task 1.6 — Execute at quoted price, not refetched price
**Resolves:** BUG-F08
**Primary Files:**
- `src/fin_trade/services/portfolio.py` (`execute_trade`)
- `src/fin_trade/pages/pending_trades.py` (pass captured price through to
  `execute_trade`)

**Actions:**
- Add required `price: float` parameter to `execute_trade`. Remove the
  `force_update_price` call.
- In `_apply_pending_trades`, capture price once per ticker at the moment the
  user clicks "Apply" (into a `{ticker: price}` dict), and pass that price to
  every `execute_trade` call in the batch.
- Unit test: `execute_trade(..., price=123.45)` writes a trade with
  `price == 123.45` regardless of what `get_price` returns.

### Task 1.7 — Split/dividend-adjusted price history
**Resolves:** BUG-F06
**Primary Files:**
- `src/fin_trade/services/stock_data.py` (`update_data` and any `yf.Ticker.history`
  call sites)
- `src/fin_trade/services/comparison.py` (benchmark cumulative return)

**Actions:**
- Pass `auto_adjust=True` to `stock.history(...)` in `update_data`.
- Delete the existing cached CSVs (they contain unadjusted closes) as part of
  the change rationale in the commit message; cache will repopulate on next
  fetch.
- Confirm `cumulative_return` in `get_benchmark_performance` is now true total
  return (includes dividends for SPY).
- Unit test: mock a yfinance response with a known split; cached close after
  the split adjusts earlier prices.

### Task 1.8 — Fix `initial_investment` inflation in pending-trades apply
**Resolves:** BUG-F09
**Primary Files:**
- `src/fin_trade/pages/pending_trades.py` (`_apply_pending_trades`)

**Actions:**
- Remove the `+100` buffer entirely. If `total_buy_cost > state.cash`, raise a
  user-visible error and do not auto-top-up cash.
- Only set `state.initial_investment` when transitioning from
  `len(state.trades) == 0` → `>0`, i.e. guard with
  `if state.initial_investment is None:`.
- Unit test: apply two pending batches in sequence from an empty portfolio →
  `initial_investment` is set by batch 1 and unchanged by batch 2.

### Task 1.9 — Record realized P/L on SELL (FIFO tax lots)
**Resolves:** BUG-F10 (partial — TWR deferred)
**Primary Files:**
- `src/fin_trade/models/portfolio.py` (add `realized_pnl: float | None` to `Trade`)
- `src/fin_trade/services/portfolio.py` (`execute_trade` SELL branch; state
  save/load)
- `src/fin_trade/pages/portfolio_detail.py` / trade history render

**Actions:**
- On each SELL, compute realized P/L using FIFO over prior BUYs of the same
  ticker (re-use the matcher shape from `comparison._calculate_win_rate`).
- Persist `realized_pnl` on the Trade record; backfill `None` for existing
  trades on load.
- Surface cumulative realized P/L as a separate metric ("Realized P/L") in the
  portfolio detail page, distinct from unrealized mark-to-market.
- Unit test: BUY 10 @ $10, BUY 10 @ $20, SELL 15 @ $25 → realized P/L on the
  SELL trade = 10×(25−10) + 5×(25−20) = $175.

### Task 1.10 — Monthly cadence uses calendar months
**Resolves:** BUG-F11
**Primary Files:**
- `src/fin_trade/services/portfolio.py` (`is_execution_overdue`)
- `src/fin_trade/pages/dashboard.py` (upcoming runs schedule)

**Actions:**
- Use `dateutil.relativedelta(months=1)` for the "monthly" cadence.
- Add `python-dateutil` to Poetry dependencies if not already present.
- Unit test: last execution 2026-01-31 → next due 2026-02-28 (not 2026-03-02).

### Task 1.11 — Wilder's smoothing for RSI
**Resolves:** BUG-F12
**Primary Files:**
- `src/fin_trade/services/stock_data.py` (`_calculate_rsi`)

**Actions:**
- Replace `rolling(window=period).mean()` with
  `ewm(alpha=1/period, adjust=False).mean()` for both gains and losses.
- Unit test: feed in a hand-crafted 20-day series and assert final RSI matches
  the Wilder reference value (1978 worked example).

### Task 1.12 — 52-week range uses ≥252 trading days
**Resolves:** BUG-F13
**Primary Files:**
- `src/fin_trade/services/stock_data.py` (`get_price_context`)

**Actions:**
- When falling back to history for `high_52w`/`low_52w`, always call
  `get_history(ticker, days=400)` (buffered for weekends/holidays) and take
  max/min of that slice — do not reuse the `days_needed` value that may be 30.
- Unit test: with `days_needed=30` code path, returned `high_52w` equals the
  max over ~365 calendar days of input data.

### Task 1.13 — Contribution % on gross-absolute basis
**Resolves:** BUG-F14
**Primary Files:**
- `src/fin_trade/services/attribution.py` (`calculate_attribution`,
  `_calculate_sector_attribution`)

**Actions:**
- Change `contribution_pct = unrealized_gain / total_gain` to
  `contribution_pct = unrealized_gain / sum(abs(h.unrealized_gain) for h in ...)`.
- Keep sign on the resulting percent (winner is positive, detractor is negative).
- Unit test: two holdings +$500 / −$499 → contributions of +50.05% / −49.95%,
  not ±50,000%.

### Task 1.14 — `float` quantities in attribution and reflection
**Resolves:** BUG-F15
**Primary Files:**
- `src/fin_trade/services/attribution.py` (`HoldingAttribution.quantity`)
- `src/fin_trade/services/reflection.py` (`CompletedTrade.quantity`)
- `src/fin_trade/pages/dashboard.py` (quantity column_config)

**Actions:**
- Change both dataclass fields to `float`.
- Replace `format="d"` with the existing `format_quantity()` helper (8-decimal
  for CRYPTO, whole number for STOCKS) in the dashboard column config.
- Unit test: BTC-USD holding of 0.1234 produces non-zero cost basis and
  current value in attribution.

### Task 1.15 — Benchmark row: compute or omit, don't fabricate
**Resolves:** BUG-F16, BUG-F17
**Primary Files:**
- `src/fin_trade/services/comparison.py` (`get_comparison_table`)

**Actions:**
- Compute real benchmark volatility, Sharpe, max drawdown, and days_active over
  the same `[first_trade_date, now]` window used for each *portfolio row*.
  Because the table is shared across portfolios, use the *widest* portfolio
  window (earliest `first_trade_date` across the set) for the single benchmark
  column and note the window in a subtitle.
- Drop the hardcoded "~15%", "N/A", "0.0%", "1.00", "365" strings.
- Unit test: benchmark row produces non-hardcoded numbers that match
  `calculate_metrics` run on a synthetic benchmark-tracking portfolio.

### Task 1.16 — Preserve SL/TP on partial-fill reflection rebuild
**Resolves:** BUG-F18
**Primary Files:**
- `src/fin_trade/services/reflection.py` (`_find_completed_trades`)

**Actions:**
- When rebuilding the partially-remaining buy at
  `reflection.py:225-233`, also pass `stop_loss_price` and `take_profit_price`.
- Unit test: partially filled BUY with SL/TP → rebuilt open buy retains SL/TP.

### Task 1.17 — Tolerant float comparison in SELL validation
**Resolves:** BUG-F19
**Primary Files:**
- `src/fin_trade/services/portfolio.py` (`execute_trade` SELL branch)

**Actions:**
- Round or `math.isclose` the qty comparison with `abs_tol=1e-9` (crypto) /
  `abs_tol=1e-6` (stocks) to avoid 5e-17 residuals.
- After SELL, drop any holding whose `quantity` is within tolerance of zero.
- Unit test: BUY 0.1 + BUY 0.2, SELL 0.3 → holdings is empty (no 5e-17
  residual), no exception raised.

### Task 1.18 — Per-tax-lot win rate + profit factor
**Resolves:** BUG-F20
**Primary Files:**
- `src/fin_trade/services/comparison.py` (`_calculate_win_rate`, `PortfolioMetrics`,
  `get_comparison_table`)

**Actions:**
- Change FIFO matcher to count per tax-lot closure, not per SELL event.
- Add `profit_factor_pct: float | None` to `PortfolioMetrics` =
  `Σwinners_$ / |Σlosers_$|`.
- Render both "Win Rate" and "Profit Factor" side-by-side in the comparison
  table.
- Unit test: a SELL closing one winning and one losing lot produces 50% win
  rate (1 of 2), not 100%.

### Task 1.19 — `initial_investment` zero-vs-None semantics
**Resolves:** BUG-F22
**Primary Files:**
- `src/fin_trade/services/portfolio.py` (`calculate_gain`)
- `src/fin_trade/services/comparison.py` (`_build_portfolio_value_series`,
  `calculate_metrics`)
- `src/fin_trade/pages/portfolio_detail.py` (3 call sites)

**Actions:**
- Replace every `initial_investment or config.initial_amount` with
  `initial_investment if initial_investment is not None else config.initial_amount`.
- Unit test: a state with `initial_investment=0.0` reports `return_pct=0.0`
  (not a non-zero value inferred from `config.initial_amount`).

### Task 1.20 — Earnings "today" uses hours, not days
**Resolves:** BUG-F23
**Primary Files:**
- `src/fin_trade/services/market_data.py` (`get_earnings_info`, 2 call sites)

**Actions:**
- Replace `(earnings_date - datetime.now()).days` with a float-hour computation;
  store `hours_until_earnings` in `EarningsInfo`, derive days in formatters.
- Treat hours < −1 as "past" and omit from the prompt.
- Unit test: earnings 3h ago → not rendered; earnings 5h from now → rendered
  as "today".

### Task 1.21 — UTC-aware trade timestamps
**Resolves:** BUG-F24 (partial — price-history tz stays as-is for now)
**Primary Files:**
- `src/fin_trade/services/portfolio.py` (`execute_trade`, `_to_naive_datetime`,
  state save/load)
- `src/fin_trade/services/comparison.py`, `pages/portfolio_detail.py` — any
  `datetime.now()` used as a timestamp cutoff for trades.

**Actions:**
- Use `datetime.now(timezone.utc)` for new Trade timestamps and `last_execution`.
- On load, parse timestamps and normalize to UTC-aware.
- Keep display conversion to local time in UI only.
- Unit test: a trade created at local 23:00 on day D still falls on day D when
  filtered with a UTC cutoff of `D 00:00`.

### Task 1.22 — Reflection holding days as float
**Resolves:** BUG-F26
**Primary Files:**
- `src/fin_trade/services/reflection.py` (`CompletedTrade.holding_days`,
  `_find_completed_trades`, `_calculate_metrics`, `_analyze_biases`)

**Actions:**
- Type `holding_days: float` and compute with
  `(sell.timestamp - buy.timestamp).total_seconds() / 86400`.
- Update the "quick trades < 7" and "> 30" thresholds to work on float days
  (no integer floor).
- Unit test: a 4h-held trade reports `holding_days ≈ 0.17`, not 0.

---

## Deferred (not fixed in this phase)

| Bug     | Reason for deferral                                                                                    |
|---------|--------------------------------------------------------------------------------------------------------|
| BUG-F07 | Multi-currency FX engine is a project in its own right: needs FX-rate service, reporting-currency setting on portfolio, separate FX P/L attribution, UI changes across three pages. Addressing it as a one-off risks a half-built implementation. Track as its own phase once the performance layer is trustworthy. |
| BUG-F10 (TWR portion) | TWR requires sub-periodizing around every external cash flow and recording deposits/withdrawals as first-class events. The realized-P/L half of F10 is included in Task 1.9; the TWR half is deferred until we introduce a Deposit/Withdrawal model. |
| BUG-F21 | Transaction costs, slippage, and margin interest are configurable modelling choices, not bugs. Deciding on a default commission model, spread model, and cash-rate schedule is a product call — revisit after Phase 1. |
| BUG-F25 | Aggregate return displayed on the dashboard/overview is a labelling/product question (which denominator; annualized vs. since-inception; AUM-weighting). Not a correctness fix — revisit once the per-portfolio numbers are trustworthy post-Phase-1. |
| BUG-F24 (price-history tz portion) | Task 1.21 makes trade timestamps UTC-aware. Fully standardizing yfinance DataFrame indexes to UTC-aware through every consumer requires a broader sweep; defer until a concrete tz-bug is reported after 1.21 lands. |
