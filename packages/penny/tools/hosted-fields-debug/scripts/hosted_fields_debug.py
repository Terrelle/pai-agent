#!/usr/bin/env python3
"""Diagnose Pay Theory JavaScript SDK + hosted-fields problems.

Three commands:
  list-symptoms              List symptom ids and SDK error codes.
  diagnose <key>             Show causes/checks/fixes for a symptom id or error code.
  scan <path>                Heuristic static scan of frontend code for common pitfalls.

Grounded in _data/diagnostics.json (derived from docs.paytheory.com / llm-docs). Heuristic findings
are leads to confirm in the integrator's code, not proof.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = SKILL_DIR / "_data" / "diagnostics.json"

SCAN_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".html", ".htm", ".php", ".vue", ".svelte"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "out", "__pycache__"}
KNOWN_OBSERVERS = {"readyObserver", "errorObserver", "stateObserver", "validObserver"}
LEGACY_OBSERVER_RE = re.compile(r"\b(errorobserver|error_observer|validobserver|valid_observer|readyobserver|stateobserver)\b")
ALL_FIELD_IDS = set()


def load_data() -> dict:
    if not DATA_PATH.exists():
        raise SystemExit(f"diagnostics not found: {DATA_PATH}")
    return json.loads(DATA_PATH.read_text())


def _collect_field_ids(data: dict) -> set[str]:
    ids: set[str] = set()
    for key, val in data.get("element_ids", {}).items():
        if isinstance(val, list):
            ids.update(val)
    return ids


def cmd_list_symptoms(args: argparse.Namespace) -> None:
    data = load_data()
    if args.json:
        print(json.dumps({"symptoms": list(data.get("symptoms", {}).keys()),
                          "error_codes": list(data.get("error_codes", {}).keys())}, indent=2))
        return
    print("Symptoms:")
    for sid, s in data.get("symptoms", {}).items():
        print(f"  {sid} - {s.get('summary','')}")
    print("\nSDK error codes:")
    for code, c in data.get("error_codes", {}).items():
        print(f"  {code} - {c.get('meaning','')}")


def cmd_diagnose(args: argparse.Namespace) -> None:
    data = load_data()
    key = args.key
    symptoms = data.get("symptoms", {})
    errors = data.get("error_codes", {})

    if key in symptoms:
        result = {"type": "symptom", "id": key, **symptoms[key]}
    elif key.upper() in errors:
        result = {"type": "error_code", "code": key.upper(), **errors[key.upper()]}
    else:
        # fuzzy: symptom contains key
        matches = [sid for sid in symptoms if key.lower() in sid.lower()]
        if len(matches) == 1:
            result = {"type": "symptom", "id": matches[0], **symptoms[matches[0]]}
        else:
            raise SystemExit(
                f"unknown key: {key}. Try `list-symptoms`. "
                f"Symptoms: {', '.join(symptoms)}. Error codes: {', '.join(errors)}."
            )

    if args.json:
        print(json.dumps(result, indent=2))
        return

    if result["type"] == "error_code":
        print(f"[{result['code']}] {result.get('meaning','')}")
        print(f"  fix: {result.get('fix','')}")
        return

    print(f"{result['id']}: {result.get('summary','')}")
    for i, c in enumerate(result.get("causes", []), 1):
        print(f"  {i}. cause: {c['cause']}")
        print(f"     check: {c['check']}")
        print(f"     fix:   {c['fix']}")
        print(f"     docs:  {c.get('ref','')}")
    if result.get("related_errors"):
        print(f"  related SDK errors: {', '.join(result['related_errors'])}")


def _iter_files(root: Path):
    if root.is_file():
        yield root
        return
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SCAN_EXTENSIONS:
            yield path


def _add(findings, path, lineno, check, message, severity="warn"):
    findings.append({"file": str(path), "line": lineno, "check": check,
                     "message": message, "severity": severity})


def cmd_scan(args: argparse.Namespace) -> None:
    data = load_data()
    field_ids = _collect_field_ids(data)
    root = Path(args.path)
    if not root.exists():
        raise SystemExit(f"path not found: {root}")

    findings: list[dict] = []
    uses_paytheoryfields = False
    found_any_field_id = False
    has_sdk_import = False
    init_line_by_file: dict[str, int] = {}
    observer_lines: list[tuple[str, int]] = []
    domcontentloaded_dynamic_sdk_files: dict[str, int] = {}

    for path in _iter_files(root):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        low_text = text.lower()
        has_domcontentloaded_listener = re.search(
            r"addEventListener\s*\(\s*['\"]DOMContentLoaded['\"]", text
        ) or re.search(
            r"\.onDOMContentLoaded\b", text
        )
        if (
            has_domcontentloaded_listener
            and ("createelement('script'" in low_text or "createelement(\"script\"" in low_text)
            and "appendchild" in low_text
            and "paytheoryfields" in low_text
        ):
            line_no = next((i for i, l in enumerate(lines, 1) if "DOMContentLoaded" in l and "addEventListener" in l), 1)
            domcontentloaded_dynamic_sdk_files.setdefault(str(path), line_no)

        for idx, line in enumerate(lines, 1):
            low = line.lower()

            if any(fid in line for fid in field_ids):
                found_any_field_id = True

            if "paytheoryfields" in low:
                uses_paytheoryfields = True
                init_line_by_file.setdefault(str(path), idx)

            if "pay-theory" in low and ("src=" in low or "import" in low or "sdk" in low and "url" in low):
                has_sdk_import = True
            if "paytheory" in low and "src=" in low:
                has_sdk_import = True

            # result.type compared against FAILURE
            if re.search(r"\.type\s*===?\s*['\"]FAILURE['\"]", line) or re.search(r"['\"]FAILURE['\"]\s*===?\s*\w+\.type", line):
                _add(findings, path, idx, "result-type",
                     "result.type compared against 'FAILURE'; the failed result type is 'FAILED'.", "error")

            # amount looks like dollars (decimal) in a transact call context
            m = re.search(r"amount\s*[:=]\s*(\d+\.\d+)", line)
            if m:
                _add(findings, path, idx, "amount-cents",
                     f"amount {m.group(1)} looks like dollars; transact expects an integer number of cents.", "warn")

            # legacy/wrong observer casing
            for lm in LEGACY_OBSERVER_RE.finditer(low):
                token = lm.group(1)
                if token not in {o.lower() for o in KNOWN_OBSERVERS} or token not in {o for o in KNOWN_OBSERVERS}:
                    # only flag if the actual cased token isn't a known observer
                    if not any(o in line for o in KNOWN_OBSERVERS):
                        _add(findings, path, idx, "observer-name",
                             f"possible wrong observer name '{token}'; expected one of {sorted(KNOWN_OBSERVERS)}.", "warn")
                        break

            for obs in KNOWN_OBSERVERS:
                if obs in line:
                    observer_lines.append((str(path), idx))

            # near-miss field id typos
            if re.search(r"paytheory-credit-card|pay-theory-card\b|pay-theory-cc", low) and not any(fid in line for fid in field_ids):
                _add(findings, path, idx, "field-id",
                     "possible misspelled hosted-field container id; check exact IDs (e.g. pay-theory-credit-card).", "warn")

    # cross-file heuristics
    if uses_paytheoryfields and not found_any_field_id:
        _add(findings, root, 0, "no-fields",
             "payTheoryFields is used but no known hosted-field container IDs were found; risks NO_FIELDS/FIELD_ERROR.", "error")
    if uses_paytheoryfields and not has_sdk_import:
        _add(findings, root, 0, "sdk-import",
             "payTheoryFields is used but no Pay Theory SDK <script> import was detected; confirm the SDK is imported.", "warn")

    # dynamic SDK import inside DOMContentLoaded can hang because the SDK may wait for DOMContentLoaded too
    for file_path, line_no in domcontentloaded_dynamic_sdk_files.items():
        _add(findings, Path(file_path), line_no, "sdk-load-timing",
             "SDK appears to be dynamically loaded inside DOMContentLoaded and payTheoryFields is used; this can leave payTheoryFields pending with no iframes. Prefer a static SDK script import, or if loading dynamically, mount after document.readyState === 'complete' / window.load.", "warn")

    # observer-after-init (same file)
    for file_path, init_line in init_line_by_file.items():
        after = [ln for (fp, ln) in observer_lines if fp == file_path and ln > init_line]
        if after:
            _add(findings, Path(file_path), min(after), "observer-order",
                 "observer appears to be registered after payTheoryFields; register observers before initializing.", "warn")

    summary = {"scanned_root": str(root), "findings": findings,
               "counts": {"error": sum(1 for f in findings if f["severity"] == "error"),
                          "warn": sum(1 for f in findings if f["severity"] == "warn")}}
    if args.json:
        print(json.dumps(summary, indent=2))
        return
    if not findings:
        print(f"No hosted-fields pitfalls detected under {root}. (Heuristic — confirm manually.)")
        return
    print(f"Hosted-fields scan of {root}: {summary['counts']['error']} error, {summary['counts']['warn']} warn (heuristic)")
    for f in findings:
        loc = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
        print(f"  [{f['severity']}] {f['check']} - {loc}")
        print(f"      {f['message']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pay Theory hosted-fields debugging")
    sub = parser.add_subparsers(dest="command", required=True)

    ls = sub.add_parser("list-symptoms")
    ls.add_argument("--json", action="store_true")
    ls.set_defaults(func=cmd_list_symptoms)

    dg = sub.add_parser("diagnose")
    dg.add_argument("key", help="symptom id or SDK error code")
    dg.add_argument("--json", action="store_true")
    dg.set_defaults(func=cmd_diagnose)

    sc = sub.add_parser("scan")
    sc.add_argument("path", help="file or directory of frontend code")
    sc.add_argument("--json", action="store_true")
    sc.set_defaults(func=cmd_scan)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except BrokenPipeError:
        sys.exit(0)


if __name__ == "__main__":
    main()
