# MasterTrader — Automated Day-Trading Web App: Master Plan

Status: **v2** (after Gauntlet round 1). Critique history: `docs/GAUNTLET_LOG.md`.
Date: 2026-09-02

---

## 0. Premise and honesty statement (read first)

**Achievable with high confidence:** a system whose account equity never falls more than
15% below its high-water mark, enforced by arithmetic (a stress-loss budget), by
broker-side configuration, and by an off-host flattener that does not depend on the
trading engine being alive.

**Not achievable by anyone:** a guarantee of profit. Peer-reviewed evidence: ~64% of US
day traders lose money after costs (Jordan & Diltz 2003); in Brazil 97% of persistent
day traders lost (Chague et al.). The most-cited retail intraday strategy (opening-range
breakout on QQQ) loses nearly all its paper edge at ~2.2¢/share slippage in an
independent replication. Read §6.1 for the arithmetic: below roughly **$7,500** the
fixed costs of running this system exceed any plausible edge, and the honest expected
outcome for most strategy candidates is "does not pass the gates."

**The objective is therefore:**

> Maximize expected after-tax compounded growth of one fixed starting balance,
> **subject to** equity never dropping more than 15% below its high-water mark, trading
> only strategies that survived a pre-registered, cost-inclusive, out-of-sample pipeline,
> with capital deployed in proportion to demonstrated *live* edge.

**Design principle:** the risk system is the product; strategies are replaceable
plug-ins. If nothing passes the gates, the system holds cash. Under the constraint that
is a success.

**Interpretation of the 15% rule (stated assumption):** maximum drawdown from the
high-water mark (HWM) ≤ 15%, where HWM = the highest *daily closing* equity (the
account is flat at every close, so this is unambiguous), adjusted for external cash flows
(§4.7), and drawdown is checked continuously against broker-reported equity.

---

## 1. Quality bar (the Gauntlet "bar")

A hostile reviewer, given only this document, must agree all of these hold:

| # | Bar item | Evidence required |
|---|----------|-------------------|
| B1 | Drawdown invariant is enforced by a layer strategies cannot bypass, with broker-side backup and an off-host backstop, and the buffer arithmetic holds under stated worst cases (halts, gaps, correlated crash, dead host). | §4.1 formula and worked cases; §4.3–4.6 mechanisms. |
| B2 | No live capital is risked on a strategy that has not passed all promotion gates; gates are numeric, consistent, and not noise-driven. | §5.4. |
| B3 | Backtests are cost-inclusive (spread-aware slippage, all fees, fixed costs, tax) and overfitting-resistant (per-fold selection, once-only holdout, registered trials). | §2.3, §5.3. |
| B4 | The system operates legally and within the broker's actual rules (account model, margin calls, halts, order types, tick sizes, SSR, asset master). | §2.2, §2.4, §4.8. |
| B5 | Notional never exceeds equity; no external funds; leverage and shorting are disabled at the **broker**, and inflows are detected. | §2.5, §4.7. |
| B6 | Every component's failure resolves to "flat and halted", never "unknown exposure"; halt is latching; restart cannot re-arm trading. | §4.9 fault table, §4.10 state machine. |
| B7 | Owner has full visibility and a halt that works when the engine, API, or host is dead. | §7. |
| B8 | Roadmap steps each have a runnable, falsifiable acceptance test; scope is realistic for one developer. | §10. |

Reference standards: FINRA Rule 15c3-5 (pre-trade market-access controls) as the model
for the risk gate; Bailey & López de Prado (Deflated Sharpe Ratio) and walk-forward
analysis for research hygiene.

---

## 2. Hard constraints (facts verified 2026-09-02; unverified items marked)

### 2.1 Broker: Robinhood is not viable; Alpaca is primary

- Robinhood: no official stock/options API; Terms of Service prohibit automation; only a
  crypto API exists. **Rejected.** The owner can still *watch* the Alpaca account in
  Alpaca's own web dashboard (positions, orders, activity, "liquidate all", "suspend
  trading"), which is the Robinhood-like view. **Manual trades in the live account will
  trip reconciliation and be flattened by the engine** (§4.5); the dashboard is for
  viewing and emergency liquidation only.
- Alpaca: API-first, commission-free, official `alpaca-py` SDK (Python ≥ 3.10), REST +
  WebSocket, bracket/OCO/OTO orders, free paper environment, ~200 req/min/key.
- Backups: Tradier (offers true cash accounts, 120 req/min), Interactive Brokers.
  Broker adapter is an interface; anything Alpaca-specific in this plan is marked.

### 2.2 Alpaca account model and regulation

- **Alpaca does not offer cash accounts.** Every account is a margin account. Below
  $2,000 equity it is a *limited-margin* account: 1× buying power, no shorting,
  **unsettled proceeds are reusable, no Good-Faith-Violation regime.** The settled-cash
  ledger from v1 is therefore *not* Alpaca's operating mode; it is retained only as an
  adapter-conditional module for a true cash-account broker (§4.8.6).
- FINRA retired the Pattern Day Trader rule effective **2026-06-04** (SEC approval
  2026-04-14). No day-trade counting, no $25k minimum. Replacement: brokers monitor
  **intraday margin exposure**; Alpaca publishes "Intraday Buying Power" that updates
  through the day. Exceeding it creates an **intraday margin call**; repeated unmet calls
  within five business days can restrict the account for 90 days. This account has no
  deposit path, so the only cure is liquidation (§4.9).
- **$2,000 is a live state, not a one-time decision.** Margin features (2× RegT BP,
  shorting) switch off when equity crosses below $2,000 intraday. The risk gate reads
  equity every cycle and applies hysteresis: margin-dependent features (Phase 6 shorting
  only) require equity ≥ $2,300; below $2,100 any short is flattened pre-emptively.
- Broker-side configuration (Alpaca `PATCH /v2/account/configurations`, fields verified):
  `max_margin_multiplier = "1"`, `no_shorting = true`, `dtbp_check = "both"` until Phase
  6. The reconciler asserts these every cycle and halts on mismatch. This makes B5 a
  broker-enforced fact, not a code promise.
- Multiple simultaneous API key pairs per live account: **unverified.** Phase 0.2 tests
  it. If only one key pair can exist, the off-host flattener shares it and independence
  comes from separate hosts/processes, not separate keys (§4.4).

