# MasterTrader — Automated Day-Trading Web App: Master Plan

Status: **v3** (after Gauntlet rounds 1–2). Critique history: `docs/GAUNTLET_LOG.md`.
Date: 2026-09-02

---

## 0. Premise and honesty statement (read first)

**Achievable with high confidence:** account equity never falls more than 15% below its
high-water mark. This is enforced by arithmetic (a stress-loss budget that assumes every
open position suffers its worst plausible move at once), by broker-side configuration,
and by an off-host flattener that does not depend on the trading engine being alive.

**Not achievable by anyone:** a guarantee of profit. ~64% of US day traders lose money
after costs (Jordan & Diltz 2003); 97% of persistent Brazilian day traders lost (Chague
et al.). The most-cited retail intraday strategy (opening-range breakout on QQQ) loses
nearly all its paper edge at ~2.2¢/share slippage in an independent replication.

**The arithmetic the owner must accept before funding (§6.1):** under a hard 15%
drawdown constraint, the risk per trade that survives the drawdown Monte Carlo is about
0.3–0.5% of equity. At one trade a day that is an annual volatility of roughly 5–8%, so a
genuinely good strategy (Sharpe 1–2 after costs) yields **≈ 4–16% gross per year**, not
the 50–200% that "day trading" suggests. Fixed costs are ~$180/yr for the ETF track and
~$1,370/yr with full market data. **Below ~$10,000 the ETF track cannot pay for itself
after tax; single-name trading needs ~$70,000** and, under the same constraint, is limited
to a small slice of equity. The honest expected outcome for most strategy candidates is
"does not pass the gates," in which case the system holds cash.

**The objective is therefore:**

> Maximize expected after-tax compounded growth of one fixed starting balance,
> **subject to** equity never dropping more than 15% below its high-water mark, trading
> only strategies that survived a pre-registered, cost-inclusive, out-of-sample pipeline,
> with capital deployed in proportion to demonstrated *live* edge.

**Design principle:** the risk system is the product; strategies are replaceable
plug-ins.

**Interpretation of the 15% rule (stated assumption):** maximum drawdown from the
high-water mark (HWM) ≤ 15%, where HWM = the highest *daily closing* equity (the
account is flat at every close, so this is unambiguous), proportionally adjusted for
owner withdrawals (§4.7), and drawdown is checked continuously against broker-reported
equity.

---

## 1. Quality bar (the Gauntlet "bar")

A hostile reviewer, given only this document, must agree all of these hold:

| # | Bar item | Evidence |
|---|----------|----------|
| B1 | Drawdown invariant is enforced by a layer strategies cannot bypass, with broker-side backup and an off-host backstop; the budget arithmetic holds under stated worst cases (multiple simultaneous halts, correlated crash, market-wide circuit breakers, dead host, stale data) and residuals are named. | §4.1 (formula + table), §4.2–4.6 |
| B2 | No live capital is risked on an unvalidated strategy; gates are numeric, mutually consistent, in defined units, and not noise-driven. | §5.4 |
| B3 | Backtests are cost-inclusive (spread-aware slippage, all fees, fixed costs, tax) and overfitting-resistant (per-fold selection, once-only holdout, registered trials, DSR with a defined trial count). | §2.3, §5.3 |
| B4 | The system operates within the broker's actual rules (account model, bracket TIF semantics, held-quantity rejects, halts incl. market-wide, order types, tick sizes, asset master, opening auction). | §2.2, §2.4, §4.2, §4.8 |
| B5 | Notional never exceeds equity; leverage and shorting are disabled at the broker; external flows are detected the same cycle; HWM is flow-adjusted with one formula. | §2.5, §4.7 |
| B6 | Every failure resolves to "flat and halted" or a named residual; halt is latching with defined writers/clearers; restart cannot re-arm trading mid-session; concurrent flatten actors are arbitrated. | §4.9, §4.10 |
| B7 | Owner has fresh visibility even with the engine dead, and a halt that works when the engine, API, or host is dead. | §7 |
| B8 | Roadmap steps have runnable, falsifiable acceptance tests (with a fake broker where paper cannot exercise them); scope and calendar are realistic for one developer. | §10 |

Reference standards: FINRA Rule 15c3-5 (pre-trade controls); Bailey & López de Prado
(Deflated Sharpe Ratio); walk-forward analysis.

---

## 2. Hard constraints (facts verified 2026-09-02; unverified items marked and probed in Phase 0.6)

### 2.1 Broker: Robinhood is not viable; Alpaca is primary

- Robinhood: no official stock/options API; ToS prohibits automation. **Rejected.** The
  Alpaca web dashboard gives the owner a Robinhood-like view (positions, orders, activity,
  "liquidate all", "suspend trading"). **Any manual trade, transfer, ACAT, or journal in
  this account is treated as hostile: the engine flattens/halts.** Keep other investing in
  a separate account.
- Alpaca: API-first, commission-free, official `alpaca-py` (Python ≥ 3.10), REST +
  WebSocket, bracket/OCO/OTO, paper environment. Rate limit is **~200 requests/min per
  account** (not per key) — budgeted in §4.6.
- Backups: Tradier (true cash accounts, 120 req/min), Interactive Brokers. The broker
  adapter is an interface; Alpaca-specific behavior is marked.

### 2.2 Alpaca account model and regulation

- **No cash accounts.** Every account is margin; below $2,000 it is limited-margin (1×,
  no shorting, unsettled proceeds reusable, no Good-Faith-Violation regime). A
  settled-cash module exists only for a true cash-account broker (§4.8.6).
- FINRA retired the Pattern Day Trader rule effective **2026-06-04**. No day-trade
  counting, no $25k minimum. Alpaca's 2026-06-03 changelog deprecates the PDT/DTBP fields;
  **`dtbp_check` is not asserted.**
- Broker-side configuration (`PATCH /v2/account/configurations`): `max_margin_multiplier
  = "1"`, `no_shorting = true`, `suspend_trade` (semantics probed in 0.6). Asserted every
  cycle: multiplier, no_shorting, and `suspend_trade == false` whenever the system is not
  HALTED. Options level 0 and crypto disabled are asserted too; the gate rejects any asset
  whose `asset_class != us_equity`.
- With multiplier 1 and long-only, `buying_power == cash`, no debit can arise, and an
  intraday margin call cannot occur; the margin-call runbook belongs to Phase 6 only.
  Per-cycle sanity asserts instead: `equity ≥ maintenance_margin`, `cash ≥ −accrued_fees`.
- The $2,000 threshold is irrelevant at the recommended minimum capital (a 15% drawdown
  from $10,000 is $8,500); it matters only if D1 < $2,353 and the plan recommends against
  that.
- Multiple simultaneous API key pairs per live account: **unverified** (0.2 tests it).
  Since the rate limit is per account, separate keys buy no independence; independence
  comes from separate hosts and processes (§4.4).
- Owner disclosures: margin agreement and FINRA 4210 disclosures apply; opt out of
  fully-paid securities lending; the high-yield cash program produces `INT` credits
  (treated as legitimate return); SIP data needs a non-professional self-certification;
  the 1099-B will carry wash-sale adjustments (§6.3).

