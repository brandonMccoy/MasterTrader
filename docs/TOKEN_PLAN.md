# Token-Spend Plan for Claude Code in this repo

Status: v4 (v3 plus a source review against Anthropic news, the Claude Code docs, and
the most-starred GitHub token-optimization repos; see §5). Loop history:
`docs/TOKEN_LOG.md`. Nothing here is implemented; it is the plan.
Date: 2026-09-29

## 1. What the money actually went to (measured, not guessed)

Source: this repo's one Claude Code session transcript, deduplicated by API message id.
Prices: Fable 5.1 input $10, output $50, cache read $0.25 per MTok; cache write = input × 2
on the main thread (1-hour TTL) and × 1.25 for subagents (5-minute TTL). Subagent output is
under-logged in the transcript, so its row is a floor.

| Bucket | Tokens | ≈ $ | Share |
|---|---|---|---|
| Subagent cache writes (11 agents, all on the parent model) | 1.83M | 22.9 | 37% |
| Main thread: 3 cold resumes rewriting a ~280k prefix | 0.84M | 16.8 | 27% |
| Main thread: normal per-turn appends | 0.34M | 6.8 | 11% |
| Cache reads, main + subagents | 18.1M | 4.5 | 7% |
| Output: 3 whole-file rewrites of the plan | 78k | 3.9 | 6% |
| Output: everything else on the main thread (thinking, edits, messages) | 75k | 3.8 | 6% |
| Subagent output (floor) | 41k | 2.1 | 3% |
| Uncached input | 29k | 0.3 | <1% |
| **Total** | **21.2M** | **≈ 61** | **100%** |

Other measured facts that shaped the ranking:
- Startup prefix (system prompt, tool schemas, skills list, CLAUDE.md) was 65k tokens. It is
  cached and cheap to read, but it is rewritten on every cold start and every new agent.
- 60 API calls on the main thread; context grew from 65k to 330k. Each turn's cost is
  dominated by what it appends, not by what it re-reads.
- Whole-file rewrites were 51% of main-thread output (40% including subagent output).
- 12 of 20 WebFetch calls failed on egress-blocked domains: 12 wasted turns.
- CLAUDE.md is ~600 tokens; it is not a cost lever. Shares are of the $61 total.
- The docs' own simulation puts a local session's startup at ~7.9k tokens (system prompt
  4.2k, project CLAUDE.md 1.8k, memory 0.7k, skills 0.45k, environment 0.3k, deferred MCP
  0.1k). This cloud session started at 65k. The difference is the web harness's larger
  system prompt, ~20 built-in tool schemas and ~25 skill descriptions, none of which the
  repo controls; the repo-controllable part is under 3k.

## 2. The ten, ranked by measured savings for this workflow

Items 1 and 2 overlap (both shrink the subagent bucket); their savings are not additive.

### 1. Subagents: cheaper model, minimal tools, narrow input, report to file
- `model: sonnet` in every `.claude/agents/*.md` except one `critic-final` agent that stays
  on the top model. `haiku` only for read-only grep/list lookups. Sonnet is ÷5 on every
  price line (input $2, output $10, cache write $2.5, read $0.20).
- `tools:` in the agent frontmatter limited to what the role needs (`Read, Grep` for a
  critic). Every agent rebuilds its own prefix; fewer tool schemas = smaller rebuild.
- `omitClaudeMd: true` for critics; they get the artifact and the bar, nothing else.
- Prompts pass `path:startline-endline`, never "read the whole plan".
- The agent writes its report to `scratchpad/critique-<role>.md` and returns ≤ 15 lines.
  This is a quality guard as much as a saving: the parent reads the full file before acting
  on any BLOCKING item, and grep is only for triage.
- `subagentPromptCacheTtl: "1h"` only for agents whose gaps between tool calls exceed
  5 minutes (long-thinking critics); otherwise the 5-minute default is cheaper.