### 2.3 Costs (every one is in the backtester and the weekly report)

| Cost | Value | Where applied |
|------|-------|---------------|
| Commission | $0 | — |
| SEC Section 31 | $20.60 per $1M sold (from 2026-04-04) | sells |
| FINRA TAF | $0.000195/share sold, cap $9.79/trade | sells |
| FINRA CAT fee pass-through | ~$0.000001–0.000003/share (Alpaca fee schedule; small, included for completeness) | all executions |
| **Slippage (entry)** | `max($0.02/share, half NBBO spread at the fill minute from historical SIP quotes) + 5 bp impact` | every fill |
| **Slippage (stop exit)** | `max($0.04/share, full NBBO spread at the fill minute) + 10 bp` | every stop fill |
| Stress | run at 1×, 2×, 3×. Must pass G1 at **2×** for ETFs/S&P 500 names, at **3×** for any symbol under $20 or with 20-day median spread > 5 bp | G1 |
| Market data | Basic: free, IEX only (~2% of volume), ~30-symbol WebSocket cap. Algo Trader Plus: **$99/mo**, full SIP, unlimited symbols | §2.4 |
| Hosting | ~$10–20/mo (two small VPS) | §6.1 |
| **Tax** | short-term capital gains at ordinary rates (+3.8% NIIT, + state); wash-sale deferral across year-end from re-trading the same names | §6.1 after-tax table; D6 |

### 2.4 Data plan (a design decision, not a budget footnote)

Research uses historical SIP minute bars and quotes (free). Live signals on the Basic plan
come from IEX (~2% of tape) with a ~30-symbol stream cap. Consequences:

- Consolidated relative-volume scans across hundreds of names (needed by S1/S4) **cannot
  be computed** on the Basic plan.
- IEX prints on mid-cap names can be tens of seconds apart; a research/production feed
  mismatch is invisible in paper.

Rule: **paper must run on the same feed as live for that strategy.** Two tracks:

| Track | Strategies | Feed | Precondition |
|-------|-----------|------|--------------|
| A: index ETFs (SPY, QQQ, IWM, DIA and sector ETFs) | S2, S3-ETF | IEX is adequate (SPY/QQQ trade heavily on IEX); nightly SIP replay must agree with live signals ≥ 95% (§5.4 G2) | equity ≥ $5k |
| B: single names ("stocks in play") | S1, S4, S3-stocks | SIP required | SIP subscribed **before** paper starts; equity ≥ $25k unless owner accepts the cost (D2) |

Regular session only (09:30–16:00 ET). No orders before 09:30:30 ET, no `opg`/`cls`
TIF, no extended hours. Flat by 15:55 ET (engine) / 15:57 ET (watchdog + off-host).

### 2.5 Capital

- One initial deposit (D1). No deposit code exists in the app, but that is not the
  control: the reconciler reads `GET /v2/account/activities` for cash-flow types
  (`CSD`, `CSW`, ACH/wire) every cycle. **Any inflow after go-live → HALT + alert**;
  any withdrawal is expected only after an owner-acknowledged halt (tax payments) and is
  applied to the HWM ledger (§4.7).
- Equity used by every limit = broker-reported `equity − accrued_fees`, never a local
  mark. Sizing uses **day-start (flat) equity**, so intraday unrealized gains are never
  sized on.

---

## 3. System architecture

```
   Owner's phone/laptop ── WireGuard/Tailscale only ──► Dashboard (API + UI, NO broker keys)
   Owner's phone ─────────── public HTTPS, bearer token ──► Watchdog  POST /halt   (halt only)
   Owner's phone ─────────── public HTTPS, bearer token ──► Flattener POST /halt   (halt only)
   Owner ─────────────────── Alpaca web dashboard ────────► Liquidate all / suspend trading

 HOST A (US-East VPS)                                     HOST B (different provider)
 ┌──────────────────────────────────────────────┐        ┌──────────────────────────┐
 │ engine container (broker key K1)             │        │ off-host FLATTENER       │
 │  data feed ─► strategy host (separate        │        │  (broker key K2 or K1)   │
 │              container, NO keys, NO egress)  │        │  15:57 ET: cancel+close  │
 │              ─Intents via local queue─►       │        │  09:31 ET: close if any  │
 │  RISK GATE ─► execution adapter ─► Alpaca    │        │  every 60s: DD ≥ 12% →   │
 │  reconciler · recovery state machine         │        │    cancel+close+halt     │
 ├──────────────────────────────────────────────┤        │  serves POST /halt       │
 │ watchdog container (key K2 or K1)            │        │  dead-man ping           │
 │  heartbeat · DD · flatten loop · POST /halt  │        └──────────────────────────┘
 ├──────────────────────────────────────────────┤
 │ api + web (read DB only; owner VPN only)     │        Research: offline, on-demand
 │ postgres (audit, orders, fills, runs)        │        (backtester, walk-forward, gates)
 └──────────────────────────────────────────────┘
```

**Tech:** Python 3.12 (`alpaca-py`, pandas/numpy, Hypothesis for property tests),
FastAPI, server-rendered HTML with htmx for the dashboard until Phase 4 (React deferred),
plain Postgres (Timescale deferred), parquet on disk for research data, Docker Compose,
`import-linter` in CI. Secrets via environment from a secret file with 0600 perms; live
keys are not present on any host until G3.

**Structural rules (enforced, not promised):**
1. Strategies run in their own container with **no broker credentials and no network
   egress** (`internal: true` Docker network); `alpaca-py`, `httpx`, `requests` are not
   installed in that image. Intents cross a local queue. `import-linter` forbids
   `strategies` → `execution|alpaca|httpx|requests|socket` as a second line. Acceptance
   test: a deliberately malicious strategy that tries `os.environ`, `importlib`, and raw
   sockets fails to reach the broker (§10 step 1.9).
2. Only the Risk Gate produces Orders. The Execution Adapter's submit function takes a
   `GatedOrder` type constructed only inside the gate module.
3. The API service holds no broker keys. It reads the DB. Halt goes to the watchdog.

---

## 4. Risk system — the 15% invariant