### 2.3 Costs (every one is in the backtester and the weekly report)

| Cost | Value | Where applied |
|------|-------|---------------|
| Commission | $0 | — |
| SEC Section 31 | $20.60 per $1M sold (from 2026-04-04) | sells |
| FINRA TAF | $0.000195/share sold, cap $9.79/trade | sells |
| CAT fee | $0.000001/share (CAT Fee 2026-1) + $0.000002/share (Historical Assessment 1A) | all executions |
| Slippage (entry, Track A) | `max($0.02/share, half NBBO spread at the fill minute) + 5 bp` | every fill |
| Slippage (entry, Track B) | `max($0.02/share, time-weighted 90th-percentile spread within the fill minute) + 5 bp` | every fill |
| Slippage (stop exit) | `max($0.04/share, full spread) + 10 bp`; Track B intrabar stops fill at `min(stop − slippage, low of trigger bar + half spread)` in stress runs | every stop fill |
| Stress | 1×, 2×, 3×; G1 at **2×** for Track A, **3×** for Track B | G1 |
| Market data | Basic: free, IEX only (~2% of volume), ~30-symbol WebSocket cap, **one concurrent WebSocket connection**. Algo Trader Plus: $99/mo, full SIP | §2.4 |
| Hosting | ~$180/yr (two small VPS + dead-man service) | §6.1 |
| Tax | short-term gains at the owner's marginal rate (D6; 30% assumed); NIIT only above the MAGI threshold; **fixed costs are not deductible** absent Trader Tax Status, which is unlikely at ~190 trades/yr; net losses deductible only $3,000/yr; wash-sale deferral across strategies and year-end (§6.3) | §6.1 |

### 2.4 Data plan

Research uses historical SIP minute bars and NBBO quotes (free). Live Basic-plan signals
come from IEX with a ~30-symbol, single-connection stream. **Paper must run on the same
feed as live for that strategy.**

| Track | Instruments | Feed | Precondition |
|-------|-------------|------|--------------|
| A | SPY, QQQ (and their lower-priced twins SPLG, QQQM for share granularity), IWM, DIA, sector ETFs | IEX; nightly SIP replay must agree with live per-minute signal state (§5.4 G2) | equity ≥ $10k |
| B | ≈ 200 most-liquid single names | SIP subscribed before paper | equity ≥ $70k or D2 |

Regular session only. **Engine entries from 09:32:00 ET** (after the flattener's morning
pass, §4.4); no `opg`/`cls` TIF; no extended hours; Track B entries end 15:00 and Track B
positions are closed by 15:30; everything flat by 15:55 (engine) / 15:57 (backstops).

### 2.5 Capital

- One initial deposit (D1). No deposit code exists, but detection is the control:
  - **Per-cycle cash identity** (same cycle, no lag): `cash_now − cash_at_open − Σ fill
    cash − accrued_fee_delta = 0 ± $1`; any residual → treated as an external flow → HALT.
  - **Nightly activities allow-list:** `FILL`, `FEE`, `INT*`, `DIV*` only. Any other
    activity with `net_amount ≠ 0` (`CSD`, `CSW`, `JNL*`, `ACAT*`, `FOPT`, …) → HALT.
    `INT`/`DIV` are legitimate returns and may raise HWM; `FEE` is a loss.
- Sizing equity `E0 = min(day-start equity − accrued_fees, buying_power)`. A 403
  "insufficient buying power" is a sizing-bug alert (SAFE), not a hard incident.

---

## 3. System architecture

```
 Owner ── WireGuard/Tailscale ──► Dashboard (api + web; NO broker keys; reads DB)
 Owner's phone ── public HTTPS ──► halt-receiver A (no keys) ─ writes HALT_REQUESTED file ─► watchdog
 Owner's phone ── public HTTPS ──► halt-receiver B (no keys) ─ writes HALT_REQUESTED file ─► flattener
 Owner ── Alpaca web dashboard ──► liquidate all / suspend trading (ultimate manual path)

 HOST A (US-East VPS)                                    HOST B (different provider)
 ┌────────────────────────────────────────────────┐     ┌───────────────────────────┐
 │ strategies container: NO keys, NO egress,       │     │ flattener (key K2 or K1)  │
 │   read-only fs, cap_drop ALL, non-root, limits  │     │  09:29 snapshot / 09:30:05│
 │   ── JSON Intents over unix socket (strat_net) ─┼─┐   │    close overnight carry  │
 │ engine (key K1)  [core_net]                     │ │   │  15:57 cancel+close+verify│
 │   feed ─► strategy host ◄───────────────────────┼─┘   │  every 60 s: DD ≥ 11% →   │
 │   RISK GATE ─► execution adapter ─► Alpaca      │     │    cancel+close+HALT      │
 │   reconciler · state machine · heartbeat file   │     │  status POST to host A    │
 │ watchdog (key K2 or K1): heartbeat, DD −10%,    │     │  dead-man ping            │
 │   flatten loop, re-enable consumer, readback→DB │     └───────────────────────────┘
 │ halt-receiver A · api/web · postgres            │
 └────────────────────────────────────────────────┘     Research: offline, dev machine
```

**Tech:** Python 3.12 (`alpaca-py`, pandas/numpy, Hypothesis), FastAPI + server-rendered
HTML/htmx (React deferred), plain Postgres, parquet for research data, Docker Compose,
`import-linter`, WireGuard. Secrets from a 0600 env file; live keys absent until G3.

