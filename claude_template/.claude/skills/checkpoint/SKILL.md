---
name: checkpoint
description: Write the session's state to NOTES.md (decisions, files touched, verification commands, next steps) so it survives /compact, /clear, or a break. Use before compacting, before leaving, and at the end of every task.
disable-model-invocation: true
---
Update `NOTES.md` in place (edit sections; do not rewrite the file):

- `## Decisions`: append one line per decision made this session, with the reason.
- `## Files touched`: one line per file, what changed, whether it is committed.
- `## Verify`: the exact commands that prove the current state works.
- `## Next`: replace with at most 15 lines of concrete next steps, most urgent first. This
  section is injected automatically at the next session start.
- `## Open questions`: anything unresolved that needs the owner.

Then say one line: "Checkpoint written. Safe to /compact or /clear." If the context is
above ~100k tokens, recommend `/compact` with the focus "keep NOTES.md ## Next and the
verification commands".
