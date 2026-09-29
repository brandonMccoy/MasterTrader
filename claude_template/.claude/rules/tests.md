---
paths:
  - "**/*test*"
  - "**/*spec*"
  - "**/tests/**"
---

# Test files

- Run the single test file that covers the change, not the whole suite, unless asked.
- The Bash hook already filters runner output to failures; do not add `-v`/`--verbose`.
- Report: number passed, number failed, names of failing tests, and the first assertion
  message for each. Never paste the full run.
- Never skip, disable, or loosen a test to get green.
