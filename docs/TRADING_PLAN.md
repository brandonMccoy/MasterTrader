# MasterTrader — Automated Day-Trading Web App: Master Plan

Status: **v4 — final after Gauntlet rounds 1–3 and smoothing.** Critique history and the
list of gaps that remain open: `docs/GAUNTLET_LOG.md` and §13 below.
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

**The arithmetic the owner must accept in writing before funding (§6.1):** under a hard
15% drawdown constraint, the risk per trade that the stop floor and the notional cap allow
on index ETFs is about **0.2–0.3% of equity**. At ~190 trades a
year that is an annual volatility of roughly 3–4%, so a genuinely good strategy (Sharpe
1–2 after costs) yields **≈ 3–7% gross per year**, before tax and before the drawdown
ladder's haircut. Year one is negative regardless of edge (11–13 months to full
allocation; fixed costs ~$180/yr). **Below ~$15,000 the ETF track cannot clear its
fixed-cost hurdle after tax at the policy assumption of Sharpe ~1.2. Single-name trading ("stocks in play") cannot clear its
hurdle at any capital level under this constraint and is deprioritized indefinitely.**
The honest expected outcome for most strategy candidates is "does not pass the gates," in
which case the system holds cash (which earns the broker's cash yield, credited outside
trading PnL).

**The objective is therefore:**

> Maximize expected after-tax compounded growth of one fixed starting balance,
> **subject to** equity never dropping more than 15% below its high-water mark, trading
> only strategies that survived a pre-registered, cost-inclusive, out-of-sample pipeline.
> Capital is **deployed on out-of-sample evidence and withdrawn on live evidence** — the
> live gates have enough power to detect breakage, not to prove edge.

**Design principle:** the risk system is the product; strategies are replaceable
plug-ins.

**Interpretation of the 15% rule (stated assumption):** maximum drawdown from the
high-water mark (HWM) ≤ 15%, where HWM = the highest *daily closing* equity, proportionally
adjusted for owner withdrawals (§4.7), and drawdown is checked continuously against
broker-reported equity.

---

## 1. Quality bar (the Gauntlet "bar")

| # | Bar item | Evidence |
|---|----------|----------|
| B1 | Drawdown invariant enforced by a layer strategies cannot bypass, with broker-side backup and an off-host backstop; the budget arithmetic holds under stated worst cases with entry-relative stress factors, and residuals are named. | §4.1, §4.2–4.6 |
| B2 | No live capital on an unvalidated strategy; gates numeric, mutually consistent, in defined units, codable, with their statistical power stated honestly. | §5.4 |
| B3 | Backtests cost-inclusive (spread-aware slippage from a feasible data plan, dated fees, fixed costs, tax) and overfitting-resistant (per-fold selection with a named rule, once-only holdout per track, DSR with pinned units and trial count). | §2.3, §5.3 |
| B4 | Operates within the broker's actual rules (account model, bracket TIF, held-qty rejects, per-tape halt codes, market-wide breakers, `opg` auction orders, ticks, asset master, paper-account limits). | §2.2, §2.4, §4.2, §4.8 |
| B5 | Notional never exceeds equity; leverage/shorting disabled at the broker; external flows detected the same cycle (to SAFE) with a cash-continuity gate at the open; HWM flow-adjusted with one formula and a pinned timing. | §2.5, §4.7 |
| B6 | Every failure resolves to flat-and-halted or a named residual; **one** halt semantic (latching, owner re-enable); defined writers/clearers for every store; restart cannot re-arm mid-session; concurrent actors arbitrated with a single order-writer. | §4.9, §4.10 |
| B7 | Owner has fresh visibility with host A dead and a halt that works with engine/API/host dead; the halt response tells the truth about whether anyone is listening. | §7 |
| B8 | Roadmap steps have runnable, falsifiable acceptance tests (fake broker where paper cannot exercise them); calendar states its hours assumption. | §10 |

Reference standards: FINRA Rule 15c3-5; Bailey & López de Prado (DSR); walk-forward.

---

## 2. Hard constraints (verified 2026-09-02; unverified items marked → probed in 0.6)

### 2.1 Broker

- Robinhood: no official stock API; ToS prohibits automation. **Rejected.** The Alpaca web
  dashboard is the Robinhood-like view. **Any manual trade, transfer, ACAT, or journal in
  this account is treated as hostile (SAFE, then HALTED if unexplained).** The owner must
  hold no SPY/QQQ/IWM/DIA/SPLG/QQQM (or VOO/IVV — "substantially identical" is unresolved)
  in any other account, IRA included, while live (§6.3).
- Alpaca: API-first, commission-free, `alpaca-py` (Python ≥ 3.10), REST + WebSocket,
  brackets, paper environment. Rate limit **~200 req/min per account**. `client_order_id`
  ≤ 128 chars. Orders list 500/page.
- Backups: Tradier, Interactive Brokers, via the adapter interface.

### 2.2 Account model, regulation, broker-side configuration

- **No cash accounts**; below $2,000 = limited margin (1×, no shorting, unsettled funds
  reusable). Irrelevant at the recommended minimum capital.
- PDT rule retired 2026-06-04; Alpaca removed PDT/DTBP fields 2026-07-06. `dtbp_check` is
  not used.
- `PATCH /v2/account/configurations`: `max_margin_multiplier="1"`, `no_shorting=true`,
  `fractional_trading=false`, `max_options_trading_level=0`; account `crypto_status` not
  ACTIVE; `suspend_trade` semantics (does it block closing sells? dashboard liquidate-all?)
  **probed in 0.6**. With multiplier 1 and long-only no debit can arise; asserted each cycle:
  `buying_power ≤ cash` (equality **unverified** post-June-2026), `equity ≥
  maintenance_margin`.
- Multiple key pairs per live account: **unverified**; since the rate limit is per
  account, keys buy no independence. Independence = separate hosts and processes.
