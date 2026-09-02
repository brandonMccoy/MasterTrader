# MasterTrader — Automated Day-Trading Web App: Master Plan

Status: v1 draft (pre-gauntlet). See `docs/GAUNTLET_LOG.md` for critique rounds.
Date: 2026-09-02

---

## 0. Premise and honesty statement (read first)

**What is achievable with high confidence:** a system that *never* lets equity fall more
than 15% below its running peak, enforced mechanically and independently of any strategy.

**What is NOT achievable by anyone:** a guarantee of profit. Peer-reviewed evidence says
most retail day traders lose money after costs (roughly 64% in the Jordan & Diltz study;
higher in other markets), and the most-cited retail intraday strategies (opening-range
breakout on QQQ) lose nearly all of their paper edge once ~2¢/share of slippage is applied
(independent replication, see §12). "Perfection" in the sense of guaranteed growth is not
on the table and this plan does not pretend otherwise.

**Therefore the plan's actual objective is:**

> Maximize expected compounded growth of a fixed starting balance **subject to** a hard
> constraint that equity never drops more than 15% below its high-water mark, using only
> strategies that have survived a gated, out-of-sample, cost-inclusive validation pipeline,
> and with capital deployed only in proportion to *demonstrated live* edge.

The design principle that follows: **the risk system is the product; strategies are
replaceable plug-ins.** If no strategy passes the gates, the system trades nothing and
the capital is preserved. That outcome is a success under the constraint, not a failure.

**Interpretation of the 15% rule (stated assumption):** "not losing more than 15% of the
current total at any given time" is interpreted as *max drawdown from the equity
high-water mark ≤ 15%*, measured on total account equity (cash + marked positions),
continuously. The high-water mark ratchets up with new equity peaks. This is the strictest
reasonable reading.

---

## 1. Quality bar (the Gauntlet "bar")

A plan or implementation PASSES only if a hostile reviewer, given only the artifact, agrees
that all of the following hold:

| # | Bar item | Evidence required |
|---|----------|-------------------|
| B1 | Drawdown invariant is enforced by a layer that strategies cannot bypass, with broker-side protection as backup and a buffer for gaps/slippage. | Code path + fault-tree covering: bot crash, network loss, broker outage, data staleness, gap-down, partial fills, duplicate orders. |
| B2 | No live capital is risked on a strategy that has not passed all promotion gates (backtest → walk-forward → paper → micro-live). | Gate definitions with numeric thresholds and auto-demotion rules. |
| B3 | All backtests include a conservative cost model (spread, slippage, regulatory fees, data subscription) and out-of-sample validation resistant to overfitting. | Cost model constants; deflated-Sharpe / walk-forward procedure. |
| B4 | The system operates legally: no Terms-of-Service violations, correct account type, settlement rules honored. | Broker choice with official API; cash-vs-margin rules encoded. |
| B5 | Capital never exceeds the initial deposit plus realized gains; no external funds, no uncontrolled leverage. | No deposit code path; leverage cap enforced in risk gate. |
| B6 | Every component has a defined failure mode that resolves to "flat and halted", never "unknown exposure". | Reconciliation + watchdog + kill switch specified. |
| B7 | The web app gives a human full visibility and a one-click halt that works even if the trading engine is hung. | UI spec with independent kill path. |
| B8 | Roadmap is decomposed into steps each with an acceptance test. | Every step lists its verification. |

An external reference is used where possible: broker-grade risk controls (FINRA Rule 15c3-5
market-access controls as the model for pre-trade checks) and academic backtest hygiene
(Bailey & López de Prado, "The Deflated Sharpe Ratio"; walk-forward analysis).

---

## 2. Hard constraints (facts, verified 2026-09-02)

### 2.1 Broker: Robinhood is not viable; use Alpaca

- Robinhood has **no official API for stocks/options** and its Terms of Service prohibit
  automated/scripted access. Only a crypto API exists. Unofficial reverse-engineered
  libraries risk account termination. **Rejected.**
- **Alpaca** (alpaca.markets) is an API-first, commission-free US-equities broker with:
  official REST + WebSocket APIs, an official Python SDK (`alpaca-py`, Python ≥3.10),
  bracket/OCO/OTO/trailing-stop orders, a free real-time **paper-trading** environment,
  and ~200 requests/min rate limit. **Selected as primary broker.**
