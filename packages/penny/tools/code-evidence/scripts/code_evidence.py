#!/usr/bin/env python3
"""Read-only local file evidence helper for Pay Theory agent reviews."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path


DEFAULT_EXCLUDES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    ".turbo",
    ".venv",
    "venv",
    "__pycache__",
}

TEXT_EXTENSIONS = {
    ".c",
    ".cc",
    ".cfg",
    ".cjs",
    ".conf",
    ".css",
    ".csv",
    ".env",
    ".go",
    ".graphql",
    ".htm",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".md",
    ".mdx",
    ".mjs",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".svelte",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".yaml",
    ".yml",
}

TEXT_FILENAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".gitignore",
    "Dockerfile",
    "Makefile",
}

SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(secret|token|password|passwd|api[_-]?key|authorization)(\s*[:=]\s*)(['\"]?)([^'\"\s,;]{8,})"
)
LONG_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9_+=-]{32,}(?![A-Za-z0-9])")


def redact(text: str) -> str:
    def replace_assignment(match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2)}{match.group(3)}<redacted>"

    text = SECRET_ASSIGNMENT_RE.sub(replace_assignment, text)
    return LONG_TOKEN_RE.sub("<redacted>", text)


def is_text_candidate(path: Path) -> bool:
    return path.name in TEXT_FILENAMES or path.suffix.lower() in TEXT_EXTENSIONS


def iter_files(root: Path, include_globs: list[str] | None = None) -> list[Path]:
    root = root.resolve()
    if root.is_file():
        return [root] if is_text_candidate(root) else []

    files: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in DEFAULT_EXCLUDES]
        for filename in filenames:
            path = Path(current) / filename
            if not is_text_candidate(path):
                continue
            rel = str(path.relative_to(root))
            if include_globs and not any(fnmatch.fnmatch(rel, pattern) for pattern in include_globs):
                continue
            files.append(path)
    return sorted(files)


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except UnicodeDecodeError:
        return path.read_bytes().decode("utf-8", errors="replace")


def cmd_list_files(args: argparse.Namespace) -> int:
    root = Path(args.path)
    if not root.exists():
        print(f"missing path: {root}", file=sys.stderr)
        return 2
    files = [display_path(path) for path in iter_files(root, args.glob)]
    if args.json:
        print(json.dumps(files, indent=2))
    else:
        for path in files:
            print(path)
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists() or not path.is_file():
        print(f"missing file: {path}", file=sys.stderr)
        return 2
    lines = read_text(path).splitlines()
    start = max(1, args.start)
    end = args.end or len(lines)
    end = min(end, len(lines))
    if start > end:
        print(f"invalid range: {start}-{end}", file=sys.stderr)
        return 2
    label = display_path(path)
    for number in range(start, end + 1):
        print(f"{label}:{number}: {redact(lines[number - 1])}")
    return 0


def cmd_grep(args: argparse.Namespace) -> int:
    root = Path(args.path)
    if not root.exists():
        print(f"missing path: {root}", file=sys.stderr)
        return 2

    flags = 0 if args.case_sensitive else re.IGNORECASE
    pattern = re.escape(args.pattern) if args.literal else args.pattern
    try:
        regex = re.compile(pattern, flags)
    except re.error as error:
        print(f"invalid regex: {error}", file=sys.stderr)
        return 2

    matches: list[dict[str, object]] = []
    for path in iter_files(root, args.glob):
        lines = read_text(path).splitlines()
        for index, line in enumerate(lines, start=1):
            if regex.search(line):
                matches.append(
                    {
                        "path": display_path(path),
                        "line": index,
                        "text": redact(line),
                    }
                )
                if len(matches) >= args.limit:
                    break
        if len(matches) >= args.limit:
            break

    if args.json:
        print(json.dumps(matches, indent=2))
    else:
        for match in matches:
            print(f"{match['path']}:{match['line']}: {match['text']}")
    return 0 if matches else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-files")
    list_parser.add_argument("path")
    list_parser.add_argument("--glob", action="append", help="fnmatch pattern relative to root; may be repeated")
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(func=cmd_list_files)

    read_parser = subparsers.add_parser("read")
    read_parser.add_argument("path")
    read_parser.add_argument("--start", type=int, default=1)
    read_parser.add_argument("--end", type=int)
    read_parser.set_defaults(func=cmd_read)

    grep_parser = subparsers.add_parser("grep")
    grep_parser.add_argument("pattern")
    grep_parser.add_argument("path")
    grep_parser.add_argument("--literal", action="store_true")
    grep_parser.add_argument("--case-sensitive", action="store_true")
    grep_parser.add_argument("--glob", action="append", help="fnmatch pattern relative to root; may be repeated")
    grep_parser.add_argument("--limit", type=int, default=50)
    grep_parser.add_argument("--json", action="store_true")
    grep_parser.set_defaults(func=cmd_grep)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