### 4.1 Stress-loss budget (replaces static caps)

Every position and every open entry order carries a **stress factor** `s` = the assumed
worst intraday adverse move for its instrument class:

| Class | s | Examples |
|-------|---|----------|
| Broad-index ETF | 0.10 | SPY, QQQ, IWM, DIA |
| Sector ETF / S&P 500 name with no scheduled event today or before next open | 0.25 | XLF, AAPL |
| Any other single name (this is the "stocks in play" universe by construction) | 0.50 | — |

Definitions (all in fractions of day-start equity `E0`; `N_i` = notional of position or
unfilled entry order *i*; DD = current drawdown from HWM using broker equity):

```
B  = 0.15 − DD − 0.01                         # budget: 15% minus current DD minus 1% slippage reserve
L  = max_i(N_i · s_i) + 0.10 · (Σ N_i − N_i*)  # worst single name at its stress + 10% on everything else
Invariant: L ≤ B, checked pre-trade for every Intent and every 30 s by the reconciler.
If L > B (because DD grew): trim existing positions, largest N·s first, until L ≤ B, within 60 s.
```

Worked cases (E0 = 100%; the 10% single-name cap below also applies):
- DD 0, three in-play names at the 10% cap each: L = 0.05 + 0.02 = 0.07 ≤ B = 0.14. A −50% halt-reopen on one plus −10% on the other two = −7%. Holds with room.
- DD 0, one broad ETF at 100% notional: L = 0.10 ≤ 0.14. OK (this is what lets index strategies express their edge). A −10% index crash day = −10% → hard halt fires, DD −10%, still 5 points under the requirement.
- DD −5%: B = 0.09; three in-play names at 10%: L = 0.07. Holds. ETF max notional = 90%.
- DD −9.9% (hard-halt boundary): B = 0.041; the budget now binds below the cap: one in-play name ≤ 8.2%, or ETF ≤ 41%. A −50% halt on 8.2% = −4.1% → DD −14.0%. Holds.
- Correlated crash (2020-03-16 pattern) at DD −4.9%, three S&P names at 10% each (s = 0.25): L = 0.025 + 0.02 = 0.045 ≤ 0.091. A −14% average fill on all three = −4.2% → DD −9.1%. Holds.

**Additional hard caps** (defense in depth; all measured on `E0`):

| Rule | Value |
|------|-------|
| Single non-ETF name notional | ≤ 10% of E0 regardless of budget |
| Gross notional (positions + open entries) | ≤ 100% of E0 (no leverage; enforced at broker via `max_margin_multiplier=1`) |
| One position **or** open order per symbol across all strategies | Intent rejected otherwise |
| Concurrent positions | ≤ 3 |
| Per-trade stop-distance risk | `r*` (§5.6), initial 0.5%; 0.25% for a strategy in micro-live (per strategy, not global) |
| Daily loss (broker equity vs E0) | −2.0% → flatten, no entries until next session |
| Weekly loss | −4.0% → flatten, halt until Monday + owner ack |
| Drawdown ladder | −5%: `r*` ×0.5; −8%: `r*` ×0.25, only top-ranked strategy trades; **−10%: hard halt (latching)**; −12%: watchdog and flattener close everything independently |
| Absolute sanity caps | per-order notional ≤ configured $X; entry limit price within 1% of last trade; ≤ 20 orders/day/strategy; ≤ 60 orders/day; ≤ 5 orders/min; qty must be ≥ 1 after `floor()` and the *rounded* qty must still satisfy every limit |
| Universe exclusions | any symbol with earnings/scheduled event today or before next open; any symbol with an LULD pause today; any symbol not `tradable && status == active` in the morning asset-master refresh; price < $5; 20-day median 1-min volume too small for the capacity rule |

Why the 5-point gap between the −10% hard halt and the 15% requirement still exists: it
covers the residual that no pre-trade rule can prevent — a broker outage or double host
failure while a position is halted. With the budget formula, the worst pre-trade-allowed
outcome at −9.9% is −14.0%; the remaining 1% is the slippage reserve.

### 4.2 Orders (Alpaca-specific behaviors, verified)

- Every entry is a **bracket**: limit entry (≤ 1% from last), **sell stop (market)** leg,
  limit take-profit leg. Alpaca converts *buy* stops to stop-limit (4%/2.5% band) but
  **does not convert sell stops**, so long exits are true market stops. Stop-limit exits
  are prohibited by the gate. Bracket child legs use **GTC** so they do not expire at
  16:00 if anything is still open. Brackets cannot be fractional; qty is integer.
- Prices rounded to the legal tick (2 decimals ≥ $1, 4 below), stops rounded *away* from
  entry; unit-tested. Any `rejected` order event is a hard incident (SAFE mode).
- `client_order_id = hash(strategy_hash, symbol, session_date, seq)`; Alpaca enforces
  uniqueness server-side (422). After any submit timeout, the adapter queries
  `GET /v2/orders:by_client_order_id` before retrying. On startup the order book is
  rebuilt from `GET /v2/orders?status=all&after=<session_open>`.
- No stop-leg modification based on stale data. Stale → close at market via the normal
  path.

### 4.3 Watchdog (host A, separate container, separate credentials if possible)

- Polls engine heartbeat file/HTTP (not DB) every 5 s; broker account every 15 s;
  subscribes to one symbol (SPY) itself for feed liveness.
- Triggers: heartbeat > 30 s with **open positions or open orders**; equity < HWM × 0.88;
  ≥ 15:57 ET (per broker `/v2/clock` and calendar, incl. early close) with anything
  open; engine reports DB down > 5 min; margin call event.
- Action = **verified flatten loop** (§4.6), incident row, owner alert.
- Serves `POST /halt` (halt only, bearer token, rate-limited) on its own port; the
  reverse proxy routes it directly. This is what the UI HALT button and the phone URL
  hit.
- Pings an external dead-man service every 60 s; a missed ping alerts the owner.
- Lower `oom_score_adj` than the engine; `mem_limit` set on both.

### 4.4 Off-host flattener (host B, different provider)

State-independent by design: it does not care what the engine or watchdog believe.
- 15:57 ET every trading day (calendar from broker): cancel all → close all → verify.
- 09:31 ET: if anything is open (e.g., halted into the close yesterday), close it.
- Every 60 s during the session: if broker equity < HWM × 0.88 → cancel, close, set
  `suspend_trade = true` at the broker, alert.