**Structural rules (enforced, tested):**
1. **Strategy boundary.** Strategies run in a container on `strat_net` (Docker `internal:
   true`) whose only other member is the engine's Intent listener; `core_net` (engine, db,
   watchdog, api) is unreachable from it. Container: `read_only`, `cap_drop: ALL`,
   non-root, `pids_limit`, `mem_limit`, `cpus`, no shared volumes, no docker socket;
   `alpaca-py`/`httpx`/`requests` not installed. **Intents are JSON over a unix socket**,
   validated by a closed pydantic model (`extra='forbid'`, bounded lengths, symbol must be
   in today's asset master, numeric ranges), max message size, max 10 Intents/s per
   strategy with drop-on-overflow + incident; never pickle/marshal/yaml. `import-linter`
   forbids `strategies → execution|alpaca|httpx|requests|socket` as a second line.
   Acceptance test (1.9): a malicious strategy that tries env/keys, `importlib`, raw
   sockets to `paper-api.alpaca.markets`, `db:5432`, the watchdog port, and a crafted
   payload — all fail.
2. Only the Risk Gate produces Orders (`GatedOrder` type constructible only in the gate
   module).
3. The API service holds no broker keys.

---

## 4. Risk system — the 15% invariant

### 4.1 Stress-loss budget

Each position and each unfilled entry order carries a stress factor `s` = assumed worst
move from entry to the point where we can be flat (including a next-day open for names
that halt into the close):

| Class | s | Basis |
|-------|---|-------|
| SPY, QQQ (and SPLG, QQQM) | 0.20 | Market-wide Level-3 breaker halts the day at −20% from prior close; entries are after the open, so entry-to-close loss ≤ 20% |
| IWM, DIA, sector ETFs | 0.25 | IWM −14% on 2020-03-16 plus LULD band slippage |
| S&P 500 name, market cap ≥ $10B, no scheduled event today or before next open | 0.40 | 2020-03 single-day large-cap moves; earnings excluded |
| Any other single name ("stocks in play") | 1.00 | News halts reopen −70–90% (biotech/FDA); multi-day T1 halts. No market-cap floor is assumed |

Definitions (fractions of `E0`; `N_i` = notional of position or unfilled entry *i*;
`DD = max(DD_now, DD_at_open)` from broker equity, so intraday gains never expand the
budget; reserve 0.015 covers slippage plus ≤ 90 s of trim latency):

```
B = 0.15 − DD − 0.015
L = Σ_i N_i · s_i                      # every position at full stress simultaneously
Invariant: L ≤ B, checked (a) per Intent, using an account snapshot ≤ 5 s old
(re-fetched on each Intent; snapshot age > 30 s → SAFE), and (b) every 30 s.
If L > B because DD grew: trim non-halted positions, largest N·s first (procedure §4.2),
until L ≤ B; if still L > B after trimming everything trimmable → SAFE + alert.
```

Ladder (all latching until the next 09:15 go/no-go unless stated):

| DD from HWM | Action |
|-------------|--------|
| −5% | `r*` × 0.5 |
| −8% | `r*` × 0.25; max 1 position; only the top-ranked strategy |
| −9% | **no new entries** (SAFE) |
| −10% | **hard halt** (engine); watchdog independently flattens at −10% too |
| −11% | off-host flattener cancels, closes, sets HALTED |
| Recovery mode (§4.12) | after owner review: entries only while DD > −11.5%; terminal halt at −12%; watchdog −12.5%; flattener −13% |

Worked cases (E0 = 100%):

| DD at entry | B | Permitted configuration | Event | Result |
|---|---|---|---|---|
| 0 | 0.135 | SPY 67% notional (0.20 × 0.67 = 0.134) | Level-3 day, −20% from prior close, stop fills at halt | −13.4% → DD −13.4%. Holds |
| 0 | 0.135 | 3 in-play names, 4.5% each (Σ 1.0 × 0.135) | all three halt, reopen −90% | −12.2% → DD −12.2%. Holds |
| 0 | 0.135 | 3 large caps, 10% each (Σ 0.4 × 0.30 = 0.12) | 2020-03-16 pattern, all three −25% LULD reopen | −7.5% → DD −7.5%. Holds |
| −5% | 0.085 | SPY 42% | −20% | −8.4% → DD −13.4%. Holds |
| −8% | 0.055 | 1 SPY position 27% | −20% | −5.4% → DD −13.4%. Holds |
| −8.9% (last entry allowed) | 0.046 | 1 SPY 23% | −20% | −4.6% → DD −13.5%. Holds |
| −8.9% | 0.046 | 1 in-play 4.6% | −90% | −4.1% → DD −13.0%. Holds |

Additional hard caps (defense in depth, on E0): single non-ETF name ≤ 10%; gross notional
(positions + open entries) ≤ 100% (broker: multiplier 1); one position **or** open order
per symbol across strategies; ≤ 3 concurrent positions; per-trade stop-distance risk
≤ `r*` (§5.6), 0.25% for a strategy in micro-live (per strategy); daily loss −2% →
flatten, no entries until next session; weekly −4% → flatten, owner ack; per-order
notional ≤ configured $X; entry limit within 1% of last trade; ≤ 20 orders/day/strategy,
≤ 60/day, ≤ 5/min; qty must be ≥ 1 after `floor()` and the rounded qty must satisfy every
limit; per-strategy **stop-distance floor enforced by the gate** (Intent rejected below
it); universe exclusions: scheduled event today or before next open, LULD pause today,
ex-dividend/split today, not `tradable && active`, price < $5, insufficient median volume,
`asset_class != us_equity`.

**Named residuals (not covered by the budget):** (1) a market-wide Level-3 day followed by
a further gap at the next open (SPY has never gapped −5% after an L3 day, but nothing
prevents it); (2) a broker outage that coincides with (1); (3) three simultaneous −100%
single-name outcomes (Σ at s = 1.0 covers −90%). The 5-point gap between the −10% halt and
the 15% requirement is what absorbs these.

### 4.2 Orders (Alpaca-specific, verified unless marked)

- Entry = **DAY bracket**: limit entry (≤ 1% from last), sell-stop (market) leg, limit
  take-profit leg. **Bracket TIF applies to all legs**, so brackets are DAY, and any
  position still open after 16:00 (halted name) gets a **standalone GTC stop-market** at
  the original stop level, placed after the DAY orders expire (whether an order can be
  accepted on a halted symbol is probed in 0.6). Alpaca converts *buy* stops to stop-limit
  but **not sell stops**, so long exits are true market stops. Stop-limit exits are
  prohibited.
- **Every sell path is cancel-then-submit:** cancel that symbol's open sell orders → wait
  until none is `pending_cancel` → submit. Alpaca rejects a second sell against held
  quantity (403 `insufficient qty available`), so this 403 is a "cancel first" signal, not
  a hard incident. Single writer per symbol (§4.6 arbitration).
- **Trim procedure:** cancel legs → confirm → market-sell the trim qty → re-place a stop
  for the remainder.
- Prices rounded to legal ticks (stops rounded away from entry); qty integer; any
  `rejected` order event other than 403-held-qty and 403-buying-power → SAFE.
- `client_order_id = <actor>-<strategy_hash>-<symbol>-<date>-<seq>`; Alpaca enforces
  uniqueness (422). After any submit timeout, query by client order id before retrying. On
  boot, rebuild from `GET /v2/orders?status=all&after=<session_open>` (paginated, 500/page).
- No stop-leg modification on stale data; stale → close via the normal path.
- Halt detection: subscribe to the `statuses` stream for all held symbols (counts toward
  the 30-symbol cap); `sc == "H"` → position state `halted`.

### 4.3 Watchdog (host A, separate container)

- Reads the engine **heartbeat file**, which the reconciler writes at the end of each
  successful cycle with `last_reconcile_ts` and `broker_readback_ts` (liveness *and*
  correctness); polls the broker every 15 s; feed liveness via REST `latest/trades/SPY`
  compared with the engine's last-message timestamp (no second WebSocket — Basic plan
  allows one connection).
- Triggers: heartbeat > 30 s or readback age > 90 s with **open positions or orders**;
  DD ≥ 10%; ≥ 15:57 ET (broker clock/calendar incl. early close) with anything open;
  engine reports DB down > 5 min; `HALT_REQUESTED` file present.
- Action: verified flatten loop (§4.6) with `FLAT-WD-` markers; writes `HALTED_TODAY`;
  writes its own broker readback (positions, orders, equity, flatten state, timestamp)
  to the DB every 15 s for the dashboard; incident row; owner alert.
- Consumes owner re-enable rows (§4.10); dead-man ping every 60 s; `oom_score_adj` lower
  than the engine.

### 4.4 Off-host flattener (host B, different provider; state-independent)

