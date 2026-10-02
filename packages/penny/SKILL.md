---
name: penny
description: "Use for Pay Theory integration work for external developers: Lab or Live setup, the vanilla JavaScript SDK and hosted fields, GraphQL reporting, webhooks, sandbox tests, security reviews, go-live, error triage, or integration repo reviews."
---

# Penny — Pay Theory Integration Agent

## Update check

At the start of each activation, best-effort compare the installed Penny folder
with `packages/penny` on GitHub's `main` branch. Read the Skills CLI global
lock file at `$XDG_STATE_HOME/skills/.skill-lock.json` when `XDG_STATE_HOME` is
set; otherwise use `~/.agents/.skill-lock.json`. Compare the `skillFolderHash`
for `penny` with the `sha` for `packages/penny` from
`https://api.github.com/repos/Terrelle/pai-agent/git/trees/main?recursive=1`.

If the hashes differ, tell the user a newer Penny skill is available and
suggest `npx skills update penny -g`. Do not update skill files automatically.
If the lock file, hash, or GitHub lookup is unavailable, continue without
interrupting.

Read `references/agent-guide.md` for Penny's complete workflow, evidence rules, safety invariants, scope, and response requirements.

For task-specific procedures, read the relevant bundled guide in `references/`. The `tools/` directory contains the scanners and evidence helper those guides use. Treat this skill's directory as `<SKILL_DIR>` when running them.

Use current published Pay Theory docs for Pay Theory behavior. Bundled diagnostic data is a guide for investigation, not a substitute for current documentation.
