# claude_template — a token-lean starting point for any Claude Code project

Copy the contents of this folder into the root of a new project. Every file here exists
for one reason: spend the fewest tokens that still produce correct work. Nothing is
project-specific; the placeholders in `CLAUDE.md` are the only lines you must edit.

## Install (5 minutes)

1. Copy everything (including the dotfiles) into your project root.
2. Edit the `<placeholders>` at the top of `CLAUDE.md` (build, test, lint commands).
3. Make the hooks executable: `chmod +x .claude/hooks/*.py`. Requires `python3`.
4. Start Claude Code, run `/context`: `CLAUDE.md` should be listed under Memory files and
   the hooks under `/hooks`.
5. Run `/doctor prompt-audit` once a month; it proposes cuts to anything that has gone stale.

## What each piece does and why it saves tokens

| Path | Loads when | Token purpose |
|---|---|---|
| `CLAUDE.md` | every session (~60 lines) | The only always-on instructions: read narrowly, edit not rewrite, filter output, report tersely, what compaction must keep. Under 200 lines by design. HTML comments are stripped before loading, so maintainer notes cost nothing. |
| `.claude/settings.json` | every session | Wires the hooks; 1-hour main cache TTL; subagents default to Sonnet; prompt suggestions off (a hidden request after every reply). |
| `.claude/hooks/filter_bash.py` | before every Bash call | Rewrites noisy commands: test runners show only failures, bare `git log`/`git diff` become `--oneline`/`--stat`, `cat`/`find`/`ls -R` get bounded. Deterministic; Claude cannot forget it. |
| `.claude/hooks/truncate_output.py` | after every Bash call | Anything over 6,000 characters is cut to head + tail; the full output is saved to `.claude/tool-output/` and its path is returned, so nothing is lost and nothing floods context. |
| `.claude/hooks/session_start.py` | session start / resume | Injects the `## Next` section of `NOTES.md` (≤ 15 lines) so a fresh session resumes without re-reading history. |
| `.claude/rules/*.md` | only when a matching file is read | Path-scoped rules for tests, docs, and generated files. They cost nothing until relevant. |
| `.claude/agents/*.md` | when delegated to | Pre-sized subagents: `scout` (Haiku, read-only, returns a file:line map), `verifier` (Sonnet, runs the checks, returns pass/fail), `researcher` (Sonnet, writes notes to a file), `critic` (Sonnet, blind review to a file), `critic-final` (inherits the top model, final gate only). Each has a tool allow-list, a turn cap, and `omitClaudeMd` where it does not need project rules. |
| `.claude/skills/*/SKILL.md` | only when invoked | `/map` builds a code skeleton so Claude reads signatures instead of files; `/checkpoint` writes `NOTES.md` before `/compact` or a break; `/critique` runs the blind review loop with a checklist; `/token-audit` prices your session from the transcript; `/wrapup` verifies, records, commits, and reminds you to `/clear`. |
| `NOTES.md` | on demand and via the start hook | Structured note-taking: decisions, files touched, next steps. Survives compaction; replaces re-explaining. |
| `docs/EGRESS_BLOCKED.md` | on demand | Domains that failed to fetch, so they are never retried. |
| `.gitignore` | — | Keeps tool output, reports, maps, and local settings out of git. |

## The habits the files cannot enforce

- End every task with `/wrapup` (or at least `/clear`). Never start a second task in a
  session over ~100k tokens. Leaving for over an hour with a big context → `/checkpoint`
  then `/compact`.
- Side questions go through `/btw`; they never enter history.
- `/effort medium` for edit, commit, and format turns; raise it for design decisions.
- Prefer CLI tools (`gh`, `aws`) over MCP servers; disable unused servers in `/mcp`.
- Check `/usage` at the end of a task; the `Prompt cache (main)` line tells you if the cache
  is being rebuilt and why.

## Adjusting

- `CLAUDE_CODE_SUBAGENT_MODEL` in `settings.json` sets the default for every subagent;
  each agent file can override with `model:`.
- Truncation limit: edit `LIMIT` in `truncate_output.py`.
- Add a path-scoped rule by creating `.claude/rules/<topic>.md` with `paths:` frontmatter.
- Move anything that grows in `CLAUDE.md` into a skill; skills load only when invoked.