- 09:29:00 snapshot of positions (= overnight carry). 09:30:05–09:30:25: for those symbols
  only, cancel their orders → confirm → market close, `FLAT-AM-` markers. Engine entries
  start 09:32:00 and the go/no-go requires "no position at 09:29 or AM pass reported flat".
- 15:57 ET: if broker readback is non-flat, run the flatten loop (`FLAT-B-`).
- Every 60 s during the session: DD ≥ 11% → flatten loop, then HALTED.
- Serves status to host A every 60 s (signed); its own dead-man ping; `HALT_REQUESTED`
  file from halt-receiver B.
- HWM: receives a signed daily HWM from the watchdog; fallback = broker portfolio history
  minus the flow ledger (§4.7).
- Host B firewall: outbound only to Alpaca, ntfy, host A; inbound only the halt receiver.

### 4.5 Reconciliation (every 30 s and after every fill event)

1. Fetch positions, open orders, account (equity, cash, accrued fees, buying power,
   multiplier, configurations), activities since last check.
2. **Arbitration check first:** if any `FLAT-*` order exists since session open, or
   `suspend_trade == true`, or `HALT_REQUESTED`/`HALTED_TODAY` is set → SAFE-no-submit;
   touch nothing.
3. Local vs broker mismatch → SAFE + alert; two consecutive → flatten with broker truth.
4. **Position-protection invariant:** every open position has exactly one open exit order
   (sell-stop, or a resting market sell during a halt) with `qty == position qty`;
   otherwise cancel-then-place a stop; if that fails within 10 s, cancel-then-close.
5. `L ≤ B` check; trim if violated (§4.2 procedure).
6. Assert multiplier 1, `no_shorting`, `suspend_trade == false` (when not HALTED), options
   level 0, crypto disabled, account id, env; halt on mismatch.
7. Cash identity (§2.5); sanity asserts (§2.2).
8. Write heartbeat file with timestamps.

### 4.6 Verified flatten loop and arbitration

```
un-suspend: GET configurations; if suspend_trade == true → PATCH false (audit row)
loop until broker readback shows 0 open orders AND 0 positions (or only 'halted_hold'):
    DELETE /v2/positions?cancel_orders=true          # cancels and closes in one call
    for positions still open after 20 s: cancel that symbol's sells → confirm → market sell (concurrent per symbol)
    halted symbol: leave the resting market sell; mark 'halted_hold'; page owner
    bounded backoff on 429 (1→2→4→8 s), never abandon; escalate alert every 30 s
report "flat" only from broker readback, with timestamp
suspend_trade = true ONLY after readback 0/0 and no 'halted_hold' exists
```

**Arbitration (broker-visible, no shared state needed):** every actor's orders carry
`FLAT-<actor>-` client-order-id prefixes; priority flattener > watchdog > engine; a
lower-priority actor that sees a higher-priority marker stops submitting. Engine's 15:55
sweep is primary; backstops act only if readback is non-flat at 15:57. Any
watchdog/flattener flatten sets `HALTED_TODAY`.

**Rate budget (per account, 200/min):** engine ≤ 100/min, watchdog ≤ 40, flattener ≤ 40,
20 reserve; the API service never touches the broker.

### 4.7 High-water mark and drawdown ledger

- HWM = max daily closing equity, adjusted **proportionally** for owner withdrawals:
  `HWM ← HWM × (E − W) / E` on a withdrawal `W` from equity `E` (withdrawals are
  permitted only after an owner-acked halt). Deposits are not permitted (HALT). `INT`/`DIV`
  raise equity legitimately. Unit-tested: HWM 100k, E 95k, W 30k → DD 5.0%.
- Authoritative stores: latch/HWM file on a volume mounted read-write in **both** engine
  and watchdog, plus the DB, each with the flow ledger attached. Broker portfolio history
  minus the ledger is an **alert-only cross-check** (a source without a flow ledger is
  never used in `max`). "Agreeing" = within $1. On start each process takes the max of
  the authoritative stores; HWM never decreases except by the withdrawal formula.
- Intraday DD uses broker equity vs HWM; local marks are display-only.

### 4.8 Market-structure hazards

1. **Single-stock LULD/news halts:** `halted` is a first-class state (statuses stream).
   No new entries in a symbol halted today. Halted position: resting market sell stays;
   after 16:00 a standalone GTC stop is placed; the flattener's AM pass closes it at
   09:30:05 via cancel-then-market; incident logged. The budget already priced it at
   s = 1.0 (in-play) or 0.40 (large cap).
2. **Market-wide circuit breakers:** Level 1/2 (−7%/−13%, 15-minute halts, not after
   15:25): cancel entries, keep stops, no new market sells until 60 s after reopen.
   Level 3 (−20%): trading ends for the day; all positions become `halted_hold`, closed
   by the AM pass; budget uses s = 0.20 for SPY/QQQ for this reason. Residual named in
   §4.1.
3. **Corporate actions:** features on `adjustment=all` bars, accounting on raw;
   announcements API (ingested the day after declaration; same-day special dividends are
   invisible — residual); symbols with ex-date or split today excluded.
4. **Asset master** refreshed every morning; only `tradable && active && us_equity`.
5. **Opening auction:** no orders before 09:30:05 (flattener) / 09:32:00 (engine).
6. **True cash-account broker (fallback only):** settled-cash ledger with business-date
   settlement queue, per-lot `funded_by`, GFV count, restriction state;
   `settled_available = settled_at_open − Σ cost of all buys today`.
7. **Shorting (Phase 6, ETFs only):** requires verifying that shorting is permitted at
   multiplier 1 (unverified; if it requires multiplier 2, shorting is dropped — leverage
   is never enabled); SSR detection; `shortable`/`easy_to_borrow`; buy-stop conversion band
   in the budget.

### 4.9 Fault table

| Fault | Detection | Resolution |
|-------|-----------|------------|
| Engine crash/OOM | heartbeat or readback age | watchdog flatten if positions **or orders** open; `HALTED_TODAY`; engine reboots into SAFE for the rest of the session; **2 crashes in a session → HALTED (latching)** |
| Engine hung (heartbeat thread alive, loop dead) | readback age > 90 s | same as crash |
| Engine restart after halt | HALTED = OR(file, DB, `suspend_trade`) | boot refuses to trade; re-enable only via §4.10 |
| Watchdog crash | engine polls watchdog heartbeat; dead-man | engine SAFE if stale > 30 s; owner paged; flattener unaffected |
| Both crash / host A dead | dead-man | flattener 15:57 / 11% / AM rules; runbook: Alpaca dashboard liquidate-all + suspend trading (probed in 0.6) |
| Host B down mid-session | engine polls host B health every 60 s | SAFE for the session if stale > 3 min |
| DB down | engine health | SAFE immediately; latch/HWM live in the file; flatten if > 5 min; **DB down at boot → close all, SAFE** |
| Broker 5xx/429 storm | failed polls | broker-side stops live; after 2 min unreachable → on recovery cancel-all/close-all, halt for the day. Residual: coincident gap |
| Data WS silent disconnect | zero messages > 15 s while open | reconnect + REST poll; stops at broker |
| Trade-update drop | REST order poll every 10 s; replay on reconnect | reconciler ≤ 30 s |
| Clock skew | vs `/v2/clock` each cycle, > 2 s | SAFE |
| Deploy during session | script checks `clock.is_open && (positions || orders)` | refuses unless `--flatten-first` |
| Secrets leak / unknown-cause halt | — | rotation runbook (coordinated across hosts if one key pair) |
| Partial fill / orphan leg | protection invariant | stop placed or position closed (cancel-then-submit) |
| Order stuck `pending_cancel` | flatten loop | wait, then market sell; never "flat" without readback |
| Second sell rejected 403 held-qty | adapter | cancel that symbol's sells first; not an incident |
| Paper/live mix-up | account id + env asserted each cycle | refuse / halt |
| Halted symbol | statuses stream | §4.8.1 |
| L > B with nothing trimmable | budget check | SAFE + alert |
| Notification channel dead | 09:25 "alive" message | missing = alarm |
| Spurious halt (attacker replays token) | idempotent halt | harmless to capital; failed-auth IPs banned; token rotated |

