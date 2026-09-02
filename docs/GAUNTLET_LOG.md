# Gauntlet Log — MasterTrader plan

Process followed: Gauntlet Loop (set bar & budget → split → build → blind critique →
fix → repeat → smooth → report). Critics are fresh-context agents that see only the
artifact and the bar, never the author's reasoning. Verdicts are evidence-only.

**Bar:** `docs/TRADING_PLAN.md` §1 (B1–B8).
**Budget:** max 3 critique rounds × 3 critics, plus 1 smoothing pass.
**Exit:** all bar items PASS, or two consecutive rounds with no material change, or
budget exhausted. Remaining gaps are documented, not hidden.

Critic roles (each round uses new instances):
- C-RISK: quant risk officer — drawdown math, research hygiene, growth adequacy
- C-ENG: reliability engineer — fault tree, enforceability, roadmap testability
- C-REG: brokerage/compliance — legal operation, settlement, margin, costs, microstructure

---

## Round 1 — plan v1 → v2

**Verdicts:** every bar item graded FAILED (C-RISK: B1, B2, B3, B5, B6, GROWTH; C-ENG: B1,
B6, B7, B8; C-REG: B3, B4, B5).

**Findings accepted and applied in v2 (by theme):**
- *Drawdown math:* static 25%-notional caps allowed breaches at −4.9% DD with three
  positions (−15.4% in a crash-open case; −15.25% on a single halt-reopen). Replaced with
  a stress-loss budget `L = max(N·s) + 0.10·rest ≤ 0.15 − DD − 0.01`, instrument stress
  factors 0.10/0.25/0.50, trimming of existing positions when DD grows, single-name cap
  10%, one position per symbol, pending orders count as exposure, absolute sanity caps,
  sizing on day-start equity minus accrued fees.
- *Independence:* engine + watchdog on one host was a single point of failure; bracket
  DAY legs expire at 16:00. Added off-host state-independent flattener (15:57 / 09:31 /
  −12%), GTC child legs, external dead-man pings, latching HALTED flag persisted in three
  places, engine recovery state machine, verified flatten loop with broker readback,
  position-protection invariant, rate-limit budgeting, paper/live identity assertion,
  deploy guard.
- *Enforceability:* "grep for callers" is not enforcement in Python. Strategies now run in
  a no-key, no-egress container with a malicious-strategy acceptance test plus
  `import-linter`.
- *Broker facts (verified after critique):* Alpaca has no cash accounts (sub-$2k =
  limited margin, unsettled funds reusable, no GFV) — v1's settled-cash mode was wrong
  and is now adapter-conditional only; sell stops are not converted to stop-limit (buy
  stops are); broker-side `max_margin_multiplier=1` / `no_shorting=true` /
  `suspend_trade` exist and are now asserted every cycle; multi-key support is unverified
  → Phase 0.2 test. Added intraday margin-call regime, $2k as a live threshold with
  hysteresis, LULD halts as a first-class state, tick rounding, integer-qty checks,
  asset-master refresh, opening-auction rule, SSR for any future shorting, cash-flow
  detection via account activities, flow-adjusted HWM from daily closes.
- *Research hygiene:* per-share slippage constant replaced with NBBO-spread-based model
  (+CAT fee, +tax); explicit no-look-ahead fill rules; per-fold parameter selection;
  once-only 12-month holdout; trial registry keyed by `(code_hash, config_hash)` with the
  backtester refusing unregistered runs; Sharpe defined; regime gate strengthened;
  RVOL defined at 09:35; survivorship source made an owner decision (D7) that blocks
  Track B.
- *Gates:* G1 trade-rate (0.3/day) was inconsistent with G2/G4 (1.5/day) — added a
  0.75 trades/day floor and lowered live-window trade minimums to 30; paper slippage was
  vacuous evidence — replaced with counterfactual SIP re-pricing and a 95% live-vs-SIP
  signal-agreement test; rolling-Sharpe demotion (SE ≈ 3.5) replaced with a sequential
  test against the MC band; demotion mechanics, hash-keyed strategy identity,
  per-strategy micro-live risk, G3 checklist, portfolio gate before a second strategy,
  derived `r*` instead of fixed 0.5%.
- *Growth economics:* fixed-cost hurdle made explicit; minimum viable capital table
  (≥ $5k Track A; Track B ≥ $25k); shutdown rule; after-tax reporting; leverage deleted
  outright (arithmetically incompatible with 15%); data plan restructured into Track A
  (ETFs on IEX) and Track B (single names, SIP required) because the free feed cannot
  compute consolidated RVOL or stream > 30 symbols.
- *Scope:* Timescale, React SPA, Kelly allocation, Russell-1000 universe deferred; realistic
  calendar stated (~8–10 months to first full allocation).

**Findings rejected or modified:** C-REG's claim that Alpaca converts sell stops was
checked and found to apply to buy stops only (documented in §4.2). C-RISK's suggestion
of ETF exposure to ~100% notional was accepted; its 1.5%-max `r*` retained as a ceiling
under the MC constraint.

---

## Round 2 — plan v2 → v3

