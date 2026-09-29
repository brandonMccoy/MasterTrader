# Token plan — critique loop log

Process: plan → harsh critique → research → re-plan, until a round produced no finding
that changed a mechanism. Three passes; stopped when the last critic's findings were
arithmetic, ranking and wording only. (A fourth pass would itself cost more than it could
save on a plan this size.)

## Research inputs
- Official Claude Code docs (via the claude-code-guide agent): prompt caching is automatic;
  main-thread cache TTL 1 h on subscription, 5 min for subagents and compaction
  (`promptCacheTtl`, `subagentPromptCacheTtl`); invalidators are system-prompt changes
  (model, effort, MCP connect/disconnect, plugin toggles), `/compact`, and resume after
  TTL expiry. CLAUDE.md loads once per session, recommended < 200 lines; `.claude/rules/`
  with `paths:` loads on demand. Subagents get a fresh prompt plus CLAUDE.md unless
  `omitClaudeMd: true`; `model:` per agent or `CLAUDE_CODE_SUBAGENT_MODEL`; results return
  as a summary only. MCP schemas are deferred by default (tool search). Skills load
  descriptions only. PostToolUse hooks can return `updatedToolOutput`. `/effort
  low|medium|high|xhigh|max`; thinking is billed as output; `/usage` shows token buckets
  (there is no `/cost`). Auto-memory loads the first 200 lines / 25 KB.
- Pricing from the bundled claude-api skill: Fable 5.1 $10/$50, cache read $0.25;
  Sonnet 5.5 $2/$10, read $0.20; Haiku 4.5 $1/$5; cache write ≈ 1.25× (5 min) / 2× (1 h).
- Public write-ups (LOW/CODE, StationX, StackNotice, Menetray, GitHub issue
  anthropics/claude-code#44536): consistent on `/clear` between tasks, Sonnet for
  subagents, and MCP schema bloat; the issue measured a 130–150k startup overhead on
  heavy setups. Two articles were egress-blocked and not used.
- This repo's own session transcript, parsed and deduplicated: the numbers in
  `TOKEN_PLAN.md` §1.

## Pass 1 — v1 (self-critique)
- Ranked cold resumes first; the data put subagent cache writes higher. Re-ranked.
- Claimed MCP reconnects broke the cache; every large rewrite in the transcript coincided
  with a resume after hours, none with an MCP event. Claim dropped.
- Put CLAUDE.md size at #5; it is ~600 tokens of a 65k cached prefix. Demoted to hygiene.
- Missing: agents returning long reports into the parent; effort facts; TTL facts. Added.

## Pass 2 — v2 → blind critic (Sonnet, read-only, ≤ 350 words)
Findings accepted:
- Share column summed to 95% and used the wrong denominator; total row lacked tokens.
  Fixed, and the main-thread write price corrected to the 1-hour rate.
- "Rewrites were 51% of output" holds only for the main thread; 40% overall. Both stated.
- "Report to file" was ranked #2 on a false premise (a cached prefix is read, not
  rewritten); its direct saving is ≈ $1. Folded into item 1 as a quality-and-hygiene rule.
- "Fewer critic rounds" had the second-largest ceiling (~$15) and was ranked #5. Now #2.
- Items 1 and 2 overlap; stated. Items 6 and 7 share one $3.8 bucket; stated.
- Sonnet "÷5" was asserted without prices; prices now given.
- Missing levers: startup-prefix trim per agent (≈ $0.8 × 11 agents), deterministic checks
  before agent critique, and a context ceiling independent of pauses. All three added
  (items 1, 2, 3, 9).
- Quality guards added: top model for the final gate; read the full critique file before
  acting on BLOCKING items; `/compact` with a keep-list; rewrite allowed above 30% change;
  `tail`/grep instead of `head`; output contract exempts verification and uncertainty.
- Wording made implementable: exact model/tool/omitClaudeMd rules; "55 minutes / 100k";
  checklist ≤ 12 items and a BLOCKING definition; "30 tool calls and 15 files" instead of
  an unenforceable token stop; "fewer than 3 files" instead of "small tasks".
Findings rejected:
- Critic suggested cache reads might be priced at $1 (10% of input). The skill's price
  table lists $0.25 for Fable 5.1; kept.

## Pass 3 — v3 (final)
Re-ranked by the corrected table. No mechanism changed after pass 2's fixes; stopped.

## Pass 4 — source review (requested by the owner)
Sources read directly: Anthropic engineering "Effective context engineering for AI
agents"; Claude Code docs "Manage costs effectively", "Best practices", "Explore the
context window"; rtk-ai/rtk (39.5k stars); drona23/claude-token-efficient (6.1k);
alexgreensh/token-optimizer (2.4k); egorfedorov/claude-context-optimizer (112); the
yurukusa CLAUDE.md cheat-sheet gist; GitHub issue anthropics/claude-code#44536.
Two blog write-ups on "19 changes" and "8 tactics" were egress-blocked and not used.
- Ranking unchanged: every source points the same way on items 1–5 and none supplies a
  number that would promote a lower item for this repo's measured buckets.
- Mechanisms added: resume-from-summary, `/btw`, partial summarize via `/rewind`,
  CLAUDE.md compact instructions, `promptCacheTtl: "1h"` when on usage credits (item 3);
  official PreToolUse test-filter hook and RTK as the Bash-output drop-in, structure maps
  and delta re-reads as habits (item 5); prefer CLI over MCP, CLAUDE.md → skills,
  `/doctor`, code-intelligence plugins, prompt suggestions off (item 9); `/context`,
  `/usage` cache-miss line with likely cause, `/insights` (item 10); 1–2k-token subagent
  summary norm and the ~7× agent-teams warning (item 1); reviewer-gap caveat (item 2).
- Evidence weighed, not just cited: drona23's own benchmark shows 4–12% output reduction
  and a net loss at low output volume, so the plan keeps a six-line contract instead of
  importing the file; the cheat-sheet gist has no methodology and is marked corroboration.
- New fact that reframed item 9: the docs' simulation puts a local startup at ~7.9k
  tokens; this cloud session's 65k prefix is the web harness, tool schemas and skill
  listings, of which the repo controls under 3k.

## Residual uncertainty
- Subagent output tokens are under-logged in the transcript; the subagent bucket is a floor.
- Whether `tools:` in agent frontmatter shrinks the agent's cached prefix as much as
  assumed is inferred from the docs' "fresh isolated prompt" statement, not measured.
- Savings percentages are for this session's shape (research-heavy, critique loops); a
  code-heavy session will shift weight toward items 4, 5 and 8.