- Expected: the 37% bucket ÷ 5 on price and roughly ÷ 2 on volume.
- Source backing: Anthropic's context-engineering post sets the norm that a subagent
  "returns a condensed summary of 1,000–2,000 tokens"; the docs' cost page says `model:
  haiku` for simple subagents, offers "run every subagent on one model", and warns agent
  teams use ~7× the tokens of a normal session (do not enable them for this repo).

### 2. Fewer critique rounds, deterministic checks first, blind top-model critic last
- Before any agent critique, run what a script can check: arithmetic in tables, dangling
  section references, undefined terms, lint, tests. Scripts cost zero cache writes.
- One critic per round using `docs/critic-checklist.md` (≤ 12 items), not three. BLOCKING
  means wrong, unsafe, or unrunnable. Stop after two consecutive rounds with zero BLOCKING.
- Keep one fresh, blind, top-model critic for the final gate only.
- This session used 9 critics across 3 rounds; the same top findings needed 2 combined
  critics plus a final gate. Ceiling on its own numbers: up to ~$15 of the $22.9 bucket.
- Source backing: the docs' best-practices page warns that a reviewer "prompted to find
  gaps will usually report some, even when the work is sound" and to tell it to flag only
  correctness gaps. That is exactly why BLOCKING is defined and the round count is capped.

### 3. Session lifecycle and a context ceiling
- At task end run `/clear`. Follow-ups ("I live in Texas") start a fresh session: a 65k
  startup write beats a 280k rewrite.
- If leaving for more than 55 minutes with context above 100k, run
  `/compact keep: <list of facts and file paths that must survive>` first.
- Compact at 100k regardless of pauses: cache reads and every future rewrite scale with
  context, and nothing in the conversation past 100k is usually needed verbatim.
- Ceiling on this session's numbers: the $16.8 cold-resume bucket plus part of the $4.5
  read bucket.
- New from the docs: on Pro/Max, resuming a large session after a long break offers
  **resume from a summary**; take it. The cache TTL drops from 1 h to 5 min once usage
  credits are being drawn, so set `promptCacheTtl: "1h"` if that applies. Side questions go
  through `/btw` (the answer never enters history). `/rewind` → "Summarize from here"
  compacts only part of a conversation. A `# Compact instructions` block in CLAUDE.md
  tells compaction what to keep (file list, test commands, decisions). `/clear` costs
  nothing; `/compact` on a large context is itself a large request.

### 4. Edit, do not rewrite
- No `Write` on an existing file over 100 lines unless more than 30% of it changes; use
  section `Edit`s. A new long document is written once, then only edited.
- The three rewrites cost $3.9; the same changes as edits would have cost ≈ $0.7.

### 5. Cap what enters context from tools
- Bash: `wc -l` before `cat`; `| tail -50` (not `head`, failures are at the tail) or
  `| grep -E 'FAIL|Error'`; keep a path to the full output on disk.
- Grep with `-n`, then `Read` with `offset`/`limit`. Never dump a directory.
- WebFetch prompts ask for ≤ 10 bullets. One WebSearch per question.
- `docs/EGRESS_BLOCKED.md` lists domains the proxy blocks (alpaca.markets,
  docs.alpaca.markets, finra.org, schwab.com, quantconnect.com, …) so they are never
  fetched again.
- Enforcement path: a PostToolUse hook returning `updatedToolOutput` that truncates any tool
  result over 4,000 characters to head + tail with a "truncated, full output at <path>"
  line. Bucket: the $6.8 per-turn appends and every later rewrite of them.
- Source backing and a better default: the docs' cost page ships a PreToolUse hook that
  rewrites `pytest`/`npm test`/`go test` to `| grep -A 5 -E '(FAIL|ERROR|error:)' | head
  -100`. The most-starred repo in this space, **rtk-ai/rtk** (39.5k stars, single Rust
  binary), does the same for 100+ commands through a Bash hook (cargo test 155 lines → 3;
  git status 119 chars → 28; authors report 60–90% on command output). It does not touch
  Read/Grep/Glob, so item 5's Grep→Read discipline still applies. alexgreensh/
  token-optimizer (2.4k stars) adds "structure maps" (code skeleton instead of full file)
  and delta re-reads (only the diff since the last read); adopt those two ideas as habits
  even without the tool. In this session Bash results were only ~2k tokens, so the payoff
  is for code-heavy sessions, once the app exists.

### 6. Effort routing
- `/effort medium` for edit, commit, format, and file-move turns; `high` as the default;
  `xhigh` only for design decisions and critiques. Thinking is billed as output and cannot
  be disabled on Fable, so effort is the only knob.
- Ceiling: part of the $3.8 "other output" bucket; small in dollars, but it also shortens
  turns.

