# Parallel Development Task Bugs

**INSTRUCTIONS FOR AGENTS:**
1.  **Select a single bug** to work on. Do not mix tasks from different bugs to avoid merge conflicts.
2.  **Scope isolation**: Try to limit your changes to the files listed in the "Primary Files" section of your bug.
3.  **Shared Resources**: If you must modify shared files (e.g., `app.py`, `services/__init__.py`), check if other active agents are modifying them.
4.  **New Files**: Prefer creating new files/modules over heavily modifying existing large files.
5.  **Marking Progress**: When you start a bug, assume you own it until completion.
6.  **Atomic Commits**: After completing each individual task (bullet point) within a bug, ask the user to commit the changes before moving to the next task. Do not accumulate multiple features in a single commit.

---

## 📦 Bugs (Finance SME Review — 2026-04-20)

The following bugs were surfaced by a finance-focused review of portfolio accounting,
performance measurement, and market-data handling. Severity reflects impact on the
*correctness of reported numbers* (P/L, return, risk) rather than UX.

---

### BUG-F01 — CRITICAL: Historical portfolio value uses cost basis, not market value
**Primary Files:**
- `src/fin_trade/pages/portfolio_detail.py` (lines 487-526, `_calculate_performance_data`)
- `src/fin_trade/services/comparison.py` (lines 66-121, `_build_portfolio_value_series`)

**Problem:** Both performance-charting paths compute the intermediate portfolio value as
`cash + Σ(quantity * avg_price)`. Since `avg_price` is the weighted *cost basis*, the
sum `cash + cost_basis` is mathematically identical to the initial cash contribution
for every step between trades. The portfolio equity curve is therefore a flat line at
the initial amount, with an artificial jump at the final point (which does use live
prices). As a direct result:

- The portfolio-detail performance chart shows essentially no movement between trades.
- `ComparisonService.calculate_metrics` feeds this flat series into `pct_change` →
  daily returns of ~0 except at trade timestamps, which then propagates wrong
  **volatility, Sharpe ratio, and max drawdown**.
- `get_normalized_returns` produces flat comparison lines for every portfolio.

**Fix:** At each timestamp in the series, mark-to-market all open positions using
historical close prices from `StockDataService.get_history` (not `avg_price`). The
value at time *t* should be `cash_t + Σ(qty_i * close_i(t))`.

---

### BUG-F02 — CRITICAL: Beta is computed as ratio of total returns
**Primary Files:**
- `src/fin_trade/services/comparison.py` (lines 376-379)

**Problem:**
```python
if benchmark_return != 0:
    beta = total_return / benchmark_return
```
Beta is defined as `Cov(R_p, R_m) / Var(R_m)` over a return series — it is **not** the
ratio of two cumulative returns. The current implementation produces nonsense values
(e.g., if the benchmark is down 5% and the portfolio is up 10%, the reported beta is
-2.0). Alpha derived from this number is also meaningless.

**Fix:** Align portfolio and benchmark on a common daily return series (see BUG-F01),
then compute `beta = np.cov(port_ret, bench_ret)[0,1] / np.var(bench_ret)`.

---

### BUG-F03 — HIGH: Alpha is simple excess return, not Jensen's alpha
**Primary Files:**
- `src/fin_trade/services/comparison.py` (lines 370-374)

**Problem:** `alpha = total_return - benchmark_return` is excess return, not alpha.
Jensen's alpha requires the CAPM adjustment:
`α = R_p − [R_f + β · (R_m − R_f)]`. Because the label in the UI is "Alpha", users
(and the LLM prompts that may consume these metrics) are misled about whether the
portfolio beat its risk-adjusted benchmark.

**Fix:** Either rename to "Excess Return" or compute Jensen's alpha using a correct
beta (BUG-F02) and the configured risk-free rate.

---

### BUG-F04 — HIGH: Volatility annualization assumes daily observations
**Primary Files:**
- `src/fin_trade/services/comparison.py` (lines 339-347)

**Problem:** The series fed into `pct_change()` contains one row per **trade**, plus a
final "now" point. Weekly/monthly strategies will have a few dozen rows per year, not
252. Multiplying `std()` by `√252` therefore massively under- or over-states
annualized volatility depending on sampling frequency.

**Fix:** Resample the value series to a uniform daily frequency (after fixing BUG-F01)
before computing `std()`, or apply the correct annualization factor based on the
observed sample frequency.

---

### BUG-F05 — HIGH: 2-year Treasury yield is actually the 3-month T-bill
**Primary Files:**
- `src/fin_trade/services/market_data.py` (line 410)

