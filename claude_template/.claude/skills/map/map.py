#!/usr/bin/env python3
"""Write a code skeleton for a directory: per file, top-level definitions with line numbers.

Language-agnostic by regex; good enough to pick read ranges. Output: .claude/maps/<slug>.md
"""
import os
import re
import sys

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "target", "coverage",
             "__pycache__", ".claude", ".next", ".cache", "vendor"}
EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".rb", ".php",
        ".cs", ".c", ".h", ".cpp", ".hpp", ".swift", ".scala", ".sh", ".sql"}
MAX_FILE_BYTES = 400_000
DEF = re.compile(
    r"^(?:export\s+)?(?:default\s+)?(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?"
    r"(?:def|class|func|fn|function|interface|type|struct|enum|trait|impl|module|"
    r"public|private|protected|static|abstract|final|const|let|var|CREATE\s+TABLE)\b.*$",
    re.IGNORECASE,
)


def signatures(path):
    out = []
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return [(0, "(large file, skipped)")]
        with open(path, errors="replace") as f:
            for i, line in enumerate(f, 1):
                s = line.rstrip()
                if not s or s[0] in " \t":
                    continue  # top-level only
                if DEF.match(s) and len(s) < 160:
                    out.append((i, s))
    except Exception:
        pass
    return out


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    root = root.rstrip("/") or "."
    slug = "root" if root in (".", "") else re.sub(r"[^A-Za-z0-9]+", "-", root).strip("-")
    os.makedirs(os.path.join(".claude", "maps"), exist_ok=True)
    out_path = os.path.join(".claude", "maps", f"{slug}.md")
    lines = [f"# Map of {root}", ""]
    files = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if os.path.splitext(name)[1] not in EXTS:
                continue
            path = os.path.join(dirpath, name)
            sigs = signatures(path)
            try:
                nlines = sum(1 for _ in open(path, errors="replace"))
            except Exception:
                nlines = 0
            files += 1
            lines.append(f"## {path} ({nlines} lines)")
            lines.extend(f"- {n}: {s}" for n, s in sigs[:80])
            if len(sigs) > 80:
                lines.append(f"- … {len(sigs) - 80} more")
            lines.append("")
    with open(out_path, "w") as f:
        f.write("\n".join(lines))
    print(f"{out_path}: {files} files, {len(lines)} lines")


if __name__ == "__main__":
    main()