- Broker-side stops are **broker-simulated** (held in Alpaca's OMS, not on-exchange):
  during a broker outage the only protection is `L ≤ B` (§4.1).
- Owner disclosures: margin agreement and FINRA 4210 disclosures; opt out of fully-paid
  lending; cash yield (`INT`) is credited to cash, not trading PnL; SIP requires
  non-professional self-certification; 1099-B carries wash-sale adjustments; estimated
  quarterly taxes on short-term gains.

### 2.3 Costs (dated; the backtester and weekly report key every constant by effective date)

| Cost | Value | Applied |
|------|-------|---------|
| Commission | $0 | — |
| SEC Section 31 | $20.60 per $1M sold from 2026-04-04; resets each fiscal year | sells |
| FINRA TAF | $0.000195/share (cap $9.79) through 2026-12-31; **$0.000232 (cap $11.61) from 2027-01-01** (filed) | sells |
| CAT | $0.000001 + $0.000002/share | all executions |
| Slippage, entry (Track A) | `max($0.02/share, half NBBO spread at the fill minute) + 5 bp` | fills |
| Slippage, stop exit | `max($0.04/share, full spread) + 10 bp` | stop fills |
| Stress | 1×, 2×, 3×; **all G1 statistics computed on the 2× run** (Track A) | G1 |
| Tick size | round to $0.01; half-penny ticks (Rule 612) arrive Nov 2026 for tick-constrained names incl. SPY; $0.01 rounding remains legal; slippage floors were set under penny ticks | §4.2 |
| Market data | Basic: free, IEX (~2% of volume), ~30 symbols, **one WebSocket**. Algo Trader Plus: $99/mo, SIP, 10,000 req/min | §2.4 |
| Hosting | ~$180/yr | §6.1 |
| Tax | **federal only — the owner lives in San Antonio, Texas; Texas has no state or local income tax.** Short-term gains at the owner's federal marginal rate (D6; **24% assumed** until the owner states their bracket), NIIT 3.8% only above $200k MAGI single / $250k joint, on **positive** net; losses carry forward, $3,000/yr against ordinary income; fixed costs not deductible without Trader Tax Status (unlikely at ~190 trades/yr; Section 212 deductions suspended permanently); wash sales §6.3 | §6.1 |

**Quote-data feasibility:** bulk-loading NBBO history is infeasible on Basic (SPY alone is
~10M quotes/day). Quotes are fetched only for the `[t, t+1 min]` window of each candidate
fill, cached per symbol-minute. That is a few hundred requests per run for Track A.

### 2.4 Data plan and session rules

| Track | Instruments | Feed | Status |
|-------|-------------|------|--------|
| A | SPY, SPLG, QQQ, QQQM (IWM/DIA/sector ETFs only if their stress factor leaves a usable notional) | IEX; nightly SIP replay agreement gate | active; equity ≥ $15k |
| B | single names | SIP | **deprioritized: cannot pass the fixed-cost hurdle under s = 1.0 (§6.1)**; research only if economics change |

Regular session only. Flattener owns 09:19–09:31:45 for overnight carry; **engine entries
from 09:32:00**; no extended hours; everything flat by 15:55 (engine) / 15:57 (backstops).

### 2.5 Capital and external-flow detection

- One initial deposit (D1). Detection, not the absence of code, is the control:
  1. **Every cycle:** `pending_transfer_in == 0 and pending_transfer_out == 0` (fields on
     the account) else SAFE + alert (instant ACH reflects in buying power before any
     activity posts).
  2. **Cash identity every cycle:** `Δcash − Σ fill_cash + Σ FEE_today = 0 ± $1`, where
     `fill_cash` comes from the **broker's own closed orders** (`filled_avg_price ×
     filled_qty`, signed by side: sells +, buys −) fetched *after* the account snapshot in
     the same cycle, `accrued_fees`
     tracked separately (fee/cash field semantics pinned in 0.6). A residual → **SAFE** and
     freeze `E0`/HWM at pre-residual values (fill-event race is the common cause); HALTED if
     unexplained after two consecutive cycles or if a non-allow-listed activity appears.
  3. **09:15 cash-continuity gate:** `cash_at_open == cash_at_prev_close + Σ allow-listed
     activities since prev close ± $1`, else no-go.
  4. **Activities** paged by id (`direction=asc` from last seen id) with a trailing
     5-business-day rescan; run after 18:30 ET and again at 09:15. Allow-list: `FILL`,
     `FEE`, `PTC` (loss), `INT` (negative → alert), `DIV*`, and a `CSW` whose id matches a
     flow-ledger row (§4.7; also included in the continuity sum). Corporate-action types (`SSO`,
     `REORG`, `MA`, …) on a `halted_hold` name → SAFE + owner review. Anything else with
     `net_amount ≠ 0` (`CSD`, unmatched `CSW`, `JNL*`, `ACAT*`, `FOPT`) → HALTED.
- Sizing equity `E0 = min(day-start equity − accrued_fees, buying_power)`; a 403
  buying-power reject is a sizing-bug alert (SAFE).

---

## 3. System architecture

```
 Owner ── WireGuard ──► Dashboard on A (api+web; NO keys; reads DB) · GET /status on B (signed)
 Owner's phone ── public HTTPS ──► halt-receiver A ─► HALT_REQUESTED (own volume) ─► watchdog
 Owner's phone ── public HTTPS ──► halt-receiver B ─► HALT_REQUESTED (own volume) ─► flattener
 Owner ── Alpaca dashboard ──► liquidate all, then suspend trading (ultimate manual path)

 HOST A                                                  HOST B (different provider)
 ┌───────────────────────────────────────────────┐      ┌──────────────────────────┐
 │ strategies: NO keys, NO egress, RO fs, cap_drop│      │ flattener (K2 or K1)     │
 │   ALL, non-root, limits; socket-only volume RO │      │  09:19 snapshot; 09:20   │
 │   ── JSON Intents, one socket per strategy ────┼─┐    │   opg sells; 09:30:05    │
 │ engine (K1): feed, strategy host, RISK GATE,   │ │    │   fallback; 15:57 pass;  │
 │   single order-writer, reconciler, heartbeat   │◄┘    │   16:00:30 GTC stops for │
 │ watchdog (K2 or K1): heartbeat, DD, flatten,   │      │   halted names; DD ≥ 11% │
 │   re-enable consumer (holds TOTP secret),      │      │  ntfy per action; signed │
 │   readback → DB, HWM push → B                  │      │   status; dead-man       │
 │ halt-receiver A · api/web · postgres           │      │ halt-receiver B          │
 └───────────────────────────────────────────────┘      └──────────────────────────┘
```

**Tech:** Python 3.12, FastAPI + server-rendered HTML, Postgres, parquet, Docker Compose,
`import-linter`, WireGuard, Let's Encrypt with expiry monitoring.

**Structural rules:**
1. **Strategy boundary.** Strategy container on `strat_net` (`internal: true`) whose only
   other member is the engine's Intent listener; a dedicated volume containing only the
   unix socket, mounted **read-only** in the strategy container (connect works on RO
   mounts); one connection per strategy, backlog 1, excess connections dropped.
   **The engine computes `code_hash` from the mounted strategy source at boot and binds
   each socket to that hash; any hash field inside an Intent is ignored.** Intents are JSON
   validated by a closed pydantic model (`extra='forbid'`, bounded lengths, symbol in
   today's asset master, numeric ranges), max message size, max 10 Intents/s with
   drop-on-overflow + incident; never pickle. `import-linter` as a second line.
   `strategies/_test_*` fixtures, `--seed-position`, and `FLATTENER_HWM_OVERRIDE` are
   **refused when the broker account id equals the configured LIVE id**; CI asserts the
   live image excludes `_test_*`.
2. Only the Risk Gate produces Orders; the engine has **one order-writer task** with
   per-symbol locks; the reconciler runs under a mutex (skip if running); in-flight own
   orders are excluded from mismatch counting.
3. The API service holds no broker keys and no re-enable TOTP secret (login TOTP uses a
   separate secret).
4. The broker adapter contains the per-process rate limiter from step 1.2 (engine ≤ 100/min,
   watchdog ≤ 40, flattener ≤ 40, 20 reserve); account snapshot is a **5 s TTL cache**.

---

## 4. Risk system — the 15% invariant

### 4.1 Stress-loss budget

Stress factor `s` = assumed worst move from entry to the point where we can be flat
(including a next-day open for names that halt into the close):

| Class | s_class | Notional cap | Basis |
|-------|---------|--------------|-------|
| SPY, SPLG | 0.20 | — | Level-3 breaker (S&P −20% from prior close) ends the day |
| QQQ, QQQM | 0.25 | — | beta 1.1–1.25 to the S&P on an L3 day |
| IWM, DIA, sector ETFs | 0.35 | — | XLE −20% on 2020-03-09 with SPY −7.6%; leading sector −30–35% on an L3 day |
| S&P 500 name, cap ≥ $50B, not biotech/pharma, no scheduled event | 0.40 | 5% each | unscheduled-news moves |
| Any other single name | 1.00 | 10% | news halts reopen −70–90%; multi-day halts |

**Per-Intent stress is entry-relative:** `s_i = max(s_class, 1 − (1 − s_class) ×
prior_close / limit_price)` — an entry 5% above prior close on SPY carries s = 0.238.

```
E0     = min(day-start equity − accrued_fees, buying_power)   # all fractions below are of E0
DD_eff = max(DD_now, session running-max DD)                   # intraday recoveries never expand the budget
B      = 0.15 − DD_eff − 0.015                                 # reserve = s-model error + slippage (≈ 2.2 pts of s at 67%)
N_i    = entry notional (avg fill × qty), or limit_price × qty for an unfilled entry
L      = Σ_i N_i · s_i
Invariant L ≤ B: per Intent (snapshot ≤ 5 s old; 5–30 s → refresh and re-check, reject the
Intent if still stale; age > 30 s → SAFE) and every 30 s.
If L > B because DD grew: close the largest N·s non-halted position outright (no trim);
repeat; if L > B with nothing closable → SAFE + alert (halted names are already priced).
Bound by construction: terminal DD ≤ DD_eff + B = 13.5%.
```

Ladder (latching until the next 09:15 go/no-go); `r_current = r* × multiplier`:

| DD_eff | Action |
|--------|--------|
| −5% | multiplier 0.5 |
| −8% | multiplier 0.25; max 1 position; top-ranked strategy only |
| −9% | no new entries (SAFE) |
| −10% | HALTED (engine); watchdog independently flattens + latches at −10% |
| −11% | flattener flattens + latches |
| Recovery mode (§4.12) | thresholds {engine 11.5% / watchdog 12.5% / flattener 13%} from a signed mode row |

Worked cases (E0 = 100%; budget binds before the 100% gross cap for every ETF):

| DD_eff | B | Permitted | Event | Terminal DD |
|---|---|---|---|---|
| 0 | 0.135 | SPY 67% (entry at prior close) | L3 day, AM-pass close at −20% | −13.4% |
| 0 | 0.135 | SPY 67% entered +3% above prior close (s = 0.223) → budget allows 60% | −20% from prior close | −13.4% |
| 0 | 0.135 | QQQ 54% | −25% | −13.5% |
| 0 | 0.135 | 3 in-play names at 4.5% | all three −90% | −12.2% |
| 0 | 0.135 | 2 large caps at 5% + SPY 47% | both large caps −100%, SPY −20% | −10% − 9.4% → **−19.4% (named residual)** — requires two ≥ $50B names going to zero in one session |
| −5% | 0.085 | SPY 42% | −20% | −13.4% |
| −8% | 0.055 | 1 SPY 27% | −20% | −13.4% |
| −8.9% | 0.046 | 1 SPY 23% | −20% | −13.5% |

Hard caps (defense in depth, on E0): gross notional incl. open entries ≤ 100%; **one
position or open order per symbol**; ≤ 3 concurrent positions **including open entry
orders**; per-trade stop-distance risk ≤ `r_current`, 0.25% for a strategy in micro-live
(per strategy); daily loss −2% of E0 → flatten, no entries until next session; weekly −4%
of Monday's E0 → HALTED (owner re-enable); per-order notional ≤ the symbol's budget cap
`B / s_i` (the budget, the 100% gross cap, and the 5%/10% single-name caps bound notional;
there is no separate dollar cap); entry limit within 1% of last; ≤ 20 orders/day/strategy, ≤ 60/day, ≤ 5/min; integer qty ≥ 1
with the rounded qty re-checked; per-strategy stop-distance floor enforced by the gate;
universe exclusions (event today or before next open, LULD pause today, ex-date/split
today, not `tradable && active && us_equity`, price < $5, insufficient volume).

**Named residuals:** (1) L3 day followed by an adverse reopen beyond +2% (the reserve
absorbs 1.3 pts of a 2% adverse reopen at 67%); (2) a broker outage coinciding with (1);
(3) two large-cap total losses in one session (table row 5); (4) an in-play name frozen for
weeks (loss is priced by s = 1.0, time is not). `P(terminal halt at −10%)` per year is
published from the Monte Carlo (§5.6) so the owner knows the expected system lifetime.

### 4.2 Orders (Alpaca-specific)

- Entry = **DAY bracket** (limit entry ≤ 1% from last; sell-stop market leg; limit
  take-profit). TIF applies to all legs. Positions still open after the close (halted
  names) get **one standalone GTC stop-market** placed by the flattener at 16:00:30 via
  cancel-then-submit (not by waiting for `expired`). Sell stops are not converted to
  stop-limit; buy stops are (relevant only to Phase 6 shorting).
- **Every sell path is cancel-then-submit** for stop/limit legs. **A resting market sell is
  never cancelled by any actor; on 403 held-qty, list the symbol's sells and adopt a resting
  market sell.** This removes the inter-actor priority rule for exits.
- Prices rounded to $0.01 (stops away from entry); qty integer; `rejected` → SAFE, except
  403-held-qty (adopt the resting sell).
- `client_order_id = <actor>-<hash8>-<symbol>-<date>-<seq>` for strategy orders;
  backstop sells `FLAT-<actor>-<symbol>-<date>-<seq>`; AM-pass sells
  `AM-<actor>-<symbol>-<date>-<seq>`. After a submit timeout, query
  by client order id before retrying; boot rebuilds from orders since session open
  (paginated).
- **Halt detection per tape** (`statuses` stream): `halted := (tape == "C" and sc in
  {"H","P","Q"}) or (tape in {"A","B"} and sc == "2")`; resumed on `T` (C) / `3` (A, B).
  SPY `statuses` always subscribed. Whether `statuses` is delivered on the IEX feed is
  **unverified** (0.6); fallback: no prints on a held symbol for 60 s while SPY prints →
  treat as halted.
- **Market-wide breaker detector:** from SPY last trade vs prior close (−7/−13/−20%) and
  from UTP/CTA reason codes where present.

### 4.3 Watchdog (host A)

- Reads the engine heartbeat file (written atomically, tmp + rename, by the engine's 10 s
  REST order-poll loop, carrying `last_reconcile_ts`, `broker_readback_ts`,
  `last_feed_msg_ts`); polls the broker every 15 s; feed liveness via REST
  `latest/trades/SPY` vs `last_feed_msg_ts`.
- Triggers: heartbeat > 30 s or readback age > 90 s with open positions **or orders**
  other than `halted_hold` (this rule wins during a 429 storm); DD ≥ 10%; ≥ 15:57 with
  anything open other than `halted_hold`; engine DB-down > 5 min; `HALT_REQUESTED` present.
- `crashes_today` is reset by the watchdog at the 09:15 go/no-go.
- **Latch-before-touch:** write the latch (file + DB halt row + incident id) *before* the
  first broker call; then flatten (§4.6). Every backstop action is a latching HALTED.
- Maintains `crashes_today` in the latch file + DB; increments on each engine crash.
- Writes its own broker readback to the DB every 15 s; pushes the signed daily HWM to
  host B; consumes re-enable rows (§4.10) — it holds the TOTP secret; dead-man ping;
  lower `oom_score_adj` than the engine.

### 4.4 Off-host flattener (host B; state-independent)

- **09:19** snapshot of positions = overnight carry. **09:20:** for every carried position,
  cancel-then-submit an `opg` market sell over its GTC stop (enters the opening auction).
  **09:30:05–09:30:25:** market-sell fallback for anything not filled. A symbol unfilled
  with unchanged order status by 09:31:25 is `halted_hold` (the flattener has no feed) and
  gets its GTC stop again at 16:00:30. Engine submits nothing for snapshot symbols during
  09:19–09:31:45. AM-pass orders use the prefix `AM-<actor>-` (they are scheduled duties,
  not backstop actions, and do not trigger SAFE-no-submit).
- **15:57:** if readback shows anything open other than `halted_hold` → flatten.
  **16:00:30 (scheduled duty, not a backstop action):** GTC stop for every position still
  open (halted), cancel-then-submit.
- **Every 60 s:** DD ≥ 11% (or 13% in recovery mode) → latch, flatten.
- Serves signed `GET /status` over WireGuard; POSTs status to host A every 60 s; sends
  **ntfy on every action and a daily 15:58 "flat confirmed HH:MM:SS"**; own dead-man;
  `HALT_REQUESTED` from receiver B (own volume). HWM = watchdog-pushed value, fallback
  broker history minus the flow ledger. Firewall (flattener container only): outbound
  Alpaca/ntfy/host A; the halt receiver keeps inbound 443 and ACME egress.

### 4.5 Reconciliation (every 30 s and after every fill event; single order-writer)

1. Fetch positions, open orders, account, configurations, closed orders since last cycle.
2. **Fail-closed arbitration:** if the listing itself fails (429/5xx) → no submit until a
   listing ≤ 10 s old succeeds. If any `FLAT-*` (backstop) order since session open —
   `AM-*` orders do not count — or `suspend_trade == true`, or the latch is set, or **any
   of the engine's own open orders was cancelled without its request** → SAFE-no-submit.
3. Local vs broker mismatch (excluding in-flight own orders) → SAFE + alert; two
   consecutive → flatten with broker truth.
4. **Protection invariant:** every open position has exactly one *protective* exit order
   (sell-stop, or a resting market sell) with `qty == position qty`; a bracket's
   take-profit leg is not counted. Else cancel stop/limit legs → place a stop; if that
   fails within 10 s → close. Not applied to flattener-owned symbols during
   09:19–09:31:45 or to `halted_hold` names that already have their GTC stop.
5. `L ≤ B`; close-largest if violated.
6. Assert multiplier 1, `no_shorting`, `fractional_trading=false`, options level 0, crypto
   not active, `suspend_trade == false` when not HALTED (`suspend_trade == true` with no
   matching audit row = an owner halt → latch, never un-suspend), account id, env,
   `buying_power ≤ cash`, `equity ≥ maintenance_margin`, `pending_transfer_* == 0`.
7. Cash identity (§2.5). 8. Heartbeat write.

### 4.6 Verified flatten (all actors)

```
latch first: write HALTED (file + DB + incident id); flattener/watchdog status = "flattening"
if suspend_trade == true and the 0.6 probe showed it blocks closing sells and the latch
   has a matching audit row (i.e., we set it): PATCH false, audit row   # else leave it
loop until readback shows 0 open orders and 0 positions (or only halted_hold):
    cancel stop/limit orders (never a resting market sell)
    DELETE /v2/positions?cancel_orders=true
    for positions still open after 20 s: per-symbol FLAT-<actor>- market sell (adopt an existing resting sell)
    halted symbol: leave the resting sell; mark halted_hold; page owner
    bounded backoff on 429 (1→2→4→8 s), never abandon; escalate alert every 30 s
report "flat" only from broker readback, with timestamp
suspend_trade = true ONLY after readback 0/0 and no halted_hold exists
```

### 4.7 High-water mark and drawdown ledger

- HWM = max daily closing equity; on an owner withdrawal `W` (permitted only after an
  owner-acked halt): `HWM ← HWM × (E − W) / E` where **`E` = equity at the last cycle
  before `pending_transfer_out` became non-zero** (equivalently `E_after + W`), recorded
  in the flow ledger with the `CSW` id. Deposits are not permitted (HALTED). `INT`/`DIV`
  raise equity legitimately. Unit test: HWM 100k, E 95k, W 30k → DD 5.0%.
- Authoritative stores: latch/HWM file (volume mounted read-write in engine and watchdog;
  **separate** from the halt-receiver volume) and the DB, each with the flow ledger.
  Broker portfolio history minus the ledger is an alert-only cross-check. On start take the
  max of the authoritative stores; an unreadable latch file → HALTED (fail closed).

### 4.8 Market-structure hazards

1. **Single-stock halts:** per-tape detection (§4.2). No new entries in a symbol halted
   today. A halted position keeps its resting sell; after the close it gets one GTC stop;
   it stays `halted_hold` across days with its `N·s` inside `L`; **the go/no-go passes with
   `halted_hold` positions** (the rest of the book keeps trading). Delisted to OTC →
   liquidate via Alpaca support (runbook).
2. **Market-wide breakers:** L1/L2 (−7/−13%, 15-minute halts, not after 15:25): cancel
   entries, keep stops, no new market sells until 60 s after reopen. **L3 (−20%): ends the
   day (also after 15:25)**; all positions → `halted_hold`, AM pass next day. s_SPY = 0.20
   assumes exactly this.
3. **Corporate actions:** `adjustment=all` for features, raw for accounting; announcements
   API lags a day (same-day specials are a residual); ex-date/split today excluded.
4. **Asset master** refreshed each morning.
5. **Opening auction:** flattener uses `opg` (submitted before 09:28); engine never trades
   before 09:32.
6. Settled-cash module for a true cash-account broker only.
7. **Shorting (Phase 6, ETFs only)** only if permitted at multiplier 1 (unverified).

### 4.9 Fault table

| Fault | Detection | Resolution |
|-------|-----------|------------|
| Engine crash/OOM/hung | heartbeat > 30 s or readback age > 90 s | with anything open → watchdog latch + flatten (HALTED); with nothing open → engine reboots to SAFE for the session; `crashes_today ≥ 2` → HALTED |
| Restart after halt | latch OR(file, DB, `suspend_trade`) | refuses; re-enable per §4.10 |
| Watchdog crash | engine polls its heartbeat; dead-man | engine SAFE if stale > 30 s; flattener unaffected |
| Host A dead | dead-man | flattener 15:57 / 11% / AM rules; owner: dashboard liquidate-all then suspend |
| Host B down | engine polls B health every 60 s | SAFE for the session if stale > 3 min |
| DB down | engine health | SAFE; latch/HWM live in the file; flatten if > 5 min; DB down at boot → close all, SAFE |
| Latch file unreadable | boot | HALTED |
| Broker 5xx/429 storm | failed polls | watchdog 30 s rule fires; stops are broker-simulated so `L ≤ B` is the protection; on recovery cancel-all/close-all → HALTED (watchdog latch) |
| Data WS silent | > 15 s no messages | reconnect + REST poll |
| Trade-update drop | REST order poll every 10 s; replay on reconnect | reconciler ≤ 30 s |
| Clock skew | > 2 s vs `/v2/clock` | SAFE |
| Deploy in session | script check | refuses unless `--flatten-first` |
| Secrets leak / unknown-cause halt | — | coordinated rotation runbook |
| Partial fill / orphan leg | protection invariant | stop placed or closed |
| Order stuck `pending_cancel` | flatten loop | wait, then FLAT- market sell |
| 403 held-qty | adapter | adopt resting market sell; cancel only stop/limit legs |
| Paper/live mix-up | id + env each cycle | refuse / halt |
| `L > B`, nothing closable | budget | SAFE + alert |
| Cash residual | identity | SAFE, freeze E0/HWM; HALTED if unexplained after 2 cycles |
| Instant ACH / pending transfer | `pending_transfer_*` | SAFE + alert |
| Notification dead | 09:25 alive incl. cert-expiry check | missing = alarm |
| Spurious halt (token replay) | idempotent | harmless; invalid-token IPs banned, valid tokens always accepted |

### 4.10 State machine and the single halt semantic

```
BOOT → RECOVERING (rebuild from broker; HWM from file/DB; assert config/id/env;
        latch set or unreadable → HALTED; DB down → close all → SAFE)
     → SAFE (exits only)
     → ARMED   only at the 09:15 go/no-go
     → RUNNING only at 09:31:45 when broker positions == carry-only (halted_hold) and
                flattener status ts ≥ 09:30:25; else SAFE for the day
FLATTENING → SAFE (engine 15:55 sweep) or → HALTED (−10%)
HALTED (latching): −10%, any backstop action, config mismatch, unexplained flow,
        weekly −4%, owner halt, crashes_today ≥ 2, latch unreadable
```

**Writers and clearers.** `HALT_REQUESTED` (receiver volume): written by the receiver;
consumer renames it to `HALT_REQUESTED.<ts>.consumed` in the same step that writes the
latch. Latch file + DB halt row: written by engine or watchdog; **cleared only by the
watchdog** when it consumes a re-enable row `{incident_id, totp, ts, nonce}` — it verifies
the TOTP with its own secret, rejects rows older than 10 min or naming a non-current
incident, marks the row consumed, clears the file, sets the DB row's `cleared_at`, and
PATCHes `suspend_trade=false` in one step. DB HALTED := latest halt row has no
`cleared_at`. The engine then boots to SAFE, becomes ARMED at the next 09:15 go/no-go, and
RUNNING at 09:31:45.

### 4.11 Go/no-go

**09:15 (→ ARMED):** clock skew · calendar incl. early close · asset master · event
exclusions · overnight positions are only `halted_hold` with one GTC stop each · cash
continuity (§2.5.3) · activities pass clean · reconciliation clean · watchdog + flattener
heartbeats fresh · HWM file and DB within $1 · all config asserts · `pending_transfer_* ==
0` · no latch · `crashes_today == 0` · notification channel self-test (the 09:25 alive
message with the cert-expiry check is the external alarm, §4.9).
**09:31:45 (→ RUNNING):** broker positions == carry-only; flattener status ts ≥ 09:30:25.

### 4.12 After a −10% halt

(a) Default: **terminal** (owner review). (b) Recovery mode: a TOTP-signed, expiring,
one-way `mode=recovery` row consumed by **both** watchdog and flattener and read by the
engine from the DB selects the fixed threshold table {engine 11.5 / watchdog 12.5 /
flattener 13}. In recovery mode the −5/−8/−9 ladder rows are superseded by: multiplier
0.25; max 1 position; **no new entries at DD_eff ≥ 11.0%** (0.5-pt SAFE gap below the
engine's 11.5% halt); HWM untouched. At −11.0%: B = 0.025 → SPY ≤ 12.5% → −2.5% → DD
−13.5%. Chaos-tested before it is ever used.

---

## 5. Strategy layer

### 5.1 Principles

1. Pure function `(bars, features, account_state) → Intents`; no I/O.
2. Identity `(code_hash, config_hash)` computed by the engine from mounted source; any
   change = new strategy at Idea; gate/promotion rows append-only, git-committed.
3. Portfolio of small, uncorrelated, validated edges.
4. No discretion, no news, no latency games.

### 5.2 Candidates

| ID | Track | Strategy | Evidence | Weakness |
|----|-------|----------|----------|----------|
| S3-ETF | A | VWAP mean-reversion on SPY/QQQ after 10:00; fade > 2σ with volume exhaustion; target VWAP; stop = max(1×ATR(5m), **0.4%**); trend-day filter | execution literature | r_eff limited by the 0.4% floor × 67% cap |
| S2 | A | Intraday momentum with noise band (Zarattini, Barbon & Aziz 2024); trailing stop at band; exit at close | Sharpe ~1.3–2.4 in paper | paper uses leverage; costs; regime |
| S1/S4 | B | ORB stocks-in-play / gaps | Zarattini & Aziz | **not economically viable under s = 1.0 (§6.1)** |
| S5 | — | cash | 0% DD | default |

Order: S3-ETF → S2. Long-only.

### 5.3 Research protocol (pre-registered)

1. **Data:** SIP minute bars ≥ 7 years (from 2016); quotes fetched per fill window (§2.3);
   `adjustment=all` for features, raw for accounting.
2. **Fill rules:** signal at bar t executes ≥ bar t+1 open; limit entries fill on
   trade-through; stops at `min(stop, next open)` minus stop slippage; halts at reopen;
   targets on trade-through; partial fills per capacity.
3. **Costs** per §2.3 keyed by date; **all G1 statistics on the 2× stress run.**
4. **Parameters:** ≤ 5; pre-registered grid; **in-fold selection rule: maximize in-fold
   Sharpe subject to ≥ 0.75 trades/day and ≥ 100 in-fold trades**; per-fold surfaces
   reported.
5. **Walk-forward:** anchored expanding window, initial train 12 months, 3-month steps.
6. **Holdout:** most recent 12 months, evaluated **once per (track, holdout window)** —
   any strategy on the track's instrument set burns it. **Pass criterion:** holdout Sharpe
   ≥ 0.5 × OOS Sharpe and holdout MDD ≤ MC 95% MDD.
7. **Trial registry / DSR (daily units):** N = registered walk-forward runs **across every
   family on the track**; in-fold grid points do not count; abandoned runs do; synthetic
   runs flagged and excluded. `SR_d = SR_ann/√252`; `V = max(sample variance of the runs'
   daily OOS Sharpes, (0.5/√252)²)` **for all N**; `SR₀ = √V·[(1−γ)Φ⁻¹(1−1/N) +
   γΦ⁻¹(1−1/(N·e))]`, γ = 0.5772; `DSR = Φ[(SR_d − SR₀)·√(T−1) / √(1 − γ₃·SR_d +
   (γ₄−1)·SR_d²/4)]` with γ₃, γ₄ from OOS daily returns and T = OOS days. Implementation
   cross-checked against a reference test vector.
8. **Sharpe:** daily returns at `r_eff`, annualized, with standard error.
9. **Regime:** ≥ 60% of OOS calendar years positive; no year > 50% of the sum of positive
   years; ≥ 2 of 3 VIX terciles positive.
10. **Monte Carlo (one definition):** stationary block bootstrap of OOS daily PnL (block
    5–10 days), 10,000 paths, 252-day horizon, at `r_eff`, ladder simulated; **95% MDD
    ≤ 8%**; also reports `P(DD ≥ 10% within a year)`.
11. **Capacity:** ≤ 1% of 20-day median 1-minute volume.
12. **Fixed-cost hurdle:** after-tax expected annual PnL at the intended equity ≥ 2 ×
    fixed costs.
13. **Trade-rate floor:** ≥ 0.75 trades/day.
14. **Synthetic calibration:** 1,000 noise strategies run through the **same in-fold
    optimization and grid size** → ≤ 0.5% pass G1.

### 5.4 Gates (units: R = stop-distance risk of the trade; band = trade-block bootstrap of OOS per-trade R (block = one trading day's trades), 10,000 paths, pointwise envelope scaled until 90% of paths lie entirely inside for n ∈ [10, 100] trades; MDD-in-R = MC 95% MDD ÷ r_eff)

| Gate | Requirements |
|------|--------------|
| G1 Idea → Backtested | §5.3 complete; DSR ≥ 0.95; `r*` ≥ 0.2% (else the strategy cannot pay its way); MC 95% MDD ≤ 8% at `r_eff`; ≥ 0.75 trades/day; regime rule; holdout pass; fixed-cost hurdle (the operative economic gate) |
| G2 Backtested → Paper-done | same feed as live; ≥ 40 trading days, ≥ 30 trades — **a plumbing gate: at Sharpe 1–2 the t-statistic at 30 trades is only 0.4–0.8**; cumulative R inside the band; counterfactual slippage (paper fills re-priced on historical SIP NBBO) ≤ modeled; modeled fees subtracted regardless; per-minute signal-state agreement 40-day mean ≥ 95%, no day < 90%; reconciliation clean |
| G3 Paper-done → Micro-live | Phase-1 tests green on the commit; chaos suite ≤ 30 days old; live 1-share close-all drills by watchdog and flattener; $10 live withdrawal drill (§4.7 path); HWM seeded; config asserted; owner TOTP. **Allocation binds:** `max(1 share, 10% of the strategy's notional cap)`; 0.25% risk is a ceiling |
| G4 Micro-live → Full | ≥ 40 days, ≥ 30 live trades (plumbing); realized slippage ≤ 1.5× modeled; cumulative R inside the band; live MDD-in-R ≤ MC 95%; **ramp 10→25→50→100% is contingent on the MDD-in-R trigger not firing** (the band has little power); 20 clean days per step (clean = no trigger, no incident, reconciliation clean) |
| Portfolio gate | before a 2nd strategy: day-block portfolio MC 95% MDD ≤ 8%; 60-day correlation < 0.6 |
| Demotion | cumulative R below the demotion band (OOS mean shrunk 50%) at n ≥ 10, **or live MDD-in-R > MC 95% (the trigger with power)**, or slippage > 1.5× over 30 trades. Flattens the strategy; allocation 0; fresh window to re-promote; two demotions in 6 months → Idea |

### 5.5 Allocation across strategies — deferred until two strategies reach G4 (¼-Kelly, correlation guard, weekly ±10 pp).

### 5.6 Risk per trade

`r* = max r ≤ 1.0% : MC(§5.3.10) 95% MDD ≤ 8%`, monthly; `r_eff = min(r_current,
stop_floor × notional cap)` — for S3-ETF on SPY: 0.4% × 67% = **0.27%**; on QQQ 0.4% × 54%
= 0.22%. Published as `r*(Sharpe, trades/day)` with `P(terminal halt)/yr` (indicatively 1–3%).

---

## 6. Economics

### 6.1 Expected returns, minimum capital, shutdown

`E[gross] ≈ Sharpe × σ_annual`, `σ_annual = r_eff × σ_R × √(trades/yr)` = 0.22–0.27% × 1 ×
√189 ≈ **3.0–3.7%**. Sharpe 1–2 → **gross 3–7%/yr**, before the ladder haircut (multiplier
halves below −5% DD, historically 10–25% of days). Tax is **federal only** (Texas resident:
no state or local income tax) at the assumed 24% marginal rate on positive net only; fixed
costs non-deductible; cells the fixed-cost hurdle excludes are marked ✗ (a strategy
producing them fails G1, so they cannot occur live).

| Equity | Gross 3% | Gross 7% | Tax (24% federal) | Fixed | Net @3% | Net @7% |
|--------|----------|----------|-------------------|-------|---------|---------|
| $10,000 | $300 ✗ | $700 | $72–168 | $180 | $48 ✗ | $352 (3.5%) |
| $15,000 | $450 ✗ | $1,050 | $108–252 | $180 | $162 ✗ | $618 (4.1%) |
| $25,000 | $750 | $1,750 | $180–420 | $180 | $390 (1.6%) | $1,150 (4.6%) |
| $50,000 | $1,500 | $3,500 | $360–840 | $180 | $960 (1.9%) | $2,480 (5.0%) |
| $100,000 | $3,000 | $7,000 | $720–1,680 | $180 | $2,100 (2.1%) | $5,140 (5.1%) |

Hurdle (after-tax ≥ 2 × $180 = $360 → gross ≥ $474 at 24%): at Sharpe 1 (3% gross) that
needs ≈ $16k, at Sharpe 1.5 ≈ $9.5k. **Minimum capital: $15,000** (policy: the hurdle at
Sharpe ~1.2). If the owner's federal bracket is 32% or higher, the hurdle moves to gross
≥ $530 and the table's net column drops by about a tenth; the minimum stays $15,000. **Track B**: at s = 1.0 total in-play notional ≤ 13.5% (split over two positions,
≈ 6.75% each) and S1 stops of 1–2% give ≈ 0.07–0.14% risk/trade → ≈ $700–1,400 gross on $70k against a $1,370 SIP + hosting
hurdle of $2,740 after tax. Not viable; deprioritized.

**Year one is negative** by ≈ $180 regardless of edge (ramp takes 11–13 months).
**Shutdown rule:** after 12 months at 100% allocation, if after-tax net trading PnL < 2 ×
fixed costs for those 12 months, stop and tell the owner (same threshold and tax basis as
the hurdle).

### 6.2 Compounding rules — all limits on E0; HWM ratchets on closes; leverage never;
shorting Phase 6 only if permitted at multiplier 1; `r*` monthly.

### 6.3 Tax and journal

- FIFO lots with wash-sale matching over the **61-day window (30 days before and after)**
  across all strategies; the export reconciles **to** the broker's realized-gain file /
  1099-B (retail machine-readable export **unverified**); December losses defer unless the
  symbol is not re-bought for 31 days (accepted). **A substantially identical position in
  any other account, IRA included, converts deferral into permanent disallowance (Rev. Rul.
  2008-5)** — hence the owner rule in §2.1.
- TTS/475(f) unlikely at ~190 trades/yr; $3,000/yr loss deduction with indefinite
  carryforward; election deadline April 15 (D6 with an advisor); quarterly federal
  estimates. **The owner is a Texas resident (San Antonio): no state or local income tax,
  no state capital-gains tax, and no state return; the weekly report's after-tax estimate
  uses the federal rate only.**

---

## 7. Web app

**Exposure:** dashboard over WireGuard only. Public: `POST /halt` on halt-receiver A and B
(separate no-key containers; own volume, write-only for the receiver, read-write for the
consumer, which renames consumed files). Token ≥ 32 random bytes, constant-time compare, per host, rotatable via env;
**valid tokens are accepted regardless of ban state**; invalid-token IPs banned (keyed
IP + token prefix). Response `202 {incident_id, consumer_heartbeat_age_s}` and the
receiver sends its own ntfy ("received by A; watchdog last alive N s ago"); the phone
Shortcut POSTs to A **and** B. **Runbook: no "confirmed flat" within 90 s → Alpaca
dashboard liquidate-all, then suspend trading.** TLS via Let's Encrypt with expiry in the
09:25 check; both receivers self-test daily; monthly phone exercise in paper. TOTP on login
and on re-enable; 12-hour sessions; lockout; CSRF.

**Pages:** Overview (PAPER/LIVE + account id; state; engine readback vs watchdog readback
with ages; flattener status age; equity, HWM + sources; DD gauge 5/8/9/10/11/11.5/12.5/13/15; `L/B`;
feed health; `suspend_trade`; markers; request budget and last 429; last rejection;
`pending_transfer_*`; halt-token last IP; HALT), Positions & Orders (state incl.
`halted_hold`; close-now via watchdog), Strategies (hash-bound; gate state; cumulative R vs
band; MDD-in-R; slippage; agreement; history), Research, Journal/Audit (incl. lot/wash-sale
ledger), Settings (read-only limits; re-enable with TOTP → row for the watchdog).

Notifications: halt, SAFE, gate change, backstop action (from the acting host), mismatch,
flow event, 09:25 alive, 15:58 flat confirmed, 16:05 summary, missed dead-man.

---

## 8. Operations

Host A: `strategies`, `engine`, `watchdog`, `halt-receiver`, `api`, `db`. Host B:
`flattener`, `halt-receiver`. Broker clock reference; chrony. Morning routine + two-stage
go/no-go. Deploy guard. Nightly backups; restore and key-rotation drills in Phase 4.
Weekly report incl. after-tax estimate, wash-sale adjustments, `P(terminal halt)`.
Runbooks: broker outage, data outage, crash with open positions, halted symbol incl.
delisting via support, mismatched fill, rotation, re-enable, recovery mode, **first real
halt → verify the `halted_hold` lifecycle**, Alpaca dashboard liquidate-all then suspend.

---

## 9. Testing

- **Fake broker:** partial fills, 403 held-qty, 403 buying-power, 429 storms, latency,
  `pending_cancel` stalls, per-tape `statuses` fixtures incl. MWCB, gap opens, **multi-day
  halted-hold lifecycle (DAY legs expire → GTC stop → AM pass → repeat)**, activities with
  cash-first/activity-later lag, `pending_transfer_*`, `suspend_trade` semantics, bracket
  TIF, `opg` handling. Contract suite passes against fake and paper.
- **Unit:** every §4.1 rule incl. entry-relative `s_i`, close-largest, ladder; ticks/qty;
  ids; HWM formula and timing; cash identity; allow-list; calendar; MWCB; Intent schema;
  hash binding; live-id refusal of fixtures/overrides; DSR test vector.
- **Property (Hypothesis, 1,000 cases in CI, 10,000 nightly):** random
  fill/price/halt/flow sequences through gate + reconciler + fake broker never produce
  DD > 10% without HALTED and never leave `L > B` unresolved after one cycle.
- **Replay:** 2020-03-16, 2024-08-05, a T1-halt day, and a **synthetic L3 day with QQQ
  −25% and a sector −35%**, with the final s-table.
- **Chaos (paper, session hours):** engine paused → watchdog latch + flat ≤ 60 s;
  watchdog paused → engine SAFE + dead-man; both paused → flattener by 15:58; three actors
  flatten simultaneously → one clean flat, zero 403-induced SAFE; halt + restart with
  `_test_always_buy` → 0 orders and ≥ 5 Intents rejected `HALTED`; re-enable without a
  valid row → still HALTED, with it → SAFE and `suspend_trade == false`; re-enable replay
  after watchdog restart → rejected; clock skew → SAFE; trade-update drop → replayed;
  429 on listing → no submit; crash counter → HALTED at 2; deploy guard; recovery-mode row.
- **Malicious strategy** (§3); **synthetic calibration** (§5.3.14).

---

## 10. Roadmap (assumes **≥ 35 h/week**; one session-hour test attempt per day)

Calendar: Phase 0 ≈ 2 weeks; Phase 1 ≈ **13–16 weeks**; Phase 2 ≈ 4; strategy 2–4 each;
paper 40 trading days; micro-live 40; ramp 60 → first full allocation ≈ **11–13 months**.

### Phase 0
- 0.1 `docs/DECISIONS.md`: each of D1–D7 has a value or an accepted default and the
  owner's signature line. D8 (written acceptance of the §6.1 economics) is signed before
  Phase 5, after the ladder haircut is quantified from the MC (§11, §13.4).
- 0.2 Alpaca account, paper keys, two-key-pair test → recorded.
- 0.3 Paper config PATCH; record exactly which fields are accepted.
- 0.4 Notification channel. 0.4a **Halt receivers A/B** (TLS, token, file write, own
  ntfy). *Accept:* phone POST → `202` with heartbeat age + receiver ntfy.
- 0.5 Host B, dead-man, WireGuard. *Accept:* missed ping alerts; dashboard port closed
  from outside.
- 0.6 **Broker semantics probe → `docs/BROKER_FACTS.md`**: each fact with captured
  request/response, date, and the plan lines depending on it: `suspend_trade` vs closing
  sells / liquidate-all; bracket TIF; child-leg qty on partials; 403 held-qty; WebSocket
  limit; **`statuses` on IEX**; orders on halted symbols; shorting at multiplier 1; **paper
  fee debits and fee/cash field semantics**; paper `suspend_trade`; portfolio-history flow
  fields; activity codes; **`buying_power` vs `cash` under the June-2026 framework**;
  **paper day-trade behavior after 2026-07-06**; `opg` acceptance window. Items needing a
  real halt are marked opportunistic.

### Phase 1
- 1.1 Scaffold, Compose (two networks, hardened strategy container, socket volume),
  Postgres, CI. 1.2 Adapter + Alpaca paper impl **with the rate limiter and 5 s snapshot
  cache**. 1.2b Fake broker (§9). 1.3 Flatten + arbitration + latch-before-touch (fake
  broker: three concurrent actors, `pending_cancel`, 403, resting market sell adopted,
  `suspend_trade` set only after 0/0). 1.4 Risk gate (Σ budget with `s_i`, close-largest,
  caps, rounding, floors, snapshot age, exclusions, Intent schema, hash binding). 1.5 HWM
  ledger + cash identity + transfers + allow-list (fake broker: `CSD`/`JNLC`/`ACATC` →
  HALTED; fill-race residual → SAFE then clears; instant-ACH → SAFE; withdrawal timing
  test). 1.6 Reconciler (single writer, protection invariant, asserts, fail-closed
  arbitration; paper: cancel a stop leg → replaced ≤ 30 s; `no_shorting=false` → HALTED →
  re-enable path). 1.6b **Property + replay suite** (§9). 1.7 State machine, single halt
  semantic, crash counter, two-stage go/no-go, fixtures (paper-only). 1.8 Watchdog
  (heartbeat file, DD, 15:57, receiver file, readback → DB, re-enable consumer with TOTP
  secret, dead-man, HWM push). 1.9 Isolation + malicious strategy test. 1.10 Flattener
  (09:19/09:20 `opg`/09:30:05/15:57/16:00:30/11%; ntfy; signed status; override refused on
  live id). 1.11 Overview page + re-enable only (other pages Phase 4). 1.12 Deploy guard,
  runbooks, one-command chaos suite. *Accept:* every §9 chaos test passes in paper.

### Phase 2 — loader (≥ 7 years, quotes per fill window), backtester (fill rules, dated
fees), walk-forward with named selection rule, holdout lock per track, registry, DSR
(test vector), MC, `r*` table, research page. *Accept:* toy PnL to the cent; synthetic
≤ 0.5%; unregistered run refused; DSR vector matches.