**Problem:**
```python
treasury_2y = get_treasury_yield("^IRX")  # 3-month as proxy, 2Y is ^TWO
```
`^IRX` is the 13-week (3-month) T-Bill. Everything downstream that labels this as the
2-year yield and computes the "10Y − 2Y" yield-curve spread — including the **recession
signal `(INVERTED)`** shown to the LLM — is comparing 10Y vs 3M. That produces a very
different curve (3M vs 10Y is often inverted even when 2Y vs 10Y is not).

**Fix:** Use a 2-year constant-maturity Treasury series. Yahoo does not expose ^TWO;
fetch from FRED (`DGS2`) or an equivalent source. Until a true 2Y source is wired up,
relabel the field as `treasury_3m` everywhere so the UI/LLM is not misled.

---

### BUG-F06 — HIGH: Price changes use raw Close, ignoring dividends/splits
**Primary Files:**
- `src/fin_trade/services/stock_data.py` (lines 226-245, `_calculate_change_pct`; lines 303, 322 current-price reads)
- `src/fin_trade/services/comparison.py` (line 478-480, benchmark cumulative return)

**Problem:** `yf.Ticker.history()` returns unadjusted `Close` unless `auto_adjust=True`
or `Adj Close` is used. All 5-day/30-day changes, RSI inputs, MA calculations, and the
benchmark "cumulative return" are computed off raw `Close`, which causes:

- Negative return spikes on dividend ex-dates (e.g., AAPL drops ~$0.25 the morning of
  its ex-date — that shows up as a fake 5-day loss).
- Completely wrong returns after stock splits.
- Benchmark total-return comparisons understate SPY's performance (SPY yields ~1.3%).

**Fix:** Use `yf.Ticker(...).history(period=..., auto_adjust=True)` so `Close` is
split- and dividend-adjusted. Where a true **total return** is needed (benchmark
comparisons), prefer the adjusted series explicitly.

---

### BUG-F07 — HIGH: No currency handling — FX-denominated holdings are summed as USD
**Primary Files:**
- `src/fin_trade/services/portfolio.py` (lines 199-205, `calculate_value`)
- `src/fin_trade/services/attribution.py` (lines 89-99)
- UI: `src/fin_trade/pages/portfolio_detail.py` (`_render_summary`, `_render_holdings`)

**Problem:** `yfinance` returns prices in each listing exchange's native currency (EUR
for `.DE`, GBP for `.L`, CAD for `.TO`, etc.). The code unconditionally adds them to
USD cash and formats everything with `$`. A portfolio with one BMW.DE (EUR) plus one
AAPL (USD) position produces an arithmetically invalid "total value".

**Fix:** Read `currency` from stored `SecurityService._full_info`, convert each
position to the portfolio's reporting currency (USD) using an FX rate from yfinance
(e.g., `EURUSD=X`), and surface FX P/L separately in attribution.

---

### BUG-F08 — HIGH: Execution price diverges from recommended/quoted price
**Primary Files:**
- `src/fin_trade/services/portfolio.py` (lines 258-262, `execute_trade`)

**Problem:** `execute_trade` calls `security_service.force_update_price(ticker)` to
*refetch* the last close right before computing `cost = price * quantity`. The price
the agent reasoned about — and the price the user reviewed in the Pending Trades UI
(which had to `get_price()` the ticker to build the summary) — is discarded. Result:

- User approves a BUY of 10 AAPL at quoted $180 ($1,800 cost); `force_update_price`
  returns $185; actual cost is $1,850. The cash summary shown in the UI is wrong.
- In "insufficient cash" edge cases, the validation (`cost > cash`) runs after the
  silent re-quote, which can flip validity between UI and execution.
- For multi-trade batches, later trades in the sorted list get different prices than
  earlier trades priced at the same button click.

**Fix:** Accept the quoted price as a parameter (captured at the time the user clicked
"Apply") and execute at that price. If the source wants to re-quote for freshness, show
the user the new quote and re-confirm before writing the trade.

---

### BUG-F09 — HIGH: `initial_investment` silently inflated by pending-trades flow
**Primary Files:**
- `src/fin_trade/pages/pending_trades.py` (lines 484-507, `_apply_pending_trades`)

**Problem:** For an "empty portfolio", the code adds `cash_needed + $100` to `state.cash`
to make BUYs fit, then sets `state.initial_investment = state.cash`. Two problems:

1. The extra $100 is silently added to the user's recorded initial investment, distorting
   percent-return calculations forever.