### 7. Output contract
- Final message ≤ 150 words for tasks touching fewer than 3 files; exempt: verification
  results and stated uncertainty, which CLAUDE.md requires.
- No restating the task, no headers under 500 words, commit messages ≤ 6 lines, interim
  narration one sentence and only when the harness asks for it.
- Shares the $3.8 bucket with item 6; combined ceiling under $2 per session of this size.
- Source check: drona23/claude-token-efficient (6.1k stars) is a drop-in CLAUDE.md that
  enforces terse output; its own README reports 4–12% output-token reduction in
  reproducible 2026 benchmarks and warns the file "adds input tokens per message — net
  savings only positive at high output volume". Conclusion: keep the contract to the six
  lines in §3, do not import a long terse-mode file, and note that current models already
  skip preamble.

### 8. Turn economy
- Independent tool calls go in one message. No `TaskCreate`/`TaskUpdate` for tasks under
  3 files (8 task-tool turns here). Never `Read` a file after editing it. Do not retry a
  failed fetch on a blocked domain.
- Worth ≈ $0.6 per session directly; its real value is fewer appends for items 3 and 5.

### 9. Startup-prefix hygiene
- CLAUDE.md under 200 lines and free of rules the system prompt already states.
- File-scoped rules in `.claude/rules/*.md` with `paths:` so they load only when matching
  files are touched.
- Disable MCP servers a session does not need in `/mcp`; `skillOverrides` for skills the
  repo never uses; auto-memory under 200 lines.
- The 65k prefix is paid on every cold start and every agent; each 10k trimmed saves
  ~$0.13–0.25 per start and per agent.
- New from the docs: prefer CLI tools (`gh`, `aws`) over MCP servers, which "don't add any
  per-tool listing"; move workflow instructions out of CLAUDE.md into skills that load on
  invocation; run `/doctor` on a checked-in CLAUDE.md to get proposed cuts; install a code
  intelligence plugin for typed languages so "go to definition" replaces grep-then-read;
  turn off prompt suggestions (a background request after every response). The yurukusa
  cheat sheet (CLAUDE.md under 100 lines, decision rules as tables, safety rules moved to
  hooks) agrees but offers no measurements; treat it as corroboration, not evidence.

### 10. Measure and budget with enforceable limits
- `/usage` at the end of every task; the parser in Appendix A for per-bucket dollars.
- Every agent prompt carries an enforceable limit: "at most 30 tool calls and 15 files
  read, then report." Token counts are not enforceable from inside an agent.
- Monthly: look at the largest bucket and change one habit. This document is re-ranked
  when the largest bucket changes.