### Phase 3 — S3-ETF then S2, each ending in a G1 record (FAIL is valid).

### Phase 4 — paper: **re-provision** (reset creates a new paper account: new keys on A and
B, new id, HWM seed); 40 days; monthly chaos; restore and rotation drills; remaining
dashboard pages.

### Phase 5 — micro-live: G3 checklist incl. the $10 withdrawal drill; 40 days.

### Phase 6 — ramp on the MDD-in-R trigger; second strategy after the portfolio gate; ETF
shorting only if permitted at multiplier 1.

---

## 11. Decisions for the owner

| ID | Decision | Default |
|----|----------|---------|
| D1 | Starting capital | ≥ $15,000; below that do not go live |
| D2 | SIP subscription | No (Track B deprioritized) |
| D3 | Notifications | ntfy + email |
| D4 | Hosting | A: US-East VPS; B: different provider |
| D5 | Shorting | ETFs only, Phase 6, only if allowed at multiplier 1 |
| D6 | Federal marginal tax rate (Texas: no state/local income tax); 475(f) | 24% federal until the owner states their bracket; no election (advisor) |
| D7 | Point-in-time universe (Track B) | moot while Track B is deprioritized |
| D8 | **Written acceptance of §0/§6.1 economics (3–7% gross, negative year one)** | required before Phase 5 |