### 4.10 Engine state machine and halt semantics

```
BOOT → RECOVERING (rebuild from broker; HWM = max(file, DB); assert config/id/env;
        DB down → close all; HALTED flag set → HALTED)
     → SAFE (exits only)
     → RUNNING  ONLY from the 09:15 go/no-go; a mid-session boot stays SAFE all session
FLATTENING (engine 15:55 sweep or trigger) → SAFE
HALTED_TODAY (set by any backstop action or crash) → clears at next 09:15 go/no-go
HALTED (latching; −10%, config mismatch, inflow, 2 crashes, owner halt)
```

HALTED = OR over the latch file, the DB row, and `suspend_trade`. **Re-enable:** owner
writes a TOTP-verified row in the DB via the dashboard; the **watchdog** consumes it,
verifies, clears the file, PATCHes `suspend_trade=false`, writes the audit row; the
engine boots to SAFE and reaches RUNNING at the next 09:15. Test: without a valid row,
restart leaves HALTED; with it, engine reaches SAFE and `suspend_trade == false`.

### 4.11 Pre-session go/no-go (09:15 ET; all must pass or the day is skipped)

Clock skew OK · calendar (incl. early close) · asset master refreshed · event exclusions
loaded · no GTC order older than today except a `halted_hold` stop · reconciliation clean ·
watchdog + flattener heartbeats fresh · HWM file and DB agree · multiplier 1,
`no_shorting`, `suspend_trade == false`, options 0, crypto off · no inflow · no HALTED ·
AM pass reported flat · "alive" message sent.

### 4.12 After a −10% halt (defined path)

Default is **terminal**: the owner reviews the post-mortem and decides. Option (b),
recovery mode, keeps the original HWM (the 15% is absolute): `r*` × 0.25, max 1 position,
entries only while DD > −11.5%, terminal halt at −12%, watchdog −12.5%, flattener −13%.
Arithmetic at −11.5%: B = 0.02 → SPY ≤ 10% notional → −20% on it = −2% → DD −13.5%.
Holds.

---

## 5. Strategy layer

### 5.1 Principles

1. A strategy is a pure function `(bars, features, account_state) → Intents`. No I/O.
2. Same code in backtest, paper, live. Identity = `(code_hash, config_hash)`; any change
   = new strategy at Idea. The gate refuses Intents from a hash not at the required state.
   Promotion/demotion rows are append-only and git-committed (the owner is also the
   developer).
3. Portfolio of small, uncorrelated, validated edges; allocation by live track record.
4. No discretion, no news, no sub-second latency.

### 5.2 Candidate strategies (research queue)

| ID | Track | Strategy | Prior evidence | Known weakness |
|----|-------|----------|----------------|----------------|
| S3-ETF | A | VWAP mean-reversion on SPY/QQQ/IWM after 10:00: fade > 2σ from VWAP with volume exhaustion; target VWAP; stop = max(1×ATR(5m), **0.4% floor**); trend-day filter | Execution literature | Must reach 0.75 trades/day; tight stops cannot express `r*` |
| S2 | A | Intraday momentum on SPY/QQQ with noise band (Zarattini, Barbon & Aziz 2024); trailing stop at band; VIX-scaled sizing; exit at close | Sharpe ~1.3–2.4 in paper versions, beta ≈ 0 | Paper uses leverage; we run ≤ 67% notional; costs; regime |
| S1 | B | ORB on stocks in play: RVOL = (pre-market + first-5-min volume)/same-window 14-day avg ≥ 2; price > $5; 5-min OR; stop = OR opposite side or 10% ATR | Zarattini & Aziz; QQQ replication matched *before* costs | Break-even ~2.2¢/share; 76% of PnL from 2022; s = 1.0 caps total notional ≈ 13% |
| S4 | B | Gap continuation/fade | Mixed | Needs SIP pre-market; dividend adjustment |
| S5 | — | Hold cash | 0% DD | Default |

Order: S3-ETF → S2 → (SIP, ≥ $70k) S1 → S4. Long-only until Phase 6.

### 5.3 Research protocol (pre-registered)

1. **Data:** SIP minute bars + NBBO quotes, **≥ 7 years** (Alpaca history from 2016);
   `adjustment=all` for features, raw for accounting. Track A ETFs; Track B ≈ 200 names.
   Point-in-time constituents need an external source (D7); until chosen, Track B G1 is
   blocked.
2. **Fill rules:** signal at bar-t close executes no earlier than bar t+1 open; limit
   entries fill only on trade-through (not touch); stops fill at `min(stop, next open)`
   minus stop slippage, and for Track B at `min(stop − slippage, trigger-bar low + half
   spread)` in stress runs; halts fill at the reopen print; limit targets on trade-through;
   partial fills per capacity.
3. **Costs** per §2.3; stress 1×/2×/3×.
4. **Parameters:** ≤ 5; grid **pre-registered**; selection only inside each train fold
   with a fixed rule; OOS uses per-fold selections; per-fold surfaces reported.
5. **Walk-forward:** anchored *expanding* window, initial train 12 months, 3-month test
   steps.
6. **Holdout:** most recent 12 months evaluated **exactly once per family per 12 months**;
   family = strategy ID × track; registry append-only and git-committed.
7. **Trial registry:** every walk-forward *run* is `(code_hash, config_hash)`; in-fold grid
   points do not count, abandoned runs do; synthetic runs are flagged and excluded from
   holdout burn and DSR counts. DSR computed with N = registered runs in the family, V =
   variance of their OOS Sharpes (floor 0.5² if N < 10), skew/kurtosis from OOS daily
   returns, T = OOS days.
8. **Sharpe:** daily returns at `r*`, annualized ×√252, with standard error.
9. **Regime:** positive in ≥ 3 of 5 OOS years and ≥ 2 of 3 VIX terciles; no year > 50%.
10. **Monte Carlo (one definition everywhere):** stationary block bootstrap on daily PnL
    (block 5–10 days), 252-day horizon, at `r*`, with the ladder simulated;
    **95th-percentile max drawdown ≤ 8%**.
11. **Capacity:** ≤ 1% of the symbol's 20-day median 1-minute volume at the entry minute.
12. **Fixed-cost hurdle:** after-tax expected annual PnL at the intended equity ≥ 2 × (data
    + hosting) for the track.
