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

## Round 2 — plan v2

_(pending)_
