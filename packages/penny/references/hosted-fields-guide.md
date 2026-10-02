---
name: pay-theory-hosted-fields-debug
description: Diagnose and fix a stuck vanilla JavaScript SDK + hosted-fields integration — fields not rendering, observers not firing, transact returning ERROR/FAILED, validation never passing, styling/sizing issues, and SDK error codes (NO_FIELDS, FIELD_ERROR, NOT_VALID, NOT_READY, TRANSACTING_FIELD_ERROR, etc.). Use when an integrator reports the card/ACH fields won't appear, nothing happens on submit, an observer callback never runs, or transact returns an ERROR. Pairs with triage-error (which handles processor decline/failure codes) — this skill handles SDK and hosted-field lifecycle problems.
---

# Pay Theory Hosted Fields Debugging

Use this skill to debug a JavaScript SDK + hosted-fields integration. It works from
a symptom (or an SDK error code) plus the integrator's code and console output, and
returns a specific cause and fix — not a wall of possibilities.

This skill does not duplicate the docs. It **grounds in docs.paytheory.com / llm-docs** and the
schema skill, and adds a symptom→cause→fix decision tree and a static scanner for the
common pitfalls.

## Boundaries (avoid overlap)

- **`docs.paytheory.com` / `llm-docs`** — authoritative for SDK prose: hosted-field element IDs,
  observers, `transact` behavior, styling. Fetch/read the relevant docs page before asserting a
  fact; prefer `llms.txt`, `llm-docs/index.md`, and linked `/llm-docs/...md` pages.
- **`api-guide.md`** — authoritative for GraphQL operations/types.
- **`triage-error` (agent lifecycle)** — handles processor **decline/failure codes**
  (e.g. `102`, `193`, `888888`) and reporting. This skill handles **SDK / hosted-field
  lifecycle** problems (rendering, observers, init order, `transact` result handling,
  SDK error codes).
- Inherits the agent's invariants: never place the secret key in client code, never
  move card capture out of hosted fields. For secret-key/PCI scanning use
  `security-scan-guide.md`; this guide covers **functional** correctness only.

## Workflow

1. Resolve `SKILL_DIR` as the root directory of the Penny package.
2. Get the integrator's symptom, the relevant code (HTML + JS), and any console output
   (the `errorObserver` string or `result.type`/`result.error`).
3. Map the symptom or SDK error code to causes:

```bash
python3 <SKILL_DIR>/tools/hosted-fields-debug/scripts/hosted_fields_debug.py list-symptoms
python3 <SKILL_DIR>/tools/hosted-fields-debug/scripts/hosted_fields_debug.py diagnose fields-not-rendering
python3 <SKILL_DIR>/tools/hosted-fields-debug/scripts/hosted_fields_debug.py diagnose NOT_VALID
```

4. When you have their files, run the static scan for known pitfalls:

```bash
python3 <SKILL_DIR>/tools/hosted-fields-debug/scripts/hosted_fields_debug.py scan <path-to-their-frontend>
```

5. Confirm any fact you rely on against `docs.paytheory.com` / `llm-docs`, then give one cause + one fix.
   Re-check after they apply it.

## What the scan looks for (functional pitfalls)

- Missing or misspelled hosted-field container IDs (e.g. `pay-theory-credit-card`
  family) when `payTheoryFields` is called — risks `NO_FIELDS` / `FIELD_ERROR`.
- `result.type` compared against `FAILURE` (the failed result type is **`FAILED`**;
  only the transaction body status/state uses `FAILURE`).
- `transact` amount that looks like dollars, not cents (decimal amount).
- Observers registered **after** `payTheoryFields(...)` instead of before.
- Wrong/legacy observer names (correct: `readyObserver`, `errorObserver`,
  `stateObserver`, `validObserver`).
- `payTheoryFields` used with no SDK import present.
- Dynamic SDK loading inside `DOMContentLoaded` before calling `payTheoryFields(...)`; prefer the docs-style static SDK script import, or if dynamic loading is required, mount after `document.readyState === "complete"` / `window.load` so fields do not hang pending with zero iframes.

The scan is heuristic and conservative — treat findings as leads to confirm in the
integrator's code, not as proof.

## Reference

`_data/diagnostics.json` holds the element IDs, observer names, SDK error-code table,
and the symptom decision tree, derived from Pay Theory published docs
(`docs.paytheory.com` / `llm-docs`). If the published docs and this file disagree,
the published docs win — update this reference.