- Serves `POST /halt` too. Holds key K2 if Alpaca allows two key pairs, else K1.
- Its own dead-man ping.

### 4.5 Reconciliation (every 30 s and after every fill event)

1. Fetch broker positions, open orders, account (equity, accrued fees, multiplier,
   configurations, activities since last check).
2. Local vs broker mismatch → SAFE (no new entries) + alert; two consecutive → flatten
   using **broker truth** (`DELETE /v2/positions?cancel_orders=true`), never the local
   book.
3. **Position-protection invariant:** for every open position there is exactly one open
   sell-stop with `qty == position qty`. Otherwise place one immediately; if that fails
   within 10 s, close the position.
4. Budget check `L ≤ B` (§4.1); trim if violated.
5. Assert `multiplier == 1`, `no_shorting == true`, account id == configured, env ==
   configured (paper/live) — halt on any mismatch.
6. Cash-flow detection (§2.5).

### 4.6 Verified flatten loop (used by engine, watchdog, flattener, and HALT)

```
loop until broker readback shows 0 open orders AND 0 positions:
    DELETE /v2/orders
    wait until no order is 'pending_cancel' (poll 2 s, max 30 s)
    DELETE /v2/positions?cancel_orders=true
    for any position still open after 20 s: submit market sell for full qty
    if a symbol is HALTED: leave the market sell resting, mark 'halted_hold', page owner
    escalate alert every 30 s
report "flat" only from broker readback, with timestamp
```

Rate-limit budgeting: each key has one token bucket; a reserved allocation exists for
cancel/close calls; flatten retries are exempt from backoff caps; the API/UI never
touches the broker.

### 4.7 High-water mark and drawdown ledger

- HWM = max daily closing equity, **flow-adjusted** (withdrawals whitelisted only after an
  owner-acked halt; any deposit halts). Never decreases.
- Stored in three places: DB, a file on the watchdog volume, and derived from Alpaca
  `GET /v2/account/portfolio/history`. On every start, engine, watchdog, and flattener
  each take `max(all sources)`. Unit test: delete the DB → HWM unchanged.
- Intraday DD is measured with broker equity vs this HWM. Local marks are display-only.

### 4.8 Market-structure hazards (each with a rule)

1. **LULD / news halts:** `halted` is a first-class position state. Cancel works, close
   does not. Rule: no new entries in a symbol halted today; on reopen submit a market
   exit and log an incident; a name halted into the close is held with its GTC stop
   resting, the flattener closes it at 09:31, and the stress budget already priced it at
   s = 0.5. Market-wide Level-3 halt → flatten at reopen, halt for the day.
2. **Margin call (intraday framework):** liquidate to cure within the session; if the
   uncurable case (halted symbol) occurs, page owner; record that the account may be
   restricted; engine halts for the day.
3. **Corporate actions:** signal features use `adjustment=all` bars; qty/fee accounting
   uses raw. Ex-dividend/split dates from the announcements API; symbols with an ex-date
   or split effective today are excluded (S4 gap sizes dividend-adjusted).
4. **Asset master refresh** every morning from `/v2/assets`; only `tradable && active`
   symbols; symbol changes/delistings handled by exclusion.
5. **Opening auction:** no orders before 09:30:30; entries are limit orders.
6. **True cash-account broker (Tradier fallback only):** settled-cash ledger with
   business-date settlement queue, per-lot `funded_by` tag, GFV count (rolling 12 months),
   90-day restriction state; rule `settled_available = settled_at_open − Σ cost of all
   buys today`. Under T+1 each dollar round-trips once per day, so ~100% deployable.
7. **Shorting (Phase 6 only, ETFs only):** SSR (Rule 201) flag detection,
   `shortable`/`easy_to_borrow` flags, buy-stop conversion band accounted for in the
   budget, `no_shorting=false` only after the Phase 6 gate.
8. **Sub-$2k crossing** handled per §2.2.

### 4.9 Fault table (every row resolves to flat/halted or a named residual)

| Fault | Detection | Resolution |
|-------|-----------|------------|
| Engine crash/OOM | watchdog heartbeat > 30 s | watchdog flatten loop if positions **or orders** open; engine restarts into RECOVERING (§4.10) |
| Engine restart after a halt | latching `HALTED` flag (file on watchdog volume + DB + broker `suspend_trade`) | startup refuses to trade; re-enable only via TOTP action + audit row |
| Watchdog crash | engine polls watchdog heartbeat; external dead-man | engine: no new entries if watchdog stale > 30 s; owner paged; flattener unaffected |
| Both crash / host A reboot | dead-man misses | flattener (host B) still runs 15:57 / 12% / 09:31 rules; owner runbook: Alpaca dashboard liquidate-all + suspend trading |
| Host B down | its dead-man | owner paged; host A still protects; no new entries until B is back (go/no-go §4.11) |
| DB down | engine health | SAFE immediately (no safety decision depends solely on DB); flatten if > 5 min |
| Broker API 5xx/429 storm | N failed polls | broker-side stops still live; after 2 min unreachable → on recovery: cancel-all/close-all, halt for the day, post-mortem. **Residual:** an outage coinciding with a gap; the stress budget is sized for it |
| Market-data WS silent disconnect | zero messages across all symbols for > 15 s while `clock.is_open` | force reconnect + REST poll; positions still protected by broker stops |
| Trade-update WS drop / missed fill | REST order poll every 10 s; replay since last event on every reconnect | reconciler catches within 30 s |
| Clock skew | compare local clock with `/v2/clock` every cycle; > 2 s | SAFE; all session times use broker clock |
| Deploy during session | deploy script checks `clock.is_open && (positions || orders)` | refuses unless `--flatten-first`; no auto-deploy |
| Secrets leak / unknown-cause halt | — | rotate keys per runbook; keys rotated after any halt of unknown cause |
| Bracket legs partially cancelled / partial fill orphan | position-protection invariant (§4.5.3) | protective stop placed or position closed |
| Order stuck `pending_cancel` | flatten loop | loop waits, then market-sells; never reports flat until readback |
| Paper/live key mix-up | startup + every cycle: account id and env asserted | refuse to start / halt |
| Halted symbol | §4.8.1 | held with resting stop; closed at reopen/09:31; incident |
| Notification channel dead | 09:25 ET daily "alive" message | missing message is the alarm |
| Margin call | account event / activities | liquidate to cure; halt for the day |