13. **Trade-rate floor:** ≥ 0.75 trades per trading day over OOS.
14. **Stress-factor validation (Track B):** replay the final `s` table against every LULD/
    halt event in the universe over the window; report max realized reopen loss vs `s`.

### 5.4 Promotion gates (numeric, automatic; state keyed by strategy hash; live metrics in R units)

Definitions: *allocation* = fraction of the strategy's notional cap (§4.1) it may use;
*target* = allocation from §5.5 (100% for a single live strategy); *clean day* = no
demotion trigger, no incident row, reconciliation clean; *band* = bootstrap envelope of the
maximum excursion of the cumulative-R path over n ≤ 100 trades (simultaneous 5%/95%
coverage), evaluated only at n ≥ 10, OOS mean shrunk 50% for the demotion band.

| Gate | From → To | Requirements |
|------|-----------|--------------|
| G1 | Idea → Backtested | §5.3 complete; **DSR ≥ 0.95** (the effective Sharpe bar follows from N); MC 95% MDD ≤ 8% at `r*`; ≥ 300 OOS trades and ≥ 0.75/day; regime rule; fixed-cost hurdle; holdout passed once |
| G2 | Backtested → Paper-done | Paper on the same feed as live, ≥ 40 trading days and ≥ 30 trades (a **plumbing gate**, t ≈ 1.4 — not evidence of edge); cumulative R inside the band; counterfactual slippage (paper fills re-priced against historical SIP NBBO) ≤ modeled; modeled fees subtracted from paper PnL regardless of whether paper debits them; **per-minute signal-state agreement** between live feed and nightly SIP replay: 40-day mean ≥ 95%, no day < 90%; reconciliation clean |
| G3 | Paper-done → Micro-live | Phase-1 tests green on the current commit; chaos suite passed within 30 days; watchdog **and** flattener each performed a live 1-share close-all drill; HWM seeded; broker config asserted; owner TOTP. Allocation = `max(1 share, 10%)`, per-trade risk 0.25% (this strategy only) — with SPLG/QQQM for share granularity |
| G4 | Micro-live → Full | ≥ 40 trading days, ≥ 30 live trades (plumbing gate); realized slippage (real fills) ≤ 1.5× modeled; cumulative R inside the band; live MDD in R ≤ MC 95% MDD in R; then allocation ramps 10→25→50→100% of target, each step after 20 clean days |
| Portfolio gate | before a 2nd strategy gets allocation | day-block-bootstrapped portfolio MC 95% MDD ≤ 8% at combined `r*`; 60-day PnL correlation with each live strategy < 0.6 |
| Demotion | one level down | cumulative R below the demotion band at any n ≥ 10, **or** live MDD (R) > MC 95%, **or** slippage > 1.5× modeled over 30 trades. Flattens that strategy, allocation 0; re-promotion needs a fresh full window; two demotions in 6 months → Idea |

### 5.5 Allocation across strategies (only once ≥ 2 strategies are at G4)

¼-Kelly on OOS trade distributions, capped by §4.1; correlation guard; weekly rebalance
±10 pp. Deferred until needed.

### 5.6 Risk per trade `r*` (derived)

`r* = max r ≤ 1.0% such that the §5.3.10 Monte Carlo (252 days, day-block bootstrap, ladder
simulated) gives 95% MDD ≤ 8%`; recomputed monthly on live + OOS; initial 0.4%. Published
as a table `r*(Sharpe, trades/day)` so the owner sees the growth ceiling before D1
(indicatively: Sharpe 1 → ≈ 0.3%; Sharpe 2 → ≈ 0.5%). Each strategy declares a
stop-distance floor and the gate enforces it, so `r_eff = min(r*, stop% × notional cap)`
is reachable.

---

## 6. Growth mechanics and economics

### 6.1 Expected returns and minimum capital (the owner must see this before D1)

`E[gross] ≈ Sharpe × σ_annual`, `σ_annual ≈ r_eff × σ_R × √(trades/yr)`. With `r_eff`
0.3–0.5%, `σ_R ≈ 1`, ~250 trades/yr: σ_annual ≈ 5–8%; Sharpe 1–2 → **gross 4–16%/yr**
for one Track A strategy. Two uncorrelated strategies under the same drawdown budget add
roughly 1.4× (not 2×). Tax at 30% on gross; fixed costs non-deductible.

| Starting equity | Track | Gross (4–16%) | Tax (30%) | Fixed cost | Net | Net % |
|-----------------|-------|---------------|-----------|------------|-----|-------|
| $5,000 | A | $200–800 | $60–240 | $180 | −$40 to +$380 | −1% to 8% |
| $10,000 | A | $400–1,600 | $120–480 | $180 | $100–940 | 1–9% |
| $25,000 | A | $1,000–4,000 | $300–1,200 | $180 | $520–2,620 | 2–10% |
| $70,000 | A+B | $2,800–11,200 | $840–3,360 | $1,370 | $590–6,470 | 1–9% |
| $150,000 | A+B | $6,000–24,000 | $1,800–7,200 | $1,370 | $2,830–15,430 | 2–10% |

Single numbers, derived from this table: **minimum $10,000 for Track A; $70,000 for Track
B** (Track B also cannot deploy more than ≈ 13% of equity in single names at s = 1.0, so
its marginal contribution is small). Below $10,000 the plan recommends not running live.

**Shutdown rule:** after 12 months at 100% allocation, if net trading PnL (after fees,
before fixed costs) < fixed costs for those 12 months, stop and tell the owner. The clock
does not run during ramp.

### 6.2 Compounding rules

- All limits are fractions of `E0`; size scales with the account; HWM ratchets on daily
  closes; the ladder protects the new peak.
- **Leverage: never** (`max_margin_multiplier=1`); gross ≤ 100% of E0, and the stress
  budget usually binds below that.
- Shorting: Phase 6, ETFs only, only if permitted at multiplier 1.
- `r*` re-derived monthly.

### 6.3 Tax and journal

- Journal keeps FIFO lots with wash-sale adjustment (a loss in SPY by S3 followed within 30
  days by any SPY buy from any strategy is a wash sale); the export reconciles **to** the
  broker's realized-gain file / 1099-B, not the other way. December losses defer into the
  next year unless the symbol is not re-bought for 31 days — accepted and reported.
- Section 475(f)/Trader Tax Status is unlikely at ~190 trades/yr; the $3,000 net-loss cap
  applies; election deadline April 15 (D6 with a tax advisor).

---

## 7. Web app specification

**Exposure:** dashboard only over WireGuard/Tailscale. Public endpoints: `POST /halt` on
halt-receiver A and B — separate no-key containers that atomically write
`HALT_REQUESTED` (source IP, timestamp) to the watchdog/flattener volume; the safety
processes poll that file every 1 s. Token ≥ 32 random bytes, constant-time compare,
rotatable via env, different per host; **valid-token requests are never rate-limited**;
failed auth is banned by IP. Response `202 {incident_id}`; ntfy confirms "halt received"
then "confirmed flat at HH:MM:SS". Phone Shortcut with the token is set up in Phase 0 and
exercised monthly in paper. Re-enable is never reachable from the halt route. Dashboard:
TOTP on login and on every state change; 12-hour sessions; lockout after 5 failures; CSRF.

