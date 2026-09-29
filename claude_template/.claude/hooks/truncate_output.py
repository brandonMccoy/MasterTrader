#!/usr/bin/env python3
"""PostToolUse hook for Bash: cap what enters context, keep the full output on disk.

If the tool response exceeds LIMIT characters, replace it with head + tail and a
pointer to the saved full copy in .claude/tool-output/. Prints {} otherwise.
"""
import json
import os
import sys
import time

LIMIT = 6000      # characters allowed into context (~1,500 tokens)
HEAD = 3500
TAIL = 2000
OUT_DIR = os.path.join(".claude", "tool-output")


def as_text(resp):
    if isinstance(resp, str):
        return resp
    if isinstance(resp, dict):
        parts = [str(resp.get(k, "")) for k in ("stdout", "stderr") if resp.get(k)]
        return "\n".join(parts) if parts else json.dumps(resp)
    return json.dumps(resp)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("{}")
        return
    text = as_text(data.get("tool_response"))
    if len(text) <= LIMIT:
        print("{}")
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    name = f"{int(time.time())}-{(data.get('tool_use_id') or 'out')[-8:]}.txt"
    path = os.path.join(OUT_DIR, name)
    try:
        with open(path, "w") as f:
            f.write(text)
    except Exception:
        path = "(could not save full output)"
    lines = text.count("\n") + 1
    trimmed = (
        f"{text[:HEAD]}\n\n[... truncated by token hook: {len(text)} chars / {lines} lines; "
        f"full output saved at {path} — grep it, do not cat it ...]\n\n{text[-TAIL:]}"
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedToolOutput": trimmed,
        }
    }))


if __name__ == "__main__":
    main()