- Backup candidates if Alpaca fails us: Tradier (equities/options, 120 req/min),
  Interactive Brokers (most complete, hardest to integrate). Execution adapter is an
  interface so the broker is swappable.

### 2.2 Regulation: PDT rule retired; intraday margin framework

- SEC approved FINRA's amendment to Rule 4210 on 2026-04-14; effective **2026-06-04**.
  The Pattern Day Trader designation and the $25,000 minimum are gone. Day trades are no
  longer counted.
- Replacement: brokers monitor **intraday margin exposure** and set "Intraday Buying
  Power" dynamically. Alpaca implemented this on 2026-06-04.
- Margin and short selling at Alpaca still require **≥ $2,000 equity** (Reg T). Below
  that: 1× buying power, long-only, effectively a cash account.
- **Cash-account settlement (T+1):** selling a position bought with *unsettled* funds
  before those funds settle is a Good Faith Violation; three in 12 months → 90-day
  restriction. Implication for a sub-$2k account: the engine must track *settled* cash
  and only buy with settled cash, which caps deployable capital to roughly half the
  account on consecutive trading days.

### 2.3 Costs (must be in every backtest)

| Cost | Value | Notes |
|------|-------|-------|
| Commission | $0 | Alpaca |
| SEC Section 31 fee | $20.60 per $1M sold (from 2026-04-04) | sells only |
| FINRA TAF | $0.000195/share sold, cap $9.79/trade (2026) | sells only |
| Spread + slippage | **assume ≥ $0.02/share entry, $0.04/share on stop exits** for liquid names; scale up for illiquid | the replication that killed ORB used exactly these |
| Market data | Basic: free, **IEX only (~2% of volume)**. Algo Trader Plus: **$99/mo**, full SIP, unlimited WebSocket symbols | $99/mo is 1.2%/yr of a $100k account but **24%/yr of a $5k account** |

### 2.4 Market hours & order types

- Regular session 09:30–16:00 ET. Alpaca supports extended hours and 24/5 overnight,
  **limit orders only** outside regular hours. This system trades regular hours only and
  is **flat by 15:55 ET every day** (no overnight gap risk — the largest single threat
  to the 15% invariant).

### 2.5 Capital

- One initial deposit, amount TBD by owner (open decision D1). No deposit endpoint exists
  in the app. The risk gate's notional cap is derived from live account equity fetched
  from the broker, never from a config value, so it cannot be inflated.

---

## 3. System architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Web App (React + TypeScript, served by FastAPI)                     │
│  Dashboard · Equity/DD gauges · Positions · Orders · Strategy status │
│  Research reports · Audit log · KILL SWITCH (independent path)       │
└───────────────┬──────────────────────────────────────────────────────┘
                │ REST + WebSocket (auth: single-owner, TOTP)
┌───────────────▼──────────────────────────────────────────────────────┐
│  API Service (FastAPI)  — read models, control commands, alerts      │
└───────┬───────────────────────────────────────────┬──────────────────┘
        │ Postgres (Timescale ext) : bars, orders, fills, equity curve, │
        │ audit log, strategy state, gate results                        │