**Pages**
1. **Overview** — PAPER/LIVE banner + account id; engine state with "confirmed flat at
   HH:MM:SS" vs "halt sent, awaiting readback"; **engine readback and watchdog readback
   side by side with ages**; flattener last status (age); equity, HWM (value, sources,
   agreement), DD gauge with the 5/8/9/10/11/12/15 ladder; day/week PnL; budget usage `L/B`;
   feed health; `suspend_trade` state; `FLAT-*` markers present; request budget used/min and
   last 429; last rejection reason; halt-token last-used IP; HALT button.
2. **Positions & Orders** — entry, stop, target, qty, notional, `s`, unrealized PnL, time in
   trade, state (open/halted/halted_hold), strategy hash; "close now" routes via the
   watchdog.
3. **Strategies** — gate state, allocation, cumulative-R vs band, realized vs modeled
   slippage, signal agreement, promotion/demotion history (append-only); approve G3, pause.
4. **Research** — runs, hashes, OOS metrics, DSR with N, MC MDD, per-fold surfaces,
   holdout status; "promote to paper".
5. **Journal / Audit** — every Intent, gate decision, order, fill, rejection, reconciliation
   result, incident, cash-flow event, lot/wash-sale ledger; export reconciles to 1099-B.
6. **Settings** — notifications; read-only limits (versioned YAML); re-enable action (TOTP).

Notifications: halt, SAFE entry, gate change, backstop action, mismatch, cash-flow event,
09:25 "alive", 16:05 summary, missed dead-man.

---

## 8. Operations

- Host A Compose: `strategies`, `engine`, `watchdog`, `halt-receiver`, `api`, `db`.
  Host B: `flattener`, `halt-receiver`. Research on the dev machine.
- Broker clock is the reference; chrony on both hosts.
- Morning: asset master, event calendar, go/no-go. Deploy guard. Nightly DB backup with a
  quarterly **restore drill**; key-rotation drill (coordinated across hosts).
- Weekly report: PnL (gross, net, after-tax est.), DD, per-strategy stats, slippage vs
  model, costs, incidents, budget usage, wash-sale adjustments.
