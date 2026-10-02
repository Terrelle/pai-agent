---
name: pay-theory-api-skill
description: Use Pay Theory's docs-hosted GraphQL API agent skill package to discover operations and verify schema details.
---

# Pay Theory API Skill

Use this skill when Penny needs Pay Theory GraphQL operation, argument, type, or example details.

## Source

The API skill is hosted by Pay Theory docs, not bundled locally:

- Index: `https://docs.paytheory.com/llms.txt`
- API markdown index: `https://docs.paytheory.com/llm-docs/index.md`
- Live API skill ZIP: `https://docs.paytheory.com/llm-docs/agent-skills/pay-theory-api-skill.zip`
- Lab API skill ZIP: `https://docs.paytheory.com/llm-docs/agent-skills/pay-theory-api-skill-lab.zip`

## Workflow

1. Use Live by default. Use Lab only when the user is working in sandbox/Lab or explicitly asks for Lab behavior.
2. Fetch/read `llms.txt` or `llm-docs/index.md` first to find the relevant operation.
3. For exact operation/type details, use the docs-hosted API skill ZIP or the linked API markdown docs.
4. Cite the docs URL or API operation token in the answer.
5. If the docs-hosted content is unavailable or does not contain the requested field/operation, say it is not found. Do not infer from GraphQL naming conventions.

## Evidence Token

Use `[api-skill:<operationOrType>]` only after reading docs-hosted API skill content for that operation/type. Otherwise cite the exact `docs.paytheory.com/...` URL.
