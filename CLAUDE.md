# CLAUDE.md

Operating rules for Claude Code in this repo. Follow these before any repo-specific
guidance that gets added below as the codebase grows.

## Token discipline

- Read only what the task needs. Use `Grep`/`Glob` to find the relevant file(s) and
  region first; don't read whole files or whole directories "to be safe."
- Don't re-read a file just edited — the edit tool already confirms success.
- Don't restate file contents, diffs, or command output back to the user; summarize
  the result in one or two sentences instead.
- Prefer targeted greps/searches over spawning exploration agents for anything that
  takes fewer than ~3 lookups.
- No speculative refactors, no unrequested abstractions, no defensive code for cases
  that can't happen here. Smallest diff that correctly does the job.
- No filler commentary, no restating the task back, no narrating tool calls before
  making them beyond a single short sentence when non-obvious.

## Never guess

- If a fact is checkable (a symbol's definition, a config value, an API's actual
  signature, whether a file/branch/dependency exists), check it — don't infer it from
  naming conventions or memory.
- If something is ambiguous and not checkable from the repo, state the assumption
  explicitly in one line rather than silently picking one, or ask if the ambiguity is
  material and irreversible.
- Never claim a test passed, a build succeeded, or a bug is fixed without having just
  run the command and seen the output.

## Verify after every chunk of work

Treat each logically complete change (a function, a fix, a small feature slice) as a
checkpoint, not just the end of the whole task:

1. **Re-read the diff** for that chunk before moving on — does it actually do what was
   intended, with no leftover debug code, dead branches, or TODOs?
2. **Run the narrowest check that would catch a regression**: the specific test file,
   a type check, a lint pass, or a manual invocation — not necessarily the full suite,
   but something that actually exercises the change.
3. **Self-critique before reporting done**: ask "what input would break this?" and
   "did I actually verify this or am I assuming it works?" Fix what you find; don't
   surface it as a caveat instead of fixing it.
4. Only then move to the next chunk or report completion to the user.

If there is no automated check available for a chunk, say so explicitly rather than
implying it was verified.

## Communication

- State what you're about to do in one sentence before acting, when it's not obvious.
- Report results directly: what changed, what was verified, what's next. No headers
  or sections for small tasks.
- Flag uncertainty instead of hiding it behind confident phrasing.