---

## 12. Sources consulted (2026-09-02)

Gauntlet Loop (trilwu, NicholasSpisak repos) · Robinhood API status (sanko/Robinhood,
apidog) · PDT retirement (SEC order SR-FINRA-2025-017; FINRA Notice 26-10; Alpaca changelogs
2026-06-03 / 2026-07-06) · Alpaca: cash-account and unsettled-funds support pages;
configurations reference; orders doc (buy-stop conversion; halts); order-types article
(bracket TIF); 403 held-qty forum thread + Alpaca-API #282; rate-limit support page;
paper-trading doc (reset = new account); activities + enums; instant ACH; high-yield cash;
regulatory-fees page; portfolio history v2; realtime schema (`statuses` per tape);
corporate-actions announcements; alpaca-py models · Nasdaq MWCB FAQ · FINRA Section 31
notice 2026-03-17; FINRA TAF schedule incl. 2027 rate; CAT fee alerts · SIFMA Rule 612
extension · Rev. Rul. 2008-5; TTS/475(f) guides · Jordan & Diltz 2003; Chague et al. ·
Zarattini & Aziz; Zarattini, Barbon & Aziz 2024; giovannibrusco replication · Bailey &
López de Prado 2014.

---

## 13. Known gaps after Gauntlet round 3 (documented, not hidden)

1. **Unverifiable until Phase 0.6:** `suspend_trade` vs closing sells and dashboard
   liquidate-all; `statuses` delivery on IEX; `buying_power == cash` post-June-2026; fee
   accrual field semantics (the cash identity's ±$1 band depends on it); paper day-trade
   behavior after 2026-07-06; `opg` routing into reopening auctions; UTP/CTA MWCB reason codes;
   Alpaca retail realized-gain export; two key pairs.
2. **Testable only by a real event:** the `halted_hold` lifecycle on a real halt; the AM
   `opg` sell into a thin reopen (unmodeled beyond `s`).
3. **Named residuals** in §4.1 (post-L3 adverse reopen; broker outage coinciding; two
   large-cap total losses; weeks-long freezes).
4. **Economics:** 3–7% gross is the plan's own estimate at gate-implied risk; the ladder
   haircut is stated qualitatively (10–25% of days) and must be quantified from the MC
   before D8 is signed.
5. **Strategy candidates:** S3-ETF and S2 have not been backtested under this cost model;
   both may fail G1, leaving S5 (cash).
6. **Single developer:** the calendar is a floor; anything cut from Phase 1 must not touch
   the invariant (candidates: dashboard pages, drills, Hypothesis case counts).