### 4.10 Engine state machine

```
BOOT → RECOVERING (rebuild orders/positions from broker; load HWM = max(sources);
        assert account id/env/config; if HALTED flag set → stay HALTED)
     → SAFE (manage exits only; no entries) → RUNNING (after clean reconcile,
        fresh watchdog + flattener heartbeats, go/no-go passed)
Any trigger → SAFE (recoverable) or HALTED (latching; requires TOTP re-enable + written post-mortem)
Positions found at boot that do not match DB-recorded brackets are closed immediately.
```

### 4.11 Pre-session go/no-go (09:15 ET, all must pass or the day is skipped)

Clock skew OK · calendar fetched (incl. early close) · asset master refreshed · earnings/
event exclusions loaded · reconciliation clean · watchdog + flattener heartbeats fresh ·
HWM loaded from ≥ 2 sources and agreeing · `multiplier==1`, `no_shorting==true` ·
no cash inflow detected · no HALTED flag · notification "alive" sent.

---

## 5. Strategy layer

### 5.1 Principles

1. A strategy is a pure function `(bars, features, account_state) → Intents`. No I/O.
2. Same code in backtest, paper, live (one event-loop abstraction with a clock and a data
   source). A strategy's identity is `(code_hash, config_hash)`; **any change creates a
   new strategy at state Idea.** The gate refuses Intents from a hash not in the DB at
   the required state.
3. Portfolio of small, uncorrelated, validated edges; allocation by live track record.
4. No discretion, no news reading, no sub-second latency: a 200 req/min retail API
   competes on discipline and cost control, not speed.

### 5.2 Candidate strategies (research queue)

| ID | Track | Strategy | Prior evidence | Known weakness to test |
|----|-------|----------|----------------|------------------------|
| S3-ETF | A | VWAP mean-reversion on SPY/QQQ/IWM: fade > 2σ extension from VWAP after 10:00 with volume exhaustion; target VWAP; stop 1×ATR(5m); trend-day filter (opening range > 0.8×ATR(daily) disables) | Widely used in execution literature | Trend-day tail; must be ≥ 0.75 trades/day to be gateable |
| S2 | A | Intraday momentum on SPY/QQQ with noise band (Zarattini, Barbon & Aziz 2024): band = avg of past 14 days' |move from open| by time-of-day; enter on break; trailing stop at band; VIX-scaled sizing; exit at close | Paper: Sharpe ~1.3–2.4 depending on version, beta ≈ 0, 2007–2024 | Leverage-dependent in the paper (we run ≤ 100% notional); regime concentration; costs |
| S1 | B | Opening Range Breakout on stocks in play: RVOL = (pre-market + first-5-min volume) / same-window 14-day avg ≥ 2; price > $5; ATR filter; 5-min OR; entry on break; stop = OR opposite side or 10% ATR whichever tighter; exit at close/target | Zarattini & Aziz; QQQ replication matched paper *before* costs | Break-even at ~2.2¢/share on QQQ; 76% of PnL from 2022; in-play names halt |
| S4 | B | Gap continuation/fade by gap size & pre-market volume | Mixed | Needs SIP pre-market; dividend adjustment |
| S5 | — | Hold cash | 0% drawdown | Default whenever nothing else passes |

Order: S3-ETF → S2 → (SIP) S1 → S4. Long-only until Phase 6.

### 5.3 Research protocol (pre-registered, no exceptions)

1. **Data:** Alpaca historical SIP minute bars and quotes, ≥ 5 years, `adjustment=all`
   for features and raw for accounting. Universe: Track A ETFs; Track B ≈ 200 most-liquid
   names + ETFs (not Russell 1000 — 490M minute rows is not credible on a small VPS).
   Survivorship: Alpaca's asset list is current-state only; point-in-time constituents
   require an external source (D7). Until one is chosen, Track B results carry a stated
   survivorship bias and G1 for Track B is blocked.
2. **Fill rules (no look-ahead):** a signal at bar-t close executes no earlier than bar
   t+1 open; stop fills at `min(stop, next open)` for longs minus stop slippage
   (gap-through modelled); halts fill at the reopen print; limit targets fill only if
   price trades *through* them; partial fills per the capacity rule.
3. **Costs** per §2.3 with spread-aware slippage from historical NBBO; stress 1×/2×/3×.
4. **Parameters:** ≤ 5 free parameters; grid **pre-registered** before running; selection
   only *inside each train fold* with a fixed rule; OOS concatenation uses per-fold
   selections; grid surfaces reported per fold.
5. **Walk-forward:** anchored, 12-month train / 3-month test, rolling.
6. **Holdout:** the most recent 12 months are evaluated **exactly once** at G1 sign-off.
   A fail burns the holdout for that strategy family.
7. **Trial registry:** every run is `(code_hash, config_hash)`; the backtester refuses to
   run unregistered configs; DSR uses the registry count. Implication stated honestly:
   with ~100 registered trials over 4 OOS years, DSR > 0.95 needs post-cost annualized
   Sharpe ≈ 2; with 10 trials ≈ 1.6.
8. **Sharpe definition:** daily strategy returns at intended risk, annualized ×√252,
   over the concatenated OOS series, reported with standard error.
9. **Regime:** positive in ≥ 3 of 4 OOS years and ≥ 2 of 3 VIX terciles; no single year
   > 50% of profit.
10. **Monte Carlo:** bootstrap OOS trades 10,000× → 95th-percentile max drawdown < 8%
    at the intended risk.
11. **Capacity:** position ≤ 1% of the symbol's 20-day median 1-minute volume at the
    entry minute.
12. **Fixed-cost hurdle:** expected annual net PnL at the equity where the strategy would
    trade ≥ 2 × (data + hosting) for that track.
13. **Trade-rate floor:** ≥ 0.75 trades per trading day averaged over OOS (so live gates
    are reachable).