2. `initial_investment` is reassigned on *every* application that trips the
   `increase_cash_if_needed` branch; if the user applies pending trades in two batches
   from an empty portfolio, the second batch resets `initial_investment` to whatever
   `state.cash` happens to be at that moment.

**Fix:** (a) Do not inject a hidden buffer — fail loudly if cash is insufficient and
require the user to top up explicitly. (b) Set `initial_investment` exactly once, the
first time the portfolio transitions from "no trades" to "has trades".

---

### BUG-F10 — HIGH: Realized P/L is not tracked; percent-return has no TWR
**Primary Files:**
- `src/fin_trade/services/portfolio.py` (lines 207-216, `calculate_gain`; lines 299-317, SELL path)

**Problem:**
- `calculate_gain` is `(current_value - initial_investment) / initial_investment`. This
  is a money-weighted return that assumes zero external cash flows after inception, which
  the pending-trades path explicitly violates (BUG-F09). It is not a Time-Weighted Return
  (TWR) and cannot be fairly compared against benchmarks over the same period.
- On SELL, realized gain/loss is never stored. The model has no field for realized P/L,
  so the "Gain/Loss" metric mixes realized cash proceeds and unrealized mark-to-market
  without distinction, and there is no audit trail for taxable events.

**Fix:** (a) Compute return as TWR by sub-periodizing around deposits/withdrawals.
(b) Record realized P/L at the time of SELL (FIFO or WAC) into the trade record and
expose it separately in the UI.

---

### BUG-F11 — MEDIUM: `monthly` cadence uses a fixed 30-day delta
**Primary Files:**
- `src/fin_trade/services/portfolio.py` (line 231, `is_execution_overdue`)
- `src/fin_trade/pages/dashboard.py` (line 127, upcoming runs schedule)

**Problem:** `timedelta(days=30)` drifts vs. calendar months. Over 12 months the portfolio
will be scheduled about 5 days too often. If the strategy prompt tells the LLM it runs
monthly, the context/LLM assumptions and actual cadence diverge.

**Fix:** Use `dateutil.relativedelta(months=1)` or roll to the same day-of-month of the
next month.

---

### BUG-F12 — MEDIUM: RSI uses SMA, not Wilder's smoothing
**Primary Files:**
- `src/fin_trade/services/stock_data.py` (lines 208-224, `_calculate_rsi`)

**Problem:** The textbook RSI (Wilder, 1978) uses an exponentially smoothed average of
gains/losses with α = 1/period. The current code uses `rolling(window=period).mean()` —
a simple moving average. The two agree only on the first value; on day 15+ they drift,
so the "RSI 70/30" thresholds that the prompt hints at ("overbought/oversold") are
different from what any charting package would show for the same ticker.

**Fix:** Use Wilder's smoothing: `avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()`
(and the same for losses).

---

### BUG-F13 — MEDIUM: 52-week range uses at most 1 year of data (cutoff by `days`)
**Primary Files:**
- `src/fin_trade/services/stock_data.py` (lines 296-312)

**Problem:** When stored `high_52w`/`low_52w` from `SecurityService` is absent, the code
falls back to `df["High"].max()` / `df["Low"].min()` on a DataFrame that has already
been filtered by `get_history(days=days_needed)`. But:

- The CSV cache may have been fetched with `period="1y"` which yfinance interprets
  roughly as "most recent 1y of trading days" — on short holidays that is ~252 rows
  and can be less than 365 calendar days. The resulting `high/low` is *slightly*
  wrong but more importantly, inconsistent with the `fiftyTwoWeekHigh` from yfinance's
  `info` (which uses exactly 252 trading days).
- If `get_history` is later called with `days=30`, the high/low it computes is the
  30-day high/low mislabeled as 52w.

**Fix:** Compute 52w high/low always on ≥252 trading days of adjusted history; never
let the `days` argument shorten the window used for "52w" fields.

---

### BUG-F14 — MEDIUM: Contribution % explodes near zero total gain
**Primary Files:**
- `src/fin_trade/services/attribution.py` (lines 121-126, 187-189)

**Problem:** When total portfolio gain is a small non-zero number (e.g., $1), a holding
that contributed +$500 and another that contributed −$499 each get contribution
percentages of +50,000% / −49,900%. The UI will display these raw numbers in the
"Performance Attribution" table and dashboard.

**Fix:** Switch to gross-contribution basis (`unrealized_gain / sum(|unrealized_gain|)`)
or cap/format the display when `|total_gain|` is below a threshold.

---

