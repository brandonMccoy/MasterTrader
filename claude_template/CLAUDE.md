# Project

<!-- Fill the three lines below. Everything else is generic. HTML comments are stripped before loading. -->
- Build: `<build command>`
- Test (single file): `<test command> <path>`; full suite only when asked
- Lint/typecheck: `<lint command>`

# Token rules (always on)

## Read narrowly
- `Grep -n` or `Glob` first; then `Read` with `offset`/`limit` on the matching region.
- Never read a whole directory, a lockfile, a build artifact, or a file over 300 lines
  without a line range. Run `/map <dir>` and read the skeleton instead.
- Never re-read a file you just edited. The edit result is the confirmation.
- Prefer `Grep` over spawning an agent for anything under three lookups.

## Write narrowly
- Existing file over 100 lines: `Edit` sections. `Write` only for new files or when more
  than 30% changes.
- No speculative refactors, no unrequested abstractions, no defensive code for cases that
  cannot happen here.

## Filter what enters context
- Bash: `wc -l` before `cat`; `| tail -50` or `| grep -E 'FAIL|Error'`; hooks bound the
  rest and save full output under `.claude/tool-output/`.
- WebFetch prompts ask for at most 10 bullets. One WebSearch per question.
  Check `docs/EGRESS_BLOCKED.md` before fetching; never retry a blocked domain.

## Delegate narrowly
- Use `scout` for "where is X" (file:line map), `verifier` to run checks, `researcher` for
  the web, `critic` for review. Pass `path:start-end`, never "read everything".
- Agents write long output to `.claude/reports/` and return at most 15 lines.

## Turns
- Batch independent tool calls in one message.
- Skip the task-tracking tools for work touching fewer than 3 files.

# Verify
- After each logical change run the narrowest check that would catch a regression (one
  test file, lint, a direct invocation). Say what you ran and what it returned.
- Never claim a test passed without having just seen the output.
- If something is checkable, check it; if not, state the assumption in one line.

# Communication
- One sentence before acting when the next step is not obvious.
- Final message: what changed, what was verified, what is next. Under 150 words for tasks
  under 3 files. Verification results and stated uncertainty are always included.
- No restating the task, no headers under 500 words, no filler.

# Compact instructions
When compacting, keep: the task statement, every decision made and why, the list of files
touched with what changed, the exact commands used to verify, open questions, and the
contents of `NOTES.md` `## Next`. Drop raw tool output, exploration that led nowhere, and
anything already committed.