- Runbooks: broker outage, data outage, engine crash with open positions, halted symbol,
  mismatched fill, key rotation, re-enable, **Alpaca dashboard liquidate-all + suspend
  trading** (on the owner's phone), monthly halt-path exercise.

---

## 9. Testing strategy

- **Fake broker** (adapter contract): partial fills, rejects incl. 403 held-qty and 403
  buying-power, 429 storms, latency, `pending_cancel` stalls, LULD and market-wide halts,
  gap opens, activities injection, `suspend_trade` semantics, bracket TIF semantics.
  Contract suite passes against fake and Alpaca paper.
- **Unit:** every §4.1 rule incl. Σ budget, trim, ladder; tick/qty rounding; idempotent ids;
  HWM proportional adjustment and max-of-stores; cash identity; activity allow-list;
  calendar/early close; MWCB rules; Intent schema rejection of crafted payloads.
- **Property-based (Hypothesis):** random fill/price/halt/flow sequences through the gate +
  reconciler + fake broker never produce DD > 10% without a halt and never leave `L > B`
  unresolved (trim or SAFE) after one cycle.
- **Simulation harness:** historical replays (2020-03-16, 2024-08-05, a T1-halt day)
  through live engine code + fake broker; invariant asserted.
- **Chaos (paper, session hours):** `docker pause engine` → watchdog flat ≤ 60 s +
  `HALTED_TODAY`; pause watchdog → engine SAFE, dead-man alert; pause both → flattener flat
  by 15:58; **all three actors flatten simultaneously → one clean flat, zero 403-induced
  SAFE transitions**; cut network → SAFE; duplicate fill → one position; stale data → exit;
  halt + `docker restart engine` (with `_test_always_buy` active) → 0 orders in 5 min and ≥
  5 Intents rejected `HALTED`; re-enable without a valid TOTP row → still HALTED; with it →
  SAFE and `suspend_trade == false`.
- **Malicious strategy test** (§3 rule 1).
- **Backtest reproducibility:** identical metrics on re-run; 1,000 synthetic random
  strategies → ≤ 0.5% pass G1, flagged synthetic.

---

## 10. Roadmap (each step: runnable, falsifiable acceptance test)

Calendar for one developer: Phase 0 ≈ 1–2 weeks; Phase 1 ≈ **10–12 weeks** (session-hour
tests get one attempt per day); Phase 2 ≈ 4 weeks; each strategy 2–4 weeks; paper 40
trading days; micro-live 40 days; ramp 60 days → **first strategy at full allocation ≈
11–13 months**.

### Phase 0 — Decisions, accounts, broker facts
- 0.1 `docs/DECISIONS.md` with D1–D7 answered or defaults accepted. *Accept:* file complete.
- 0.2 Alpaca account; paper keys; test two simultaneous key pairs. *Accept:* result
  recorded; §4.4 key design chosen.
- 0.3 Paper config: multiplier 1, `no_shorting`, options 0, crypto off. *Accept:* readback
  matches; the exact accepted PATCH fields recorded.
- 0.4 Notification channel + phone halt Shortcut. *Accept:* a POST **from the phone** yields
  `202` and the ntfy confirmation.
- 0.5 Host B + dead-man service + WireGuard. *Accept:* missed ping alerts; dashboard port
  unreachable from the public internet (`nmap` from outside).
- 0.6 **Broker semantics probe → `docs/BROKER_FACTS.md`** (each fact with the captured
  request/response and date): does `suspend_trade` block `DELETE /positions`, market sells,
  and dashboard liquidate-all; bracket parent/leg TIF sharing; child-leg qty on partial
  fills; 403 on a second sell against held qty; WebSocket connection limit on Basic; can an
  order be accepted on a halted symbol; is shorting allowed at multiplier 1; paper fee
  debits; paper `suspend_trade`; portfolio-history cash-flow fields; activity type codes for
  ACH/wire. *Accept:* table complete; §4.2/§4.4/§4.8 amended.

### Phase 1 — Skeleton, fake broker, gate, watchdog, flattener, halt
- 1.1 Scaffold, Compose (two networks, hardened strategy container), Postgres, CI (lint,
  import-linter, tests). *Accept:* `compose up` healthy; CI green.
- 1.2 Broker adapter interface + Alpaca paper impl (account, configurations, positions,
  orders, brackets, cancel/close, clock, calendar, activities, portfolio history, statuses
  stream). *Accept:* in session hours, 1-share bracket placed, both legs verified with
  correct qty, cancelled, readback 0/0.
- 1.2b **Fake broker** per §9. *Accept:* contract suite passes against fake and paper.
- 1.3 Verified flatten loop + arbitration markers + un-suspend ordering. *Accept:* against
  the fake broker: `pending_cancel` stall, 403 held-qty, `suspend_trade=true` at start, and
  three concurrent actors → one clean flat, correct priority, `suspend_trade` set only after
  0/0.
- 1.4 Risk gate: Σ budget, ladder, trim procedure, caps, rounding, stop-distance floor,
  snapshot-age rule, universe exclusions, Intent schema. *Accept:* unit tests per rule;
  Hypothesis 10,000 cases (§9).
- 1.5 HWM ledger (file + DB, proportional flows) + cash identity + activity allow-list.
  *Accept:* delete DB → HWM unchanged; fake-broker injected `CSD`/`JNLC`/`ACATC` → HALT
  same cycle; injected `INT` → no halt, HWM may rise; paper "reset" (cash changes, no
  activity) → identity check fires.
- 1.6 Reconciler: protection invariant (cancel-then-place), config asserts, arbitration
  check. *Accept:* cancel a stop leg in the paper dashboard → new stop ≤ 30 s; set
  `no_shorting=false` → HALTED; then re-enable path per §4.10 test.
- 1.7 State machine + latching halt + `HALTED_TODAY` + go/no-go + test fixtures
  (`strategies/_test_always_buy`, paper-only; `--seed-position`). *Accept:* the halt/
  restart chaos test in §9; mid-session boot stays SAFE.
- 1.8 Watchdog (heartbeat file with timestamps, DD −10%, 15:57, `HALT_REQUESTED`, readback
  to DB, re-enable consumer, dead-man). *Accept:* pause engine with a seeded position → flat
  ≤ 60 s, `HALTED_TODAY`, incident row; halt-receiver POST with engine paused → flat.
- 1.9 Strategy isolation + malicious strategy test (§3). *Accept:* all bypass attempts fail;
  import-linter fails on a forbidden import; crafted payload rejected with incident.
- 1.10 Off-host flattener (AM pass, 15:57, 11%, status POST, `FLATTENER_HWM_OVERRIDE`
  honored only for the paper account id). *Accept:* pause engine + watchdog at 15:50 with a
  seeded position → flat by 15:58; override on a live id ignored (unit test); AM pass closes
  a seeded overnight position and does not touch a 09:32 entry.
- 1.11 Dashboard (server-rendered) with §7.1 fields; HALT button → halt receiver. *Accept:*
  HALT with API stopped still flattens; watchdog readback visible with engine paused.
- 1.12 Rate budget per process; deploy guard; backups + restore drill; key-rotation drill;
  runbooks; one-command chaos suite. *Accept:* all §9 chaos tests pass in paper.

### Phase 2 — Data & research infrastructure
- 2.1 Historical loader (SIP bars + quotes, adjusted and raw, ≥ 7 years) + daily updater.
  *Accept:* ≥ 99.5% of session minutes per symbol-day; zero duplicate timestamps; a known
  split reproduces the adjusted series.
- 2.2 Backtester sharing the engine interface; §5.3.2 fill rules; §2.3 costs from NBBO.
  *Accept:* toy strategy reproduces hand-computed PnL to the cent incl. fees; gap-through
  stop fills at the open; limit entry fills only on trade-through.
- 2.3 Walk-forward runner (expanding), per-fold selection, holdout lock per family, trial
  registry (refuses unregistered; synthetic flag), DSR with N, block-bootstrap MC, `r*`
  table, regime table. *Accept:* 1,000 synthetic strategies → ≤ 0.5% pass G1 and none burns
  a holdout; unregistered run refused.
- 2.4 Research page. *Accept:* a G1 report renders every §5.4 field.

### Phase 3 — Strategy research (S3-ETF → S2 → [SIP, ≥ $70k] S1 → S4)
- 3.x Pre-register grid → implement → folds → stress → regime, MC, capacity, hurdle,
  stress-factor validation (Track B) → holdout once → G1 record. *Accept:* PASS with every
  number or FAIL with reason. **FAIL is a valid outcome.**

### Phase 4 — Paper (same feed as live)
- 4.1 Reset paper equity to D1; run G1-passed strategies with the full gate. *Accept:* ≥ 40
  days, ≥ 30 trades, band check, counterfactual slippage, signal agreement, fee handling
  recorded, reconciliation clean.
- 4.2 Monthly chaos re-run and halt-path exercise. *Accept:* all pass.

### Phase 5 — Micro-live
- 5.1 G3 checklist; fund with D1 exactly; live keys on both hosts; 1-share live close-all
  drills by watchdog and flattener. *Accept:* drills logged; activities show one `CSD`
  predating go-live.
- 5.2 `max(1 share, 10%)` allocation / 0.25% risk for ≥ 40 days. *Accept:* G4 metrics or
  demotion; weekly review; post-mortem per halt.

### Phase 6 — Scale
- 6.1 Ramp per G4 (each step: 20 clean days verified from the journal). 6.2 Second strategy
  after the portfolio gate. 6.3 SIP + Track B at ≥ $70k (or D2). 6.4 ETF shorting only if
  permitted at multiplier 1 and after its own gate. *Accept:* numeric gate evidence per
  step.

---

## 11. Open decisions for the owner

| ID | Decision | Default if unanswered |
|----|----------|-----------------------|
| D1 | Starting capital | ≥ $10,000 for Track A; below that, do not go live |
| D2 | Pay $99/mo SIP before $70k | No |
| D3 | Notification channel(s) | ntfy + email |
| D4 | Hosting | Host A US-East VPS; Host B different provider |
| D5 | Shorting ever | ETFs only, Phase 6, if allowed at multiplier 1 |
| D6 | Marginal tax rate; 475(f) | 30%; no election (advisor) |
| D7 | Point-in-time universe source for Track B | None → Track B research blocked |

---

## 12. Sources consulted (2026-09-02)

- Gauntlet Loop: github.com/trilwu/gauntlet-loop-skills; github.com/NicholasSpisak/gauntlet-loop
- Robinhood API status: github.com/sanko/Robinhood; apidog.com; bitget.com/wiki
- PDT retirement: SEC order on SR-FINRA-2025-017; FINRA Regulatory Notice 26-10; Alpaca 2026-06-03 changelog (PDT/DTBP deprecation); schwab.com; tastytrade.com
- Alpaca: cash-account and unsettled-funds support pages; intraday margin framework blog; account configurations (`max_margin_multiplier`, `no_shorting`, `suspend_trade`); orders doc (buy-stop conversion only; halts); bracket TIF (order-types article); 403 insufficient-qty forum thread and Alpaca-API issue #282; rate-limit support page (per account); paper-trading doc (github.com/alpacahq/alpaca-docs); account activities and activity enums; high-yield cash program; portfolio history v2; real-time data `statuses`; corporate-actions announcements; alpaca-py README
- Market structure: Nasdaq MWCB FAQ (L1/L2/L3)
- Fees: FINRA Information Notice 2026-03-17 (Section 31); FINRA TAF 2026; CAT fee alerts (2026-1, HA 1A)
- Tax: Trader Tax Status and 475(f) deadline guides (terms.law)
- Profitability: Jordan & Diltz (FAJ 2003); Chague, De-Losso & Giovannetti
- Strategies: Zarattini & Aziz (SSRN 4416622, 4729284); Zarattini, Barbon & Aziz 2024; replication github.com/giovannibrusco/zarattini-2023-orb-qqq
- Backtest hygiene: Bailey & López de Prado, "The Deflated Sharpe Ratio" (2014)