### BUG-F15 — MEDIUM: Quantity typed as `int` in attribution and reflection
**Primary Files:**
- `src/fin_trade/services/attribution.py` (line 21, `HoldingAttribution.quantity`)
- `src/fin_trade/services/reflection.py` (line 24, `CompletedTrade.quantity`)
- `src/fin_trade/pages/dashboard.py` (column_config `format="d"` at line 296, 363)

**Problem:** `Holding.quantity` is `float` (models/portfolio.py:22) to support crypto and
fractional shares, but the dataclasses in attribution and reflection narrow it to `int`
and the dashboard renders it with integer format. For a BTC-USD holding of 0.1234 BTC,
this truncates to 0, which then zeroes the cost basis, current value, and realized
P/L in every downstream calculation.

**Fix:** Change both fields to `float` and use an 8-decimal format for crypto in the
dashboard, mirroring the `format_quantity()` helper.

---

### BUG-F16 — MEDIUM: Benchmark row in comparison table fabricates metrics
**Primary Files:**
- `src/fin_trade/services/comparison.py` (lines 435-457, benchmark column in `get_comparison_table`)

**Problem:** When benchmark data loads, the benchmark row is populated with hardcoded
strings: `"Volatility": "~15%"`, `"Sharpe Ratio": "N/A"`, `"Alpha": "0.0%"`,
`"Beta": "1.00"`, `"Days Active": "365"`. None of these are computed from actual data,
but they are presented in the same table as the portfolios' (allegedly) computed
metrics. Users will interpret them as measured.

**Fix:** Compute real benchmark metrics on the same date range used for each portfolio,
or leave the cells empty rather than display fabricated values.

---

### BUG-F17 — MEDIUM: Benchmark and portfolios use different date windows
**Primary Files:**
- `src/fin_trade/services/comparison.py` (lines 436-439 — `datetime.now() - 365 days` for benchmark table column; line 160-162 — `max(earliest_dates)` for the chart)
- `src/fin_trade/pages/portfolio_detail.py` (line 440 — `end_date = filtered_timestamps[-1]`)

**Problem:** On the comparison page, portfolio metrics use *each portfolio's* first
trade date, but the benchmark column always uses the last 365 calendar days. Portfolios
that have been running 2 years or 3 weeks are compared against the same fixed
benchmark window. Any "Alpha" derived from this is apples-to-oranges.

**Fix:** For every benchmark value in the table, recompute the benchmark return over the
exact `[first_trade_date, now]` window of the portfolio it sits next to.

---

### BUG-F18 — MEDIUM: SELL does not carry forward stop-loss / take-profit on partial fills in reflection
**Primary Files:**
- `src/fin_trade/services/reflection.py` (lines 225-233)

**Problem:** When a BUY is partially consumed by a SELL in
`_find_completed_trades`, the rebuilt Trade omits `stop_loss_price` and
`take_profit_price`, which causes downstream tools that inspect reflection trades
to lose the SL/TP context for the remaining open quantity.

**Fix:** Preserve all fields when rebuilding the partially-remaining buy.

---

### BUG-F19 — MEDIUM: Float comparison in SELL validation
**Primary Files:**
- `src/fin_trade/services/portfolio.py` (lines 299-304, 307-317)

**Problem:** `existing.quantity < quantity` and `new_qty > 0` use exact float math. For
crypto the typical flow "BUY 0.1, BUY 0.2, SELL 0.3" fails with
`Insufficient holdings: need 0.3, have 0.30000000000000004` (or leaves a 5e-17 residual
holding that is rendered as "0.00000000" in the UI but still counted).

**Fix:** Use a small absolute tolerance (e.g., round to 8 decimals for crypto, or use
`math.isclose(existing.quantity, quantity, abs_tol=1e-9)`) when comparing fractional
quantities, and prune holdings whose quantity is within tolerance of zero.

---

### BUG-F20 — MEDIUM: Win rate counts trades, not P/L magnitude
**Primary Files:**
- `src/fin_trade/services/comparison.py` (lines 237-283, `_calculate_win_rate`)

**Problem:** The FIFO matcher increments `total_closed += 1` once per SELL trade and
`profitable += 1` if the average-cost of all consumed BUYs is below the sell price.
Consequences:

- A single SELL that closes several tax lots is counted once even if some lots were
  winners and others losers.
- A small partial sell at a loss followed later by a large sell at a big win both count
  as "1 sell event" each — one win, one loss, 50% win rate — even though the dollar
  outcome was overwhelmingly positive.

**Fix:** Count per-tax-lot closures (FIFO), or display both "win rate" and "profit
factor = Σwinners / |Σlosers|" side-by-side.