### 5.4 Promotion gates (numeric, automatic; state in DB keyed by strategy hash)

| Gate | From → To | Requirements |
|------|-----------|--------------|
| G1 | Idea → Backtested | §5.3 complete; OOS Sharpe ≥ 1.0 at the stress multiple for its track; DSR ≥ 0.95; MC 95% MDD < 8%; ≥ 300 OOS trades **and** ≥ 0.75 trades/day; regime rule; fixed-cost hurdle; holdout passed once |
| G2 | Backtested → Paper-done | Paper on Alpaca on the **same feed as live**, ≥ 40 trading days and ≥ 30 trades; cumulative PnL stays inside the backtest MC 10–90 band for the realized trade count; **counterfactual slippage** (each paper fill re-priced against historical SIP NBBO at the fill timestamp) ≤ modeled; **signal agreement ≥ 95%** between the live feed and a nightly SIP replay; reconciliation clean. (Paper fill quality itself is *not* evidence — Alpaca paper fills at quote.) |
| G3 | Paper-done → Micro-live | Checklist: Phase-1 acceptance tests green on the current commit; chaos tests passed within 30 days; watchdog **and** flattener each performed a live close-all drill on a 1-share position; HWM seeded; broker config asserted; owner TOTP approval. Allocation 10%, per-trade risk 0.25% (this strategy only) |
| G4 | Micro-live → Full | ≥ 40 trading days and ≥ 30 live trades; realized slippage (real fills) ≤ 1.5× modeled; cumulative PnL inside MC 10–90 band; live MDD < 5%; then allocation ramps 10→25→50→100% of target, each step after 20 more clean days |
| Portfolio gate | before any 2nd strategy gets allocation | day-bootstrapped portfolio MC (preserving co-occurrence) 95% MDD < 8%; 60-day PnL correlation with each live strategy < 0.6 |
| Demotion | any level → one lower | **sequential test**: cumulative PnL after *n* trades below the MC 5th percentile for *n* trades, **or** live MDD > MC 95% MDD, **or** slippage > 1.5× modeled over 30 trades. Demotion flattens that strategy's positions, sets allocation 0; re-promotion requires a fresh full window; two demotions in 6 months → Idea. (Rolling-Sharpe triggers are banned: a 20-day Sharpe has SE ≈ 3.5.) |

### 5.5 Allocation across strategies (only once ≥ 2 strategies are at G4)

¼-Kelly on OOS trade distributions, capped by §4.1; correlation guard (> 0.6 → combined
cap of one); weekly rebalance, ±10 pp/week. Deferred until it is needed.

### 5.6 Risk per trade `r*` (derived, not fixed)

`r* = max r ≤ 1.5% such that portfolio MC 99% MDD ≤ 7%`, recomputed monthly from live +
OOS trades, scaled by the drawdown ladder. Initial value 0.5%. Each strategy declares a
stop-distance floor so that `r*` is reachable under the notional caps (e.g., a 0.3% stop
at 10% notional expresses only 0.03% risk — such a strategy is not gateable for Track B).

---

## 6. Growth mechanics and economics

### 6.1 Minimum viable capital (owner must see this before D1)

Fixed costs: hosting ≈ $180/yr (two VPS); SIP data $1,188/yr (Track B only). Rule of
thumb: fixed costs ≤ 2% of equity, and a genuine post-cost Sharpe-1.2 intraday strategy at
0.5% risk and 0.25R expectancy yields roughly 9–35% gross/yr before caps and before tax.

| Starting equity | Track | Fixed cost / yr | Fixed cost % | Plausible gross | After fixed costs | After ~30% tax |
|-----------------|-------|-----------------|--------------|-----------------|-------------------|----------------|
| $1,000 | A | $180 | 18% | $90–350 | −$90 to +$170 | ≈ 0 |
| $5,000 | A | $180 | 3.6% | $450–1,750 | $270–1,570 | $190–1,100 |
| $7,500 | A | $180 | 2.4% | $675–2,600 | $500–2,400 | $350–1,700 |
| $25,000 | A+B | $1,370 | 5.5% | $2,250–8,750 | $900–7,400 | $600–5,200 |
| $65,000 | A+B | $1,370 | 2.1% | $5,850–22,750 | $4,500–21,400 | $3,100–15,000 |

Recommendations recorded as defaults: **minimum $5,000 (Track A only); Track B not
before $25,000.** Below $5,000 the plan recommends not running live at all.

**Shutdown rule:** if trailing 12-month live net PnL (after fees and data) < fixed costs,
the system stops and the owner is told. Bracket orders need integer shares: at $5,000
and 100% ETF notional that is ~8 shares of SPY, so a 0.5% risk ($25) needs a stop
≥ $3.1/share (≈ 0.5%) — feasible, but integer rounding alone mis-sizes by up to 12.5%,
and the gate checks the *rounded* qty against every limit. Below ~$3,000 single-share
granularity makes the limits meaningless; this is recorded in D1.

### 6.2 Compounding rules

- All limits are fractions of day-start equity, so size scales with the account.
- HWM ratchets on daily closes; the ladder always protects the new peak.
- Fixed-cost features (SIP) unlock by equity threshold, not by hand.
- **Leverage: never.** Gross notional ≤ 100% of equity; `max_margin_multiplier=1` at the
  broker. (A 10% index shock at 1.5× is 15%; leverage is arithmetically incompatible with
  the constraint.) The v1 Phase-6 leverage item is deleted.
- Shorting: Phase 6, ETFs only, after its own gate (§4.8.7).
- `r*` re-derived monthly (§5.6) so risk is as large as the drawdown budget allows, no
  larger.
- Taxes: gains are short-term; wash-sale deferral applies to re-traded symbols across
  year-end; the weekly report shows after-tax estimates; Section 475(f) mark-to-market
  election is D6 (owner + tax advisor).

---

## 7. Web app specification

**Exposure:** the dashboard is reachable **only over WireGuard/Tailscale**. The only
public endpoints are `POST /halt` on the watchdog and on the flattener (bearer token,
rate-limited, halt-only, no parameters). Re-enable is never reachable from the halt
route's auth. Sessions expire in 12 h; TOTP on login and on every state-changing action;
lockout after 5 failures; CSRF tokens on forms.

