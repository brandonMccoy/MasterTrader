#!/usr/bin/env python3
"""Price Claude Code sessions for the current project from local transcripts.

Buckets: uncached input, output, cache writes, cache reads — for the main thread and for
subagents — plus cold-resume rewrites (a call whose cache write exceeds its cache read
by a large margin after a gap). Edit PRICES for your model ($ per million tokens).
"""
import collections
import glob
import json
import os
import re
import sys

PRICES = {  # $/MTok — defaults for Claude Opus 5.5; cache write ≈ 1.25× input (5m) or 2× (1h)
    "input": 4.0, "output": 20.0, "cache_write_main": 8.0, "cache_write_sub": 5.0, "cache_read": 0.20,
}
COLD_WRITE_MIN = 60_000  # a single-call cache write this large is a prefix rebuild


def project_dir():
    cwd = os.getcwd()
    slug = re.sub(r"[^A-Za-z0-9]", "-", cwd)
    cand = os.path.expanduser(os.path.join("~", ".claude", "projects", slug))
    if os.path.isdir(cand):
        return cand
    base = os.path.expanduser("~/.claude/projects")
    if not os.path.isdir(base):
        return None
    dirs = [os.path.join(base, d) for d in os.listdir(base)]
    dirs = [d for d in dirs if os.path.isdir(d)]
    return max(dirs, key=os.path.getmtime) if dirs else None


def sums(path):
    seen, t, cold = set(), collections.Counter(), []
    with open(path, errors="replace") as f:
        for line in f:
            try:
                m = json.loads(line)
            except Exception:
                continue
            msg = m.get("message")
            if not isinstance(msg, dict) or not msg.get("usage"):
                continue
            mid = msg.get("id")
            if mid in seen:
                continue
            seen.add(mid)
            u = msg["usage"]
            for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
                t[k] += u.get(k, 0) or 0
            w, r = u.get("cache_creation_input_tokens", 0) or 0, u.get("cache_read_input_tokens", 0) or 0
            if w >= COLD_WRITE_MIN and w > 2 * r:
                cold.append((m.get("timestamp", "")[:19], w))
    return t, cold, len(seen)


def dollars(t, sub=False):
    wk = "cache_write_sub" if sub else "cache_write_main"
    return {
        "input": t["input_tokens"] * PRICES["input"] / 1e6,
        "output": t["output_tokens"] * PRICES["output"] / 1e6,
        "cache_write": t["cache_creation_input_tokens"] * PRICES[wk] / 1e6,
        "cache_read": t["cache_read_input_tokens"] * PRICES["cache_read"] / 1e6,
    }


def main():
    pdir = project_dir()
    if not pdir:
        print("No transcript directory found under ~/.claude/projects/")
        sys.exit(1)
    mains = sorted(glob.glob(os.path.join(pdir, "*.jsonl")), key=os.path.getmtime)
    subs = glob.glob(os.path.join(pdir, "*", "subagents", "*.jsonl"))
    if not mains:
        print(f"No sessions in {pdir}")
        sys.exit(1)
    mt, cold, calls = collections.Counter(), [], 0
    for p in mains:
        t, c, n = sums(p)
        mt.update(t); cold += c; calls += n
    st = collections.Counter()
    for p in subs:
        st.update(sums(p)[0])
    md, sd = dollars(mt), dollars(st, sub=True)
    total = sum(md.values()) + sum(sd.values())
    print(f"project: {pdir}\nsessions: {len(mains)}  main API calls: {calls}  subagents: {len(subs)}")
    print("\nbucket                     tokens        $")
    rows = [
        ("main cache writes", mt["cache_creation_input_tokens"], md["cache_write"]),
        ("main cache reads", mt["cache_read_input_tokens"], md["cache_read"]),
        ("main output", mt["output_tokens"], md["output"]),
        ("main uncached input", mt["input_tokens"], md["input"]),
        ("subagent cache writes", st["cache_creation_input_tokens"], sd["cache_write"]),
        ("subagent cache reads", st["cache_read_input_tokens"], sd["cache_read"]),
        ("subagent output (floor)", st["output_tokens"], sd["output"]),
    ]
    for name, tok, usd in sorted(rows, key=lambda r: -r[2]):
        share = (usd / total * 100) if total else 0
        print(f"{name:26} {tok:>11,} {usd:8.2f}  {share:4.0f}%")
    print(f"{'TOTAL (estimate)':26} {'':>11} {total:8.2f}")
    if cold:
        print(f"\ncold-resume rewrites (cache write ≥ {COLD_WRITE_MIN:,} with little read): {len(cold)}")
        for ts, w in cold[-5:]:
            print(f"  {ts}  {w:,} tokens rewritten")
        print("  → /clear at task end, /checkpoint + /compact before breaks, resume-from-summary when offered")


if __name__ == "__main__":
    main()
