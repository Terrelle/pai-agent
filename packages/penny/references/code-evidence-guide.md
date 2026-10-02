---
name: pay-theory-code-evidence
description: Use for Pay Theory local repository, agent, skill, or integrator-code reviews that need exact file existence, grep hits, line ranges, and citeable file:line evidence. Use before making claims about local files or stack/framework behavior.
---

# Pay Theory Code Evidence

Use this skill for read-only local evidence. Its script returns citeable
`path:line` output and redacts likely secrets.

## Commands

Resolve `SKILL_DIR` as the root directory of the Penny package.

List files before referencing paths:

```bash
python3 <SKILL_DIR>/tools/code-evidence/scripts/code_evidence.py list-files <target-repo>
python3 <SKILL_DIR>/tools/code-evidence/scripts/code_evidence.py list-files <target-repo> --json
```

Search exact local evidence:

```bash
python3 <SKILL_DIR>/tools/code-evidence/scripts/code_evidence.py grep "Evidence Contract" <target-repo>
python3 <SKILL_DIR>/tools/code-evidence/scripts/code_evidence.py grep "payTheoryFields" <target-repo>
```

Read exact line ranges:

```bash
python3 <SKILL_DIR>/tools/code-evidence/scripts/code_evidence.py read <target-file> --start 1 --end 90
```

## Rules

- Use `list-files` or equivalent discovery before claiming a path exists.
- Use `read` or `grep` before summarizing file contents.
- Cite findings with the emitted `path:line` token.
- Do not use this as a secret scanner; use `security-scan-guide.md` for that.
- Treat redacted output as enough to identify the issue without repeating secrets.
