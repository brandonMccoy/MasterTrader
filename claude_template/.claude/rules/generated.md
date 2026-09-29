---
paths:
  - "**/package-lock.json"
  - "**/yarn.lock"
  - "**/pnpm-lock.yaml"
  - "**/poetry.lock"
  - "**/Cargo.lock"
  - "**/go.sum"
  - "**/*.min.*"
  - "**/dist/**"
  - "**/build/**"
  - "**/node_modules/**"
  - "**/.venv/**"
  - "**/coverage/**"
---

# Generated and vendored files

- Do not read these with `Read`. Use `Grep -n` for a specific string, or `wc -l`.
- Regenerate with the project's tool (`npm install`, `poetry lock`, `cargo update`);
  never edit by hand.
- Never include them in a diff summary beyond "lockfile regenerated".