---

### BUG-F21 — LOW: No transaction costs, no slippage, no margin interest
**Primary Files:**
- `src/fin_trade/services/portfolio.py` (lines 237-338, `execute_trade`)

**Problem:** All fills execute at `last_close` with no commission and no bid-ask
spread. `allow_negative_cash=True` lets a BUY overdraft cash indefinitely without
borrowing cost. For comparisons with real-world returns this is a systematic upward
bias, especially for high-turnover strategies.

**Fix:** Add a configurable commission model (fixed per trade + bp spread) and a cash
interest model (positive and negative rates). Apply on both execute and in the
historical value reconstruction used for metrics.

---

### BUG-F22 — LOW: `initial_investment or config.initial_amount` treats 0.0 as missing
**Primary Files:**
- `src/fin_trade/services/portfolio.py` (line 213)
- `src/fin_trade/services/comparison.py` (lines 66, 321)
- `src/fin_trade/pages/portfolio_detail.py` (lines 429, 487, 567)

**Problem:** The `or` idiom falls through to `config.initial_amount` when
`initial_investment == 0.0`, which is a legitimate state for a user who
started with a zero-cash portfolio (e.g., a watchlist being tracked). Rare, but
produces a misleading "return" number in that edge case.

**Fix:** `initial_investment if initial_investment is not None else config.initial_amount`.

---

### BUG-F23 — LOW: Earnings "today" is reported as 0 days away even after the event
**Primary Files:**
- `src/fin_trade/services/market_data.py` (lines 182-196, 231-232)

**Problem:** `(earnings_date - datetime.now()).days` returns 0 both for earnings five
hours from now and earnings reported this morning. Agents reading the context will
reason about "earnings today" for companies that already reported hours ago.

**Fix:** Use `(earnings_date - datetime.now()).total_seconds() / 3600` and treat
negative values (or earnings earlier than ~1h ago) as "past".

---

### BUG-F24 — LOW: Timestamps from `datetime.now()` mixed with yfinance UTC indices
**Primary Files:**
- `src/fin_trade/services/portfolio.py` (line 225, 320, 336)
- `src/fin_trade/services/stock_data.py` (line 178-179, 233, 293)
- `src/fin_trade/services/comparison.py` (line 115-116, 329, 367, 438)

**Problem:** Trade timestamps and `is_execution_overdue` use naive local time
(`datetime.now()`), while the price DataFrame index is tz-aware UTC and stripped to
naive only in `get_history`. Depending on user timezone, cutoff filters (e.g.,
"3 months ago") can include/exclude one extra trading day, and a trade entered late
local-evening can have a timestamp *after* the most recent market close in the price
history, breaking intraday value reconstructions.

**Fix:** Standardize on UTC. Store trade timestamps as UTC-aware ISO strings; convert
to local only at display time.

---

### BUG-F25 — LOW: Aggregate return in dashboard/overview is not AUM-weighted over time
**Primary Files:**
- `src/fin_trade/pages/dashboard.py` (line 53)
- `src/fin_trade/pages/overview.py` (line 89)

**Problem:** `gain_pct = total_gain / (total_value - total_gain) * 100` produces the
correct aggregated *current* return only if all portfolios started at the same time
with their current `initial_investment`. If one portfolio has been running 3 years and
another 3 weeks, this single number is almost meaningless. It is also sensitive to
one portfolio with a large loss dwarfing the others.

**Fix:** Show each portfolio's annualized return and compute an AUM-weighted annualized
return at the top, not the naive ratio of sums.

---

### BUG-F26 — LOW: Reflection "holding days" ignores hours
**Primary Files:**
- `src/fin_trade/services/reflection.py` (line 196)

**Problem:** `(trade.timestamp - buy.timestamp).days` floors to 0 for any trade held
less than 24 hours, which then feeds the "quick trades < 7 days" bias warning. Day
traders and intraday agents will always show `avg_holding_days = 0`.

**Fix:** Use `total_seconds() / 86400` and keep a float.

---

## Notes for reviewers

- Bugs F01, F02, and F05 are the most damaging numerically: they break the three pillars
  of the performance page (equity curve, Sharpe/β, macro context) and should be fixed
  before tuning any strategy prompt on reported performance.
- Bugs F07 and F09 are correctness-of-accounting issues that corrupt the stored state
  and therefore propagate silently to every future metric.
- Items marked LOW are real but either edge cases (F22, F23) or UX/labeling concerns
  (F25) — they are worth fixing but do not invalidate current results.
