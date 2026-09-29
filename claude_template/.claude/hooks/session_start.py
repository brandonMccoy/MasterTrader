#!/usr/bin/env python3
"""SessionStart hook: inject the '## Next' section of NOTES.md (max 15 lines).

Lets a fresh or resumed session pick up where the last one stopped without
re-reading history. Prints {} when NOTES.md has no Next section.
"""
import json
import os
import sys

MAX_LINES = 15


def next_section(path="NOTES.md"):
    if not os.path.exists(path):
        return ""
    lines, grab = [], False
    with open(path) as f:
        for line in f:
            if line.startswith("## "):
                if grab:
                    break
                grab = line.strip().lower() == "## next"
                continue
            if grab and line.strip():
                lines.append(line.rstrip())
            if len(lines) >= MAX_LINES:
                break
    return "\n".join(lines)


def main():
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    body = next_section()
    if not body:
        print("{}")
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "NOTES.md ## Next (from last session):\n" + body,
        }
    }))


if __name__ == "__main__":
    main()
