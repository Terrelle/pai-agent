## Platform Setup

- Run: `npx skills add https://github.com/Terrelle/pai-agent/tree/main/packages/penny -g -a claude-code -a codex`
- If the installer asks **Symlink or Copy**, choose **Symlink**. It keeps one shared copy for Codex and Claude, making updates simpler. If it never asks, just continue.
- Start a new Claude Code session and call Penny with `/penny`. In Codex, start a new session and call Penny with `$penny`.
- To update later, run: `npx skills update penny -g`

## What's Included

- **`SKILL.md`** - Skill definition and Penny workflow instructions
- **`references/`** - Pay Theory integration, hosted fields, API, security, and evidence guides
- **`tools/`** - Helpers for hosted fields debugging, code evidence, and security scans