**Pages**
1. **Overview** — PAPER/LIVE banner + account id; engine state (RUNNING/SAFE/HALTED with
   "confirmed flat at broker at HH:MM:SS" vs "halt sent, awaiting readback"); broker
   readback positions/orders count with timestamp of last successful poll; engine belief
   vs broker side-by-side with age; equity, HWM (value + sources), DD gauge against the
   5/8/10/12/15 ladder; day/week PnL; stress-budget usage `L/B`; feed health; watchdog
   and flattener last-check times; **HALT** button (→ watchdog `/halt`).
2. **Positions & Orders** — entry, stop, target, qty, notional, `s`, unrealized PnL, time
   in trade, strategy hash; "close now" **routes via the watchdog**.
3. **Strategies** — gate state, allocation, live vs backtest MC band, cumulative-PnL
   sequential test position, realized vs modeled slippage, signal-agreement score,
   promotion/demotion history; owner actions (approve G3, pause).
4. **Research** — runs (hashes, dates, OOS metrics, DSR, MC MDD, per-fold surfaces,
   holdout status); "promote to paper" if G1 passed.
5. **Journal / Audit** — every Intent, gate decision, order, fill, rejection, reconciliation
   result, incident, cash-flow event; CSV export that reconciles to Alpaca's 1099-B CSV.
6. **Settings** — notification channels; read-only display of limits (limits change only
   via versioned YAML in the repo).

Notifications (ntfy + email): any halt, SAFE entry, gate change, watchdog/flattener
action, reconciliation mismatch, cash-flow event, 09:25 "alive", 16:05 daily summary.

---

## 8. Operations

- Compose stack on host A: `engine`, `strategies` (no egress), `watchdog`, `api`, `db`.
  Host B: `flattener` only. `research` runs on-demand on the dev machine.
- Time sync (chrony); broker clock is the reference for all session times.
- Morning: asset-master refresh, earnings/event calendar load, go/no-go (§4.11).
- Deploy script refuses during session with anything open (§4.9).
- DB backups nightly to object storage; HWM also on watchdog volume and broker history.
- Weekly report: PnL (gross, net, after-tax est.), DD, per-strategy stats, slippage vs
  model, cost totals, incidents, budget usage.
