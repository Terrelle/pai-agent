#!/usr/bin/env python3
"""Execute the Pay Theory pre-go-live integration security scorecard.

Commands:
  list-checks         Show the checks and severities.
  scan <path>         Scan a file/dir; print a pass/fail scorecard with evidence.

Heuristic and conservative. Detects patterns of misuse, never a guessed credential
value. Not a PCI certification. Exit code is non-zero if any error-severity check fails
(so it can run as a CI go-live gate).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
RULES_PATH = SKILL_DIR / "_data" / "rules.json"


def load_rules() -> dict:
    if not RULES_PATH.exists():
        raise SystemExit(f"rules not found: {RULES_PATH}")
    return json.loads(RULES_PATH.read_text())


def is_client_file(path: Path, rules: dict) -> bool:
    if path.suffix.lower() not in set(rules.get("client_file_extensions", [])):
        return False
    server_dirs = set(rules.get("server_hint_dirs", []))
    parts = {p.lower() for p in path.parts}
    return not (parts & server_dirs)


def iter_files(root: Path, rules: dict):
    skip = set(rules.get("skip_dirs", []))
    exts = set(rules.get("scan_file_extensions", rules.get("client_file_extensions", [])))
    names = set(rules.get("scan_file_names", []))
    if root.is_file():
        yield root
        return
    for path in root.rglob("*"):
        if path.is_dir() or any(part in skip for part in path.parts):
            continue
        if path.suffix.lower() in exts or path.name in names:
            yield path


def redact(line: str) -> str:
    # Never echo a full secret-looking literal; keep it short and masked.
    def mask(m: str) -> str:
        return m[:2] + "***" if len(m) > 2 else "***"
    line = re.sub(r"(['\"])([A-Za-z0-9_\-]{12,})(['\"])", lambda m: m.group(1) + mask(m.group(2)) + m.group(3), line)
    line = re.sub(
        r"(?i)\b(api[_-]?key|secret[_-]?key|api[_-]?secret|client[_-]?secret|access[_-]?token|auth[_-]?token|bearer)\b(\s*[:=]\s*)(['\"]?)([A-Za-z0-9_\-]{8,})(['\"]?)",
        lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{mask(m.group(4))}{m.group(5)}",
        line,
    )
    return line.strip()[:160]


def cmd_list_checks(args: argparse.Namespace) -> None:
    rules = load_rules()
    if args.json:
        print(json.dumps([{"id": c["id"], "severity": c["severity"], "title": c["title"]}
                          for c in rules["checks"]], indent=2))
        return
    for c in rules["checks"]:
        scope = "client-only" if c.get("client_only") else "all files"
        print(f"  [{c['severity']}] {c['id']} ({scope}) - {c['title']}")


def cmd_scan(args: argparse.Namespace) -> None:
    rules = load_rules()
    root = Path(args.path)
    if not root.exists():
        raise SystemExit(f"path not found: {root}")

    compiled = []
    for c in rules["checks"]:
        compiled.append({
            "id": c["id"], "severity": c["severity"], "title": c["title"],
            "client_only": c.get("client_only", False), "message": c["message"],
            "patterns": [re.compile(p) for p in c.get("patterns", [])],
            "secondary": [re.compile(p) for p in c.get("secondary_patterns", [])],
        })

    evidence = {c["id"]: [] for c in compiled}
    secondary_hits = {c["id"]: False for c in compiled}

    for path in iter_files(root, rules):
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        client = is_client_file(path, rules)
        for idx, line in enumerate(lines, 1):
            for c in compiled:
                if c["client_only"] and not client:
                    # still allow secondary matching for context checks
                    pass
                for pat in c["patterns"]:
                    if pat.search(line):
                        if c["client_only"] and not client:
                            continue
                        evidence[c["id"]].append({"file": str(path), "line": idx, "snippet": redact(line)})
                for pat in c["secondary"]:
                    if pat.search(line):
                        secondary_hits[c["id"]] = True

    scorecard = []
    any_error = False
    for c in compiled:
        hits = evidence[c["id"]]
        # env-url-mismatch only fails if BOTH primary (lab) and secondary (live) present
        if c["secondary"]:
            failed = bool(hits) and secondary_hits[c["id"]]
        else:
            failed = bool(hits)
        status = "fail" if failed else "pass"
        if failed and c["severity"] == "error":
            any_error = True
        scorecard.append({
            "id": c["id"], "severity": c["severity"], "title": c["title"],
            "status": status, "message": c["message"] if failed else "",
            "evidence": hits if failed else [],
        })

    result = {"scanned_root": str(root), "scorecard": scorecard,
              "gate": "fail" if any_error else "pass",
              "disclaimer": "Heuristic integration-safety scan, not a PCI certification. Confirm findings manually."}

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Security scorecard for {root} — GATE: {result['gate'].upper()}")
        for s in scorecard:
            mark = "PASS" if s["status"] == "pass" else "FAIL"
            print(f"  [{mark}] ({s['severity']}) {s['id']} - {s['title']}")
            for e in s["evidence"]:
                print(f"        {e['file']}:{e['line']}  {e['snippet']}")
            if s["status"] == "fail":
                print(f"        -> {s['message']}")
        print(f"  ({result['disclaimer']})")

    sys.exit(1 if any_error else 0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pay Theory integration security scan")
    sub = parser.add_subparsers(dest="command", required=True)

    lc = sub.add_parser("list-checks")
    lc.add_argument("--json", action="store_true")
    lc.set_defaults(func=cmd_list_checks)

    sc = sub.add_parser("scan")
    sc.add_argument("path")
    sc.add_argument("--json", action="store_true")
    sc.set_defaults(func=cmd_scan)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
