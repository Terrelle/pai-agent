---
name: pay-theory-evidence-gate
description: Use for any Pay Theory agent answer that reviews local files, uses docs or WebFetch, discusses SDK/API/security behavior, generates integration code, or makes factual claims that need grounding. Enforces cite-or-refuse, source labels, full-read-before-answer, and a verifier pass.
---

# Pay Theory Evidence Gate

Use this skill before answering Pay Theory integration, docs, schema, security,
web, or local-repo review questions.

## Contract

No evidence, no claim. A factual claim must have one source token:

- Pay Theory docs: `[docs.paytheory.com/...md]`
- GraphQL: `[api-skill:operationOrType]`
- Local file: `[path/to/file:line]`
- Scanner: `[security-scan]` or `[hosted-fields-debug]`

If no source supports the claim, say: "I don't see that in the available Pay
Theory sources."

## Workflow

1. Choose the authority:
   - Pay Theory prose behavior: WebFetch against `docs.paytheory.com`, especially `llms.txt`, `llm-docs/index.md`, and linked `/llm-docs/...md` pages
   - GraphQL operation/type details: `api-guide.md`
   - Local files: `code-evidence-guide.md`
   - Hosted-fields symptoms: `hosted-fields-guide.md`
   - Security status: `security-scan-guide.md`
2. Read full evidence before answering:
   - Docs index/search pages are discovery only; fetch/read the specific answer-bearing docs page before claiming.
   - Local file discovery is discovery only; use `read` or cite grep output.
   - GraphQL operation lists are discovery only; use `get-operation`.
3. Label claims when needed:
   - **Verified:** directly supported by cited source output
   - **Inferred:** reasoned from cited source output, not directly stated
   - **Not found:** searched the source and found no support
   - **Assumption:** user-provided or temporary working assumption
4. For high-risk claims, quote before claim:
   - auth header format
   - SDK result values
   - webhook behavior
   - sandbox failure triggers
   - credential/config variable names
   - secret-key handling
   - PCI/hosted-fields claims
   - go-live/security scorecard status
5. Before final response, verify every factual claim:
   - Cite it.
   - Label it as inference or assumption.
   - Remove it.
   - Or state that it was not found.
   - For env/config variable names, cite a source or label the name as an app-local convention chosen by the user/project.

## WebFetch Rules

Use WebFetch against `docs.paytheory.com` as the Pay Theory prose-docs source.
Prefer `llms.txt`, `llm-docs/index.md`, and linked `/llm-docs/...md` pages.

If WebFetch returns a Docusaurus shell, navigation page, homepage, 404, or text
that does not contain answer-bearing content, treat it as no content retrieved.
Do not synthesize from the shell and do not fall back to memory.

If docs and schema output conflict, report the conflict with both source tokens.

## Local Review Rules

- Enumerate files before referencing paths.
- Never describe a file not read in this session.
- Every finding needs a `file:line` token.
- Include an **Evidence reviewed** section with paths or line ranges.
- If a stack/framework is not visible from files, say unknown or ask.