- Runbooks: broker outage, data outage, engine crash with open positions, halted symbol,
  margin call, mismatched fill, key rotation, **Alpaca dashboard liquidate-all + suspend
  trading** (the ultimate manual path, written on the owner's phone).

---

## 9. Testing strategy

- **Unit:** every §4.1 rule incl. budget formula and trimming; tick rounding; qty
  flooring; idempotent ids; HWM max-of-sources; calendar/early close; cash-flow detection;
  settled-cash module (adapter-conditional).
- **Property-based (Hypothesis):** random fill/price/halt sequences never produce
  DD > 10% without a halt emitted and never violate `L ≤ B` after trimming.
- **Simulation harness:** replay historical days (incl. 2020-03-16, 2024-08-05) through
  the live engine code with a fake broker supporting partial fills, rejects, 429s,
  latency, halts, and gaps; assert invariant.
- **Chaos (paper, during session hours):** `docker pause engine` mid-trade → watchdog
  flat within 60 s; `docker pause watchdog` → engine stops entries, dead-man alerts;
  pause both → flattener closes at 15:57; cut network → SAFE; duplicate fill event → one
  position; stale data → exit; halt + `docker restart engine` → no orders submitted.
- **Malicious strategy test:** strategy attempts env/key access, `importlib`, raw socket
  → cannot reach broker.
- **Broker sandbox:** paper API end-to-end nightly; 1-share live close-all drills before
  G3.
- **Backtest reproducibility:** run twice from `(code_hash, config_hash, data_snapshot)`
  → identical metrics.

---

## 10. Roadmap (phases → steps, each with a runnable acceptance test)

Realistic calendar for one developer: Phase 1 ≈ 4–6 weeks; Phase 2 ≈ 3–4 weeks; each
strategy's research ≈ 2–4 weeks; paper 40 trading days; micro-live 40 trading days →
**first strategy at full allocation ≈ 8–10 months from start**. Anything not protecting the
invariant is deferred.

### Phase 0 — Decisions & accounts (owner)
- 0.1 Record D1–D7 in `docs/DECISIONS.md`. *Accept:* file exists with every ID answered
  or the default explicitly accepted.
- 0.2 Open Alpaca account; create paper keys; **test whether two key pairs can be active
  simultaneously** (create, call `/v2/account` with both, revoke one, confirm the other
  still works). *Accept:* result recorded; §4.4 key design chosen accordingly.
- 0.3 Set broker config on paper: `max_margin_multiplier=1`, `no_shorting=true`.
  *Accept:* `GET /v2/account/configurations` shows both.
- 0.4 Notification channel. *Accept:* test message received on phone.
- 0.5 Provision host B (different provider) and the dead-man service. *Accept:* a
  deliberately missed ping produces an alert.

### Phase 1 — Skeleton, risk gate, watchdog, flattener, halt (no strategies yet)
- 1.1 Repo scaffold (`engine/`, `strategies/`, `watchdog/`, `flattener/`, `api/`,
  `research/`, `infra/`), Compose, Postgres, CI (lint, `import-linter`, tests).
  *Accept:* `docker compose up` healthy; CI green on an empty test.
- 1.2 Broker adapter + Alpaca paper impl: account, configurations, positions, orders
  (bracket with GTC legs), cancel-all, close-all, clock, calendar (incl. early close),
  activities, portfolio history. *Accept:* integration test during session hours places a
  1-share bracket, verifies both child legs exist with correct qty, cancels, confirms
  readback 0/0.
- 1.3 Verified flatten loop (§4.6). *Accept:* with 2 paper positions and 1 pending order,
  flatten returns only after readback 0/0; injected `pending_cancel` stall is handled.
- 1.4 Risk gate: budget formula, hard caps, one-per-symbol, pending-order exposure,
  sanity caps, tick/qty rounding, day-start equity source, universe exclusions.
  *Accept:* unit tests per rule; Hypothesis property test (§9) passes 10,000 cases.
- 1.5 HWM ledger with three sources + cash-flow detection. *Accept:* delete DB → HWM
  unchanged; injected `CSD` activity → HALT.
- 1.6 Reconciler with position-protection invariant and config assertions. *Accept:*
  cancel a stop leg manually in the paper dashboard → new stop placed within 30 s; set
  `no_shorting=false` manually → halt.
- 1.7 Engine state machine + latching halt + go/no-go. *Accept:* halt, `docker restart
  engine`, assert zero orders submitted for 5 minutes; re-enable requires TOTP.
- 1.8 Watchdog (heartbeat, DD, 15:57 rule, `/halt`, dead-man). *Accept:* `docker pause
  engine` with a paper position → flat within 60 s, incident row; `curl -X POST /halt`
  with engine paused → flat.
- 1.9 Strategy container isolation + malicious strategy test. *Accept:* test strategy
  cannot reach `paper-api.alpaca.markets` (connection refused) and `import-linter` fails
  on a forbidden import.
- 1.10 Off-host flattener on host B. *Accept:* pause engine and watchdog at 15:50 with a
  paper position → flat by 15:58; DD simulated via a fake HWM → close-all + `suspend_trade`.
- 1.11 Minimal dashboard (server-rendered): overview fields in §7.1, HALT button wired to
  watchdog. *Accept:* HALT with API service stopped still flattens (button hits the
  watchdog port directly); dashboard unreachable from the public internet.
- 1.12 Deploy guard + runbooks + chaos test suite runnable by one command.
  *Accept:* all §9 chaos tests pass in paper during a session.

### Phase 2 — Data & research infrastructure
- 2.1 Historical loader (SIP minute bars + quotes, `adjustment=all` and raw) for Track A
  ETFs and the Track-B 200-name list; incremental daily updater. *Accept:* ≥ 99.5% of
  expected session minutes per symbol-day, zero duplicate timestamps; a known split date
  reproduces the adjusted series.
- 2.2 Event-driven backtester sharing the engine's strategy interface; fill rules §5.3.2;
  cost model §2.3 with NBBO-based slippage. *Accept:* toy strategy reproduces
  hand-computed PnL to the cent incl. fees; a gap-through stop fills at the open.
- 2.3 Walk-forward runner with per-fold selection, once-only holdout lock, trial registry
  (refuses unregistered configs), DSR, MC MDD, regime table. *Accept:* 1,000 random
  strategies → ≤ 5% pass G1; an unregistered run is refused.
- 2.4 Research page listing runs and gate status. *Accept:* a run's G1 report renders
  with every §5.4 field.

### Phase 3 — Strategy research (S3-ETF → S2 → [SIP] S1 → S4)
- 3.x Per strategy: pre-register grid → implement → folds → costs stress → regime, MC,
  capacity, fixed-cost hurdle → holdout once → G1 record. *Accept:* G1 report in DB with
  PASS or FAIL and reason. **FAIL is a valid outcome.** Track B blocked until D7 (survivorship
  source) is resolved.

### Phase 4 — Paper (same feed as live)
- 4.1 Reset paper equity to D1; run G1-passed strategies with the full gate. *Accept:*
  ≥ 40 trading days, ≥ 30 trades, reconciliation clean, MC band check, counterfactual
  slippage report, signal-agreement ≥ 95%.
- 4.2 Monthly chaos re-run. *Accept:* all pass.

### Phase 5 — Micro-live
- 5.1 G3 checklist; fund account with D1 exactly; install live keys on hosts A and B;
  1-share live close-all drills by watchdog and flattener. *Accept:* drills logged;
  activities show one deposit and it predates go-live.
- 5.2 10% allocation / 0.25% risk for ≥ 40 trading days. *Accept:* G4 metrics met or
  demotion fired; weekly owner review; post-mortem per halt.

### Phase 6 — Scale
- 6.1 Ramp per G4. 6.2 Second strategy after portfolio gate. 6.3 SIP + Track B at
  ≥ $25k (or D2). 6.4 ETF shorting only after its own gate. *Accept:* each step logged
  with its 20-day clean-window evidence.

---

## 11. Open decisions for the owner

| ID | Decision | Default if unanswered |
|----|----------|-----------------------|
| D1 | Starting capital | Plan recommends ≥ $5,000; below that, do not go live (§6.1) |
| D2 | Pay $99/mo for SIP before $25k equity | No; Track A only |
| D3 | Notification channel(s) | ntfy + email |
| D4 | Hosting | Host A: small US-East VPS; Host B: different provider |
| D5 | Shorting ever allowed | ETFs only, Phase 6, after its gate |
| D6 | Tax treatment (Section 475(f) election) | Owner consults a tax advisor; plan reports after-tax at 30% |
| D7 | Point-in-time universe source for Track B | None chosen → Track B research blocked |

---

## 12. Sources consulted (2026-09-02)

- Gauntlet Loop: github.com/trilwu/gauntlet-loop-skills; github.com/NicholasSpisak/gauntlet-loop
- Robinhood API status: github.com/sanko/Robinhood; apidog.com/blog/robinhood-api; bitget.com/wiki
- PDT retirement: SEC order on SR-FINRA-2025-017; FINRA Regulatory Notice 26-10; schwab.com; tastytrade.com; tradezero.com
- Alpaca: account model (support "Can I have a cash account", "What are Unsettled Funds"); intraday margin framework blog; account configurations reference (`max_margin_multiplier`, `no_shorting`, `dtbp_check`, `suspend_trade`); orders doc (buy-stop conversion, sell stops not converted); 24/5 limit-only; paper-trading mechanics (github.com/alpacahq/alpaca-docs); alpaca-py README; data plans and IEX coverage (docs market-data-faq, forum threads)
- Fees: FINRA Information Notice 2026-03-17 (Section 31 $20.60/M); FINRA TAF 2026 ($0.000195/share, cap $9.79)
- Day-trader profitability: Jordan & Diltz (FAJ 2003); Chague, De-Losso & Giovannetti
- Strategies: Zarattini & Aziz (SSRN 4416622, 4729284); Zarattini, Barbon & Aziz 2024 (SPY); replication github.com/giovannibrusco/zarattini-2023-orb-qqq
- Backtest hygiene: Bailey & López de Prado, "The Deflated Sharpe Ratio" (2014)
