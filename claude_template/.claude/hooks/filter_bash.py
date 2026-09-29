#!/usr/bin/env python3
"""PreToolUse hook for Bash: rewrite noisy commands into bounded ones.

Reads the hook JSON on stdin, prints {} to leave the command alone, or a
hookSpecificOutput.updatedInput that replaces it. Never blocks a command.
Conservative by design: only patterns whose full output is rarely needed.
"""
import json
import re
import sys

TEST_RUNNERS = re.compile(
    r"^\s*(npm test|npm run test|yarn test|pnpm test|pytest|python -m pytest|go test|cargo test|"
    r"mvn test|gradle test|dotnet test|rspec|bundle exec rspec|jest|vitest|mix test|make test)\b"
)


def rewrite(cmd: str):
    c = cmd.strip()
    if "|" in c or ">" in c or ";" in c or "&&" in c:
        return None  # user already shaped the output; leave compound commands alone
    if TEST_RUNNERS.match(c):
        return f"{c} 2>&1 | grep -A 5 -E '(FAIL|ERROR|error:|failed|passed|Tests:|✗|✖)' | head -100"
    if re.match(r"^git status\s*$", c):
        return "git status -sb"
    if re.match(r"^git log\s*$", c):
        return "git log --oneline -n 20"
    if re.match(r"^git diff\s*$", c):
        return "git diff --stat"
    if re.match(r"^(ls -R|ls -laR|tree)\b", c):
        return f"{c} | head -100"
    if re.match(r"^find \.\s*$", c):
        return "find . -maxdepth 3 | head -100"
    if c.startswith("find ") and "-maxdepth" not in c and "-name" not in c:
        return f"{c} | head -100"
    m = re.match(r"^cat\s+(\S+)\s*$", c)
    if m:
        return f"wc -l {m.group(1)} && sed -n '1,200p' {m.group(1)}"
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("{}")
        return
    cmd = (data.get("tool_input") or {}).get("command") or ""
    new = rewrite(cmd)
    if not new:
        print("{}")
        return
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "token filter: bounded output",
            "updatedInput": {**data.get("tool_input", {}), "command": new},
        }
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