**Verdicts:** C-RISK: B1 FAIL, B2 FAIL, B3 FAIL, B5 **PASS** (residuals), B6 FAIL, GROWTH
FAIL. C-ENG: B1, B6, B7, B8 FAIL. C-REG: B3, B4, B5 FAIL. First PASS recorded (B5 by
C-RISK); every other item still had mechanism-level defects.

**Findings accepted and applied in v3:**
- *Budget formula:* v2's `max(N·s) + 0.10·rest` breached 15% with two simultaneous halts at
  any DD ≥ −5%, and `s` values had zero margin (s_ETF 0.10 = the 2020-03-16 move). Now
  `L = Σ N_i·s_i` with s = 0.20 SPY/QQQ (Level-3 breaker bound), 0.25 other ETFs, 0.40
  large caps, **1.00** in-play names (multi-day halt reopens); reserve 0.015; `DD =
  max(now, at open)`; Intent admission needs a ≤ 5 s account snapshot; no entries at −9%;
  1 position at −8%; watchdog −10%, flattener −11%; a defined post-halt path (terminal or
  recovery mode with its own arithmetic). Consequence stated plainly: single-name exposure
  is capped at ≈ 13% of equity in total.
- *Broker semantics:* `suspend_trade` would have blocked our own exits → set only after
  readback 0/0, every exit path un-suspends first, probed in a new Phase 0.6 step producing
  `docs/BROKER_FACTS.md`; bracket TIF applies to all legs → DAY brackets + standalone GTC
  stop for halted names; cancel-all stripped the protective stop on a halted name → fixed;
  every sell path is cancel-then-submit (403 held-qty is not an incident); trim procedure
  defined; market-wide L1/L2/L3 rules added (L3 does not reopen); `dtbp_check` dropped
  (deprecated 2026-06-03); margin-call rows and $2k hysteresis removed as dead code at
  multiplier 1; halt detection via the `statuses` stream; rate limit is per account →
  per-process budgets; Basic plan allows one WebSocket → watchdog uses REST for liveness.
- *Isolation & arbitration:* Intent queue was an unspecified deserialization boundary →
  JSON over a unix socket with a closed schema, two Docker networks, hardened container,
  extended malicious-strategy test; three flatten actors could live-lock → broker-visible
  `FLAT-<actor>-` markers with priority; watchdog/flattener actions latch `HALTED_TODAY`;
  RUNNING reachable only from the 09:15 go/no-go; 2 crashes → HALTED; HALTED = OR of three
  stores with the watchdog as the sole re-enable consumer; heartbeat carries reconcile and
  readback timestamps; host B health polled by the engine; AM flattener pass moved to
  09:30:05–09:30:25 with engine entries from 09:32.
- *Flows & HWM:* activities lag a day → per-cycle cash identity; block-list replaced by an
  allow-list (`FILL, FEE, INT*, DIV*`); raw portfolio history is not flow-adjusted → demoted
  to an alert-only cross-check; proportional withdrawal formula with a unit test.
- *Halt path:* separate no-key halt-receiver containers writing a file; valid tokens never
  rate-limited; 202 + incident id + ntfy confirmation; phone-originated acceptance test;
  watchdog writes its own readback to the dashboard.
- *Gates & research:* Sharpe ≥ 1.0 line deleted in favor of DSR with N = walk-forward runs;
  one Monte Carlo definition (day-block bootstrap, 252 days, ladder simulated) shared by G1
  and `r*`; pointwise bands replaced with simultaneous-coverage envelopes at n ≥ 10 with
  50% shrinkage; G2/G4 labelled plumbing gates; units defined (allocation, target, clean
  day, R); signal agreement measured per minute; holdout family defined; ≥ 7 years of data
  for the regime rule; stop-distance floor enforced by the gate; Track B stress-factor
  validation added.
- *Economics:* v2's 9–35% gross was inconsistent with the plan's own MC-implied risk →
  recomputed as `Sharpe × r_eff × √trades` giving 4–16%; tax applied to gross with fixed
  costs non-deductible; $3k loss cap and TTS unlikelihood stated; single minimum-capital
  numbers ($10k Track A, $70k Track B); shutdown rule rewritten to run only after 12 months
  at full allocation; micro-live uses `max(1 share, 10%)` with SPLG/QQQM.
- *Roadmap:* fake broker (1.2b) and test fixtures so every Phase-1 acceptance test is
  runnable; Phase 0.6 probe; VPN/TLS/halt-receiver/backup/rotation steps; synthetic-strategy
  pass rate ≤ 0.5%; calendar 10–12 weeks for Phase 1, 11–13 months to full allocation.

**Rejected/modified:** C-RISK proposed s = 0.75 for in-play names with a $2B cap floor;
v3 uses 1.0 with no floor (covers −90% reopens, simpler). C-ENG proposed dropping the
serial `pending_cancel` wait entirely; v3 keeps a bounded wait only in the per-symbol
cancel-then-submit path because Alpaca rejects a second sell against held quantity.

---

## Round 3 — plan v3

_(pending)_
