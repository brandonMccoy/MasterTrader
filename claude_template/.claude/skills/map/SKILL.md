---
name: map
description: Build a code skeleton (files, classes, functions, signatures, line numbers) for a directory so Claude reads the map instead of the files. Use before exploring unfamiliar code.
disable-model-invocation: true
---
Build a structure map for `$ARGUMENTS` (a directory; default `.`).

1. Run: `python3 .claude/skills/map/map.py $ARGUMENTS`
   It writes `.claude/maps/<dir-slug>.md` and prints the path and line count.
2. `Read` the map file. It lists every source file with its top-level definitions as
   `line: signature`. Use it to pick the exact `path` and `offset`/`limit` to read next.
3. Do not `Read` any source file in that directory in full afterwards; read ranges.

Re-run after large refactors; the map is not updated automatically.