- New from the docs: `/context` shows what is occupying the window right now; `/usage`
  has a `Prompt cache (main)` line reporting misses, the likely cause ("tool definitions
  changed"), expected rebuilds, and warm/cold with the TTL — this replaces most of the
  Appendix A script for the main thread; `/insights` writes an HTML report on friction
  patterns; the plan-usage breakdown attributes spend to subagents, skills and MCP servers.
  egorfedorov/claude-context-optimizer (112 stars) adds per-file "read but never edited"
  heatmaps via hooks if per-file waste ever matters here.

## 3. Proposed CLAUDE.md additions (text only; not applied)

```
## Token budget
- Subagents: model sonnet unless the prompt says otherwise; tools limited to the role;
  pass file:line ranges; write reports to scratchpad and return ≤ 15 lines.
- Existing file > 100 lines: Edit, never Write, unless > 30% changes.
- Bash output: wc/tail/grep first; never cat a file > 200 lines.
- Before fetching a URL, check docs/EGRESS_BLOCKED.md.
- Task end: /clear. Leaving > 55 min with > 100k context: /compact keep: <facts>.
- /effort medium for edit/commit/format turns.
```

## 4. Proposed agent definition (text only; not applied)

```
# .claude/agents/critic.md
---
model: sonnet
tools: Read, Grep
omitClaudeMd: true
---
Hostile reviewer. Read only the path:lines given. Grade against the checklist in the
prompt. Write the report to the scratchpad path given; reply with ≤ 15 lines: one line
per BLOCKING finding, then the file path. At most 30 tool calls.
```

## 5. Source review: what Anthropic, the docs, and the popular repos say, and what changed

| Source | What it adds | Effect on the plan |
|---|---|---|
| Anthropic engineering, "Effective context engineering for AI agents" | Attention budget: smallest set of high-signal tokens; just-in-time retrieval over pre-loading; compaction keeps decisions and unresolved issues, discards raw outputs; structured note-taking (NOTES.md); subagents return 1–2k-token summaries; tool-result clearing as the lightest compaction | Confirms items 1, 3, 5. Adds the 1–2k summary norm to item 1 and "notes file, not chat history" to item 3 |
| Claude Code docs, "Manage costs effectively" | `/usage` cache line, `/context`, `/insights`; `/clear` between tasks; `/compact <focus>` and CLAUDE.md compact instructions; Sonnet default, `model: haiku` for simple subagents, one model for all subagents; MCP deferred by default, prefer CLI, `/mcp` disable; PreToolUse test-output filter hook; move CLAUDE.md content to skills, keep < 200 lines; effort/thinking settings; agent teams ~7×; cache TTL 1 h → 5 min on usage credits; resume-from-summary; background requests (prompt suggestions, goal check-ins, cross-session messages) | Adds mechanisms to items 3, 5, 9, 10; confirms 1 and 6 |
| Claude Code docs, "Best practices" | Context degrades before it fills; verification targets; plan mode only for multi-file work; `/btw`; partial summarize via `/rewind`; after two failed corrections, `/clear` and re-prompt; reviewer-gap caveat; `/doctor` for CLAUDE.md | Adds `/btw` and partial compaction to item 3; reviewer caveat to item 2; "two corrections → clear" as a rule in item 3 |
| Claude Code docs, "Explore the context window" | Local startup ≈ 7.9k tokens itemized; auto-compact window configurable (`/autocompact 500k`) | Explains the 65k cloud prefix; item 9 scope clarified |
| rtk-ai/rtk (39.5k stars) | Bash-hook proxy compressing command output 60–90%; not Read/Grep | Item 5: the drop-in once the app has tests and builds |
| drona23/claude-token-efficient (6.1k stars) | Terse-output CLAUDE.md; 4–12% output reduction; adds input tokens; net positive only for output-heavy sessions | Item 7: keep the contract short; do not import the file |
| alexgreensh/token-optimizer (2.4k stars) | Structure maps, delta re-reads, output compression (564 → 115 tokens on pytest), compaction checkpoints; 28% measured over 30 days | Item 5 habits; item 3 "checkpoint before compaction" |
| egorfedorov/claude-context-optimizer (112 stars) | Hook-based per-file waste heatmaps; "30–50% of context unused" claim | Item 10, optional |
| yurukusa gist "CLAUDE.md Token Optimization Cheat Sheet" | < 100 lines, tables for rules, hooks for safety rules, one example; no methodology | Item 9 corroboration only |
| GitHub issue anthropics/claude-code#44536 | Heavy setups measured 130–150k startup overhead; proposes lazy loading for skills/rules | Item 9 rationale |

What did **not** change: the ranking. Every source agrees on the direction of items 1–5,
and none supplies numbers that would move a lower item above them for this repo. The two
largest measured buckets here (subagent writes, cold resumes) are exactly the two the docs
name under "Why usage climbs in a long session".

## Appendix A: measurement script (used to produce §1; optional, not repo code)

```python
# parse ~/.claude/projects/<proj>/*.jsonl; dedupe by message id; sum by bucket
import json, glob, collections
P = {'in':10,'out':50,'w_main':20,'w_sub':12.5,'read':0.25}   # $/MTok, Fable 5.1
def sums(path):
    seen=set(); t=collections.Counter()
    for line in open(path):
        try: m=json.loads(line)
        except: continue
        msg=m.get('message',{}); u=msg.get('usage') if isinstance(msg,dict) else None
        if not u or msg.get('id') in seen: continue
        seen.add(msg['id'])
        for k in ('input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens'):
            t[k]+=u.get(k,0) or 0
    return t
main=sums(glob.glob('*.jsonl')[0]); sub=collections.Counter()
for p in glob.glob('*/subagents/*.jsonl'):
    for k,v in sums(p).items(): sub[k]+=v
print('main',dict(main)); print('sub',dict(sub))
```

Run it from `~/.claude/projects/<project-dir>/`. Print per-call rows with timestamps to
find cold-resume rewrites (large `cache_creation` with small `cache_read`).
