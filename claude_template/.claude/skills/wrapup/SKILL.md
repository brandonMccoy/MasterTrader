---
name: wrapup
description: End-of-task routine — verify, record, commit, and clear. Use when a task is done or being handed off, so the next session starts small.
disable-model-invocation: true
---
1. Launch `verifier` with the project's check commands. If anything fails, stop and
   report; do not proceed.
2. Run `/checkpoint` (updates `NOTES.md`).
3. `git status -sb`; stage only the files touched for this task; commit with a message
   of at most 6 lines describing what and why. Push only if the user asked for pushes.
4. Reply in ≤ 8 lines: what shipped, verification result, commit hash, anything left in
   `NOTES.md ## Next`.
5. Final line: "Run /clear before the next task." (Do not start new work in this
   session.)
