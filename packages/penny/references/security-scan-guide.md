---
name: pay-theory-security-scan
description: Run the pre-go-live integration security scorecard as an executable scan of the integrator's codebase — detect secret keys in client-side code, raw card capture outside hosted fields, hardcoded credentials, SDK credential / secret key misuse, and Lab/Live SDK URL mismatches. Use in the review-security lifecycle stage and as the mandatory go-live gate. This is an integration-safety scan, not a formal PCI certification.
---

# Pay Theory Security Scan

Use this skill to execute the security scorecard the agent gates go-live on, instead
of eyeballing the code. It scans common frontend, backend, and local env/config files
and returns a pass/fail per check with file:line evidence.

It is **heuristic and conservative**: it flags patterns that are very likely problems,
but a human must confirm, and a clean scan is not a guarantee or a PCI certification.

## Boundaries (avoid overlap)

- **`hosted-fields-guide.md`** — functional correctness (rendering, observers,
  transact handling). This skill covers **security/PCI-scope** only.
- **`docs.paytheory.com` / `llm-docs` and `api-guide.md`** — authoritative docs/schema.
- This skill does not invent credential formats. It detects **patterns of misuse**
  (a secret-looking value in client code, raw card inputs, hardcoded auth headers),
  never a guessed key value. Confirm findings against the actual code.

## Checks

1. **secret-key-client** (error) — a secret/`*_secret`/`apiSecret`/`client_secret`
   value, or a `partner;`/`MERCHANT_UID;` Authorization header, appearing in
   client-side / SDK code.
2. **raw-card-capture** (error) — raw card inputs (`<input>` for card number / cvv /
   expiry) or variables capturing a PAN/CVV outside hosted fields. PCI-scope risk.
3. **secret-in-paytheoryfields** (error) — a secret-looking value passed to
   `payTheoryFields` (only with docs-supported, flow-specific SDK parameters).
4. **hardcoded-credentials** (warn) — credential-looking literals assigned to
   key/secret/token identifiers.
5. **env-url-mismatch** (warn) — Lab (`paytheorylab`/`paytheorystudy`) and Live SDK
   markers mixed in the same surface; confirm the environment is intentional.

## Workflow

1. Resolve `SKILL_DIR` as the root directory of the Penny package.
2. List the checks (optional): `python3 <SKILL_DIR>/tools/security-scan/scripts/security_scan.py list-checks`
3. Scan the integrator's repo or frontend:

```bash
python3 <SKILL_DIR>/tools/security-scan/scripts/security_scan.py scan <path>
python3 <SKILL_DIR>/tools/security-scan/scripts/security_scan.py scan <path> --json
```

4. Treat any **error**-severity finding as a blocking go-live gate failure until the
   integrator fixes it. Name the specific file:line; never echo a secret value back.

## Output

A scorecard: each check `pass` / `fail` with the evidence locations. Exit code is
non-zero when any error-severity check fails, so it can run in CI as a gate.
