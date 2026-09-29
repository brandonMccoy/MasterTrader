---
name: critique
description: Run the blind review loop on a diff, file range, or document. Scripts first, then one Sonnet critic per round with a checklist, stop at two clean rounds, then critic-final once.
disable-model-invocation: true
---
Target: `$ARGUMENTS` (a path, `path:start-end`, or `diff` for the current git diff).

1. **Deterministic checks first** (zero agent tokens): run lint/typecheck/tests via the
   `verifier` agent; for documents, grep for dangling references and undefined terms.
   Fix what these find before any review.
2. **Round**: launch the `critic` agent with the target, the checklist at
   `.claude/skills/critique/checklist.md`, and a report path
   `.claude/reports/critique-<target>-r<N>.md`. Read the report file, not just the reply,
   before acting on any BLOCKING item.
3. Fix BLOCKING findings with `Edit`. Re-run step 1.
4. Repeat step 2 with a fresh `critic` (never reuse the previous agent). Stop when two
   consecutive rounds report zero BLOCKING, or after 3 rounds; list what remains.
5. **Final gate**: launch `critic-final` once. `SHIP` → done. `HOLD` → fix and re-run
   step 5 once more at most.

Report to the user in ≤ 10 lines: rounds run, BLOCKING found and fixed, what remains,
report paths.