┌───────▼──────────────┐   ┌───────────────────────▼──────────────────┐
│  Trading Engine      │   │  Watchdog (separate process/container)   │
│  (Python, asyncio)   │   │  – heartbeat check on engine             │
│  ┌────────────────┐  │   │  – independent DD check via broker API   │
│  │ Data Feed      │  │   │  – on breach/hang: cancel-all, close-all │
│  │ (Alpaca WS)    │  │   │    directly at broker, page owner        │
│  ├────────────────┤  │   └──────────────────────────────────────────┘
│  │ Strategy Host  │  │
│  │ (plugins emit  │  │   ┌──────────────────────────────────────────┐
│  │  INTENTS only) │  │   │  Research Service (offline)              │
│  ├────────────────┤  │   │  backtester · walk-forward · cost model  │
│  │ RISK GATE      │◄─┼───│  gate evaluator · report generator       │
│  │ (sole path to  │  │   └──────────────────────────────────────────┘
│  │  broker)       │  │
│  ├────────────────┤  │
│  │ Execution      │  │   Broker adapter interface: Alpaca (paper/live)
│  │ Adapter        │──┼──►  swappable: Tradier / IBKR
│  ├────────────────┤  │
│  │ Reconciler     │  │
│  └────────────────┘  │
└──────────────────────┘
```

**Tech choices (rationale):**
- Python for engine/research: `alpaca-py` official SDK, pandas/numpy/vectorbt-style
  backtesting, same code for backtest and live (prevents research/production drift).
- FastAPI for API; React+TS for UI; Postgres+TimescaleDB for time series + audit.
- Single VPS/container host near US-East (Alpaca is US-East) plus the watchdog on a
  separate lightweight container. Docker Compose for the whole stack.
- Secrets: broker keys in environment/secret store, never in repo; **live keys are not
  present on the machine until the micro-live gate is passed** (paper keys only before).

**Non-negotiable structural rule:** strategies produce `Intent{symbol, side, qty_hint,
entry, stop, target, ttl}` objects. Only the Risk Gate can turn an Intent into an Order.
The Execution Adapter accepts orders only from the Risk Gate (enforced by type + module
boundary + test that greps for any other caller).

---

## 4. Risk system — the 15% invariant

### 4.1 Layered limits (all as fraction of *current* equity, so they scale as capital grows)

| Layer | Limit | Action when hit |
|-------|-------|-----------------|
| Per-trade risk (entry→stop distance × qty) | 0.5% of equity (0.25% while any strategy is in micro-live) | Intent rejected / qty reduced |
| Per-position notional | ≤ 25% of equity | qty reduced |
| Gross exposure | ≤ 100% of equity (no leverage) until Phase 6; never > 2× | Intent rejected |
| Concurrent positions | ≤ 3 | Intent rejected |
| Daily realized+unrealized loss | −2.0% of day-start equity | Flatten all, no new entries until next day |
| Weekly loss | −4.0% of week-start equity | Flatten, halt until Monday + manual ack |
| Drawdown from HWM: soft-1 | −5% | All risk limits ×0.5 |
| Drawdown from HWM: soft-2 | −8% | All risk limits ×0.25; only highest-ranked strategy trades |
| Drawdown from HWM: **hard halt** | **−10%** | Cancel all, flatten all, engine disabled; requires owner re-enable + written post-mortem |
| Absolute ceiling (watchdog, independent) | **−12%** | Watchdog closes everything at broker directly and pages owner |

The 5-point gap between the hard halt (−10%) and the requirement (−15%) is the buffer
for a worst-case adverse gap on a position while a stop is being executed, plus
slippage, plus simultaneous failure of the engine. With ≤ 3 positions each ≤ 25% of
equity, flat overnight, a 20% adverse intraday move on one position (rare for the
liquid universe) costs 5% of equity — the buffer holds even in that case.

### 4.2 Broker-side protection (backup if our process dies)

- Every entry is a **bracket order** (entry + stop-loss + take-profit legs held at the
  broker). If the engine dies, stops still exist at the broker.
- Stop legs use **stop-limit with limit = stop − k·ATR** for liquid names, or plain stop
  (market) when fill certainty beats price — decided per strategy in research, default
  plain stop for the invariant's sake.
- A daily **time-based flatten** (15:55 ET) is issued by both engine and watchdog.

### 4.3 Watchdog (independent process)

- Polls engine heartbeat every 5s and broker account every 15s.
- Triggers on: engine heartbeat missing > 30s with open positions; equity < HWM × 0.88;
  clock past 15:57 ET with open positions; data feed stale > 60s during session.
- Action: cancel all open orders, close all positions via broker API, write incident
  record, notify owner (push + email + SMS via Twilio/ntfy).
- Has its **own** broker credentials scoped to the same account (Alpaca supports
  multiple keys) so revoking the engine's key does not disable the watchdog.

### 4.4 Reconciliation

- Every 30s and after every fill event: compare local position/order book with broker's.
  Any mismatch → engine enters SAFE mode (no new entries) and alerts. Two consecutive
  mismatches → flatten.
- Idempotent orders via `client_order_id = hash(strategy, symbol, signal_ts)`; the
  adapter refuses to submit a duplicate id. Handles the "retry after timeout" double-order
  failure.

### 4.5 Data-integrity guards

- Stale quote (> 10s no update on a symbol in position during session) → treat as
  unknown, tighten to market-stop exit.
- IEX-only feed caveat: signals from ~2% of volume may diverge from tape by a spread.
  Mitigation: use **1-minute bars aggregated from trades** (less noise than quotes) and
  require confirmation on 2 consecutive bars; upgrade to SIP when equity ≥ $20k (then
  $99/mo < 0.5%/mo).

### 4.6 Kill switch

- UI button + CLI + a physical fallback (an HTTPS endpoint the owner can hit from a phone)
  → sets a **broker-side** "halt" by cancelling all orders and closing positions using the
  watchdog's key, independent of the engine. Verified in Phase 1 by killing the engine
  process mid-session in paper and confirming flat.

---

## 5. Strategy layer

### 5.1 Principles

1. A strategy is a pure function of (bars, features, account state) → Intents. No I/O.
2. The same strategy code runs in backtest, paper, and live (single event loop
   abstraction with a clock and a data source).
3. No strategy is "the" strategy. The system runs a **portfolio of small, uncorrelated,
   validated edges**, each with a capital allocation set by its live track record.
4. Anything that requires discretion, news reading, or sub-second latency is out of scope
   for a retail account on a 200 req/min API. We compete on discipline and cost control,
   not speed.

### 5.2 Candidate strategies (research queue, prior evidence noted)

| ID | Strategy | Prior evidence | Known weakness to test |
|----|----------|----------------|------------------------|
| S1 | **Opening Range Breakout on "stocks in play"** (top-N by relative volume ≥ 2× 14-day avg, price > $5, ATR filter; 5-min OR; entry on break with stop at OR opposite side / 10% ATR; exit at close or target) | Zarattini & Aziz (2023/24) on QQQ and on stock universe; independent QQQ replication matched the paper *before* costs | Costs erase QQQ version (break-even at 2.2¢/share slippage); 76% of PnL from 2022 volatility regime. Stocks-in-play version has wider moves so cost ratio is better — must be tested. |
| S2 | **Intraday momentum on SPY/QQQ with noise-band (Zarattini, Barbon, Aziz 2024)** | Paper: Sharpe ~1.3–2.4 (varies by version), beta ≈ 0, 2007–2024 | Leverage-dependent; costs; regime concentration; needs VIX-scaled sizing |
| S3 | **VWAP mean-reversion on large-cap liquid names** (fade extensions > 2σ from VWAP after 10:00 with volume exhaustion; target VWAP; stop 1×ATR) | Widely used; best-documented in institutional execution literature | Tail risk on trend days — requires trend-day filter (e.g. OR range vs ATR) |
| S4 | **Gap-and-go / gap-fade by gap size and pre-market volume** | Retail-popular; mixed academic support | Data-heavy on pre-market (needs SIP) |
| S5 | **Do nothing** (cash) | Guaranteed 0% drawdown | Allocation floor: this is the default when nothing else passes |

Order of research: S1 (stocks-in-play variant), S3, S2, S4. Long-only until margin
eligibility (≥$2k) and until a short variant passes gates separately.

### 5.3 Research protocol (applies to every strategy, no exceptions)

1. **Data:** Alpaca historical SIP minute bars (free for historical), ≥ 5 years,
   survivorship-bias-aware universe (use daily snapshots of listed symbols, not today's
   list). Store raw; derive features reproducibly.
2. **Cost model** (§2.3) applied to every fill. Slippage stress: run at 1×, 2×, 3× the
   base slippage. A strategy must remain profitable at 2×.
3. **Parameter search discipline:** ≤ 5 free parameters; coarse grids; report the *full
   grid surface*, not the best cell. Reject strategies whose profit lives in a narrow
   parameter island.
4. **Walk-forward:** anchored, 12-month train / 3-month test, rolling across the whole
   sample; concatenate out-of-sample segments only. All reported stats are OOS.
5. **Multiple-testing correction:** Deflated Sharpe Ratio (Bailey & López de Prado) with
   the number of trials honestly counted (every backtest run is logged to the DB with its
   config hash — the trial count is computed, not estimated).
6. **Regime breakdown:** yearly and by VIX tercile. Reject if > 50% of OOS profit is from
   one year.
7. **Monte Carlo on trade sequence:** bootstrap OOS trades 10,000× → distribution of max
   drawdown. The **95th-percentile max drawdown must be < 8%** at the intended risk
   level (leaving room under the 10% hard halt).
8. **Capacity/liquidity:** position size ≤ 1% of the symbol's 20-day median 1-minute
   volume at the entry minute; else scale down.

### 5.4 Promotion gates (numeric, automatic; a strategy's state is in the DB)

| Gate | From → To | Requirements |
|------|-----------|--------------|
| G1 | Idea → Backtested | Research protocol §5.3 complete; OOS Sharpe ≥ 1.0 at 2× slippage; DSR > 0.95 probability; MC 95% MDD < 8%; ≥ 300 OOS trades; no single year > 50% of profit |
| G2 | Backtested → Paper | Live paper on Alpaca for ≥ 40 trading days AND ≥ 60 trades; paper equity curve within the backtest's MC 80% band; fill-quality log shows slippage ≤ modeled |
| G3 | Paper → Micro-live | Owner approval + live keys installed; allocation = 10% of equity, per-trade risk 0.25% |
| G4 | Micro-live → Full | ≥ 40 trading days AND ≥ 60 live trades; realized slippage ≤ 1.5× modeled; live Sharpe ≥ 0.7; MDD < 5%; then allocation ramps 10→25→50→100% of its target, each step after 20 more days without a gate violation |
| Demotion | Any → previous | 20-day rolling Sharpe < 0 or live MDD > MC 95% band or slippage > 2× modeled → step down one level automatically and alert |

### 5.5 Allocation across strategies

- Target weights by **fractional Kelly (¼ Kelly)** computed on OOS trade distributions,
  capped so the sum of per-strategy risk stays under the global limits (§4.1).
- Correlation guard: if two strategies' daily PnL correlation > 0.6 over 60 days, cap
  their combined allocation to that of one.
- Rebalance weekly; changes limited to ±10 percentage points per week.

---

## 6. Growth mechanics ("grow it to spend more")

- All limits are percentages of **live equity**, so position sizes rise automatically as
  the account grows and fall as it shrinks. No manual "level up".
- HWM ratchets; the drawdown ladder (§4.1) is always measured from the peak, so after
  growth the system protects the *new* higher balance.
- Fixed costs (SIP data $99/mo) are enabled by equity thresholds (§4.5), not by hand.
- Leverage (up to 2× intraday, only within Alpaca's Intraday Buying Power) is unlocked
  only in Phase 6 and only for strategies at G4 with ≥ 6 months live history; even then
  the gross-exposure cap is 1.5× and the per-trade risk stays 0.5%.
- Compounding is not free: expected drawdown scales with risk per trade. The Monte
  Carlo in §5.3 is re-run monthly on live trades to confirm the 95% MDD still fits under
  the hard halt; if not, per-trade risk is cut.

---

## 7. Web app specification

Single owner, authenticated (password + TOTP), served over HTTPS behind a reverse proxy.

**Pages**
1. **Overview** — equity, HWM, current drawdown as a gauge against the 5/8/10/12/15 ladder,
   day PnL, week PnL, engine state (RUNNING / SAFE / HALTED), data-feed health, last
   heartbeat, watchdog status. Big red **HALT** button (independent path, §4.6).
2. **Positions & Orders** — live table with entry, stop, target, unrealized PnL, time in
   trade, strategy id; per-position "close now".
3. **Strategies** — each strategy's gate state, allocation, live vs backtest overlay,
   rolling Sharpe, slippage realized vs modeled, promotion/demotion history, buttons for
   owner-gated actions (approve G3, pause).
4. **Research** — list of backtest runs (config hash, dates, OOS metrics, DSR, MC MDD),
   grid surfaces, walk-forward charts; "promote to paper" action if G1 passed.
5. **Journal / Audit** — every Intent, gate decision, order, fill, rejection reason,
   reconciliation result, incident; exportable CSV.
6. **Settings** — notification channels, session times, read-only display of limits
   (limits are changed only through a versioned config file committed to the repo, so
   changes are auditable; the UI never edits limits).

**Real-time:** WebSocket push from API service for positions/equity; 1s refresh.

**Notifications:** push (ntfy) + email on: any halt, any gate change, daily summary at
16:05 ET, watchdog action, reconciliation mismatch.

---

## 8. Operations

- Docker Compose: `engine`, `watchdog`, `api`, `web`, `db`, `research` (on-demand).
- Deploy on a small US-East VPS; engine and watchdog on the same host but separate
  containers with separate credentials; DB backups nightly to object storage.
- Time sync (chrony) enforced; engine refuses to start if clock skew > 500ms.
- Structured JSON logs; every order lifecycle event is an audit row.
- Session calendar from Alpaca `/calendar` endpoint; engine does not trade on early-close
  days after 12:55 ET, or on days the calendar marks closed.
- Weekly automated report: PnL, DD, per-strategy stats, slippage, cost totals,
  reconciliation incidents.
- Runbooks: broker outage, data outage, engine crash with open positions, mismatched
  fill, key rotation.

---

## 9. Testing strategy

- **Unit:** risk gate (every limit, boundary values, scaling under drawdown ladder);
  order id idempotency; settled-cash tracker; calendar handling.
- **Property-based:** random sequences of fills/prices must never produce a state where
  drawdown > 10% without a halt being emitted (Hypothesis).
- **Simulation harness:** replay historical days through the *live* engine code with a
  fake broker that supports partial fills, rejects, latency, and gaps; assert invariant.
- **Chaos tests (paper):** kill engine mid-trade → watchdog flattens within 60s; cut
  network → SAFE mode; duplicate fill event → no double position; stale data → exit.
- **Broker sandbox tests:** paper API end-to-end nightly.
- **Backtest reproducibility:** each research run stores config hash + data snapshot id;
  re-running yields identical metrics.

---

## 10. Roadmap (phases → steps → sub-steps, each with acceptance test)

### Phase 0 — Decisions & accounts (owner, ~1 day)
- 0.1 Confirm starting capital (D1) and account type: if < $2,000 → cash-account mode,
  long-only, settled-cash tracking. *Accept:* value recorded in `docs/DECISIONS.md`.
- 0.2 Open Alpaca account; create **paper** API keys only. *Accept:* `GET /v2/account`
  on paper endpoint returns 200 from the dev machine.
- 0.3 Choose notification channel (ntfy topic / email). *Accept:* test message received.

### Phase 1 — Skeleton + risk gate + kill switch (build first, before any strategy)
- 1.1 Repo scaffold: `engine/`, `watchdog/`, `api/`, `web/`, `research/`, `infra/`;
  Docker Compose; Postgres+Timescale; CI running lint + tests. *Accept:* `docker compose
  up` green; CI green.
- 1.2 Broker adapter interface + Alpaca paper implementation (account, positions,
  orders, bracket, cancel-all, close-all, calendar, clock). *Accept:* integration test
  places and cancels a paper bracket order.
- 1.3 Risk Gate module with all §4.1 limits, config from versioned YAML, equity from
  broker only. *Accept:* unit tests for each limit incl. drawdown ladder scaling;
  property test in §9.
- 1.4 Watchdog with independent key; heartbeat; DD check; flatten path. *Accept:* chaos
  test — kill engine with a paper position open → flat within 60s, incident row written.
- 1.5 Reconciler + idempotent order ids. *Accept:* injected duplicate submit → one
  order; injected mismatch → SAFE mode.
- 1.6 Minimal web UI: overview page with equity/DD gauge, engine state, HALT button
  wired to the watchdog path. *Accept:* pressing HALT with engine hung flattens paper
  account.
- 1.7 Time-based flatten 15:55 ET + calendar/early-close handling. *Accept:* simulated
  clock test.

### Phase 2 — Data & research infrastructure
- 2.1 Historical loader: Alpaca SIP minute bars, 5+ years, chosen universe (Russell 1000
  + liquid ETFs), daily universe snapshots. *Accept:* row counts, gap report, checksum.
- 2.2 Event-driven backtester sharing the engine's strategy interface; fill model with
  spread/slippage/fees per §2.3; partial fills. *Accept:* known toy strategy reproduces
  hand-computed PnL to the cent.
- 2.3 Walk-forward runner, DSR calculator, Monte Carlo MDD, grid-surface reports, trial
  registry (every run logged). *Accept:* synthetic random strategy yields DSR ≈ 0 and
  is auto-rejected.
- 2.4 Research page in UI listing runs and gate status. *Accept:* run visible with
  metrics.

### Phase 3 — Strategy research (S1, then S3, S2, S4)
- 3.x For each strategy: implement → grid → walk-forward → costs stress → regime & MC →
  G1 decision recorded. *Accept:* gate report in DB; either PASS with all numbers or
  FAIL with reason. **No shortcut: a FAIL is a valid outcome.**

### Phase 4 — Paper trading
- 4.1 Strategy host runs G1-passed strategies on paper with full risk gate. *Accept:*
  40 trading days, ≥ 60 trades, reconciliation clean, slippage log vs model.
- 4.2 Fill-quality analysis; if realized slippage > modeled, revise cost model and
  re-run G1. *Accept:* report.
- 4.3 Chaos tests re-run in paper monthly. *Accept:* all pass.

### Phase 5 — Micro-live
- 5.1 Owner approves G3; fund account; install **live** keys (engine + watchdog).
  *Accept:* live account equals starting capital; no deposit code exists (grep test).
- 5.2 Trade at 10% allocation / 0.25% risk for ≥ 40 days. *Accept:* G4 metrics met or
  auto-demotion fired.
- 5.3 Weekly review with the owner; post-mortem for every halt.

### Phase 6 — Scale
- 6.1 Ramp allocation per G4 schedule. 6.2 Add second strategy once G4 for the first.
  6.3 SIP data at ≥$20k equity. 6.4 Margin/short and ≤1.5× intraday only after
  6 months live and a separate gate pass. *Accept:* each ramp step logged with the
  20-day clean window evidence.

---

## 11. Open decisions for the owner (cannot be resolved from the repo)

| ID | Decision | Default assumed if unanswered |
|----|----------|-------------------------------|
| D1 | Starting capital amount | Plan is written to work from $1,000 upward; features gated by equity thresholds |
| D2 | Willingness to pay $99/mo for SIP data before $20k equity | No — IEX until threshold |
| D3 | Notification channel(s) | ntfy + email |
| D4 | Hosting: owner's VPS vs. managed | Small US-East VPS (Docker Compose) |
| D5 | Whether shorting is ever allowed | Only after Phase 6 gate |

---

## 12. Sources consulted (2026-09-02)

- Gauntlet Loop process: github.com/trilwu/gauntlet-loop-skills, github.com/NicholasSpisak/gauntlet-loop
- Robinhood API status: github.com/sanko/Robinhood (unofficial), bitget.com/wiki, apidog.com/blog/robinhood-api
- FINRA PDT retirement: sec.gov SR-FINRA-2025-017 approval; finra.org Regulatory Notice 26-10; schwab.com; tastytrade.com; tradezero.com
- Alpaca intraday margin, $2k margin minimum, 24/5 limit-only, paper trading mechanics: alpaca.markets blog/support, github.com/alpacahq/alpaca-docs, github.com/alpacahq/alpaca-py
- Alpaca data plans & IEX coverage: alpaca.markets/data, docs.alpaca.markets market-data-faq, forum.alpaca.markets
- Fees: FINRA Information Notice 2026-03-17 (Section 31 = $20.60/M); FINRA TAF 2026 ($0.000195/share)
- Day-trader profitability: Jordan & Diltz, "The Profitability of Day Traders", FAJ 2003; Chague, De-Losso & Giovannetti (Brazil)
- ORB / intraday momentum: Zarattini & Aziz (SSRN 4729284, 4416622); Zarattini, Barbon & Aziz 2024 (SPY); independent replication github.com/giovannibrusco/zarattini-2023-orb-qqq (costs break even at ~2.2¢/share)
- Backtest hygiene: Bailey & López de Prado, "The Deflated Sharpe Ratio" (2014)
