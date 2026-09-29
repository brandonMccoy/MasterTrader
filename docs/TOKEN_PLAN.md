# Token-Spend Plan for Claude Code in this repo

Status: v3 (final after plan → critique → research → re-plan, three passes). Loop
history: `docs/TOKEN_LOG.md`. Nothing here is implemented; it is the plan.
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

### 2. Fewer critique rounds, deterministic checks first, blind top-model critic last
- Before any agent critique, run what a script can check: arithmetic in tables, dangling
  section references, undefined terms, lint, tests. Scripts cost zero cache writes.
- One critic per round using `docs/critic-checklist.md` (≤ 12 items), not three. BLOCKING
  means wrong, unsafe, or unrunnable. Stop after two consecutive rounds with zero BLOCKING.
- Keep one fresh, blind, top-model critic for the final gate only.
- This session used 9 critics across 3 rounds; the same top findings needed 2 combined
  critics plus a final gate. Ceiling on its own numbers: up to ~$15 of the $22.9 bucket.

### 3. Session lifecycle and a context ceiling
- At task end run `/clear`. Follow-ups ("I live in Texas") start a fresh session: a 65k
  startup write beats a 280k rewrite.
- If leaving for more than 55 minutes with context above 100k, run
  `/compact keep: <list of facts and file paths that must survive>` first.
- Compact at 100k regardless of pauses: cache reads and every future rewrite scale with
  context, and nothing in the conversation past 100k is usually needed verbatim.
- Ceiling on this session's numbers: the $16.8 cold-resume bucket plus part of the $4.5
  read bucket.

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

### 10. Measure and budget with enforceable limits
- `/usage` at the end of every task; the parser in Appendix A for per-bucket dollars.
- Every agent prompt carries an enforceable limit: "at most 30 tool calls and 15 files
  read, then report." Token counts are not enforceable from inside an agent.
- Monthly: look at the largest bucket and change one habit. This document is re-ranked
  when the largest bucket changes.

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
