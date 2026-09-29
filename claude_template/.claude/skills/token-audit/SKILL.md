---
name: token-audit
description: Price the current project's Claude Code sessions from local transcripts by bucket (subagents, cold-resume rewrites, output, cache reads) and name the biggest lever. Use at the end of a task or weekly.
disable-model-invocation: true
---
1. Run `/usage` and note the Session block and the `Prompt cache (main)` line (misses,
   likely cause, warm/cold).
2. Run: `python3 .claude/skills/token-audit/usage.py`
   It finds this project's transcript directory under `~/.claude/projects/`, deduplicates
   API calls by message id, and prints per-bucket tokens and estimated dollars for the
   main thread and subagents, plus any cold-resume rewrites (large cache writes after a
   gap). Prices are in the script header; edit them for your model.
3. Report in ≤ 10 lines: total estimated $, the top two buckets, and the single habit or
   setting change that would cut the largest one (from `docs/TOKEN_PLAN.md` if present,
   otherwise: subagent model/tools, session hygiene, edit-not-rewrite, output filtering).
