"""wheelreach CLI."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .checker import (
    DEFAULT_PYTHON_SET,
    PROBLEM_VERDICTS,
    Check,
    check_package,
    has_problems,
)
from .config import find_default_config, load_config_file, merge_config
from .http import FetchError
from .pypi import fetch_pypi_info, latest_version
from .versions import parse_python_set


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wheelreach",
        description="Check that a package's declared Python support has installable files.",
    )
    p.add_argument("--version", action="version", version="wheelreach " + __version__)
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("check", help="check Python-version reachability of a package")
    c.add_argument("--package", required=True, help="PyPI package name")
    c.add_argument("--version", dest="pkg_version", default=None,
                   help="check one version (default: latest stable)")
    c.add_argument("--all", action="store_true",
                   help="check every published version")
    c.add_argument("--limit", type=int, default=10,
                   help="with --all, how many of the newest versions to check (default 10)")
    c.add_argument("--python", default=None, metavar="3.11",
                   help="check a single Python version (default: 3.10-3.14)")
    c.add_argument("--python-set", default=None, metavar="3.10,3.11",
                   help="comma-separated target Pythons (overrides config)")
    c.add_argument("--ignore", action="append", default=[], metavar="VERSION",
                   help="skip a version (repeatable)")
    c.add_argument("--config", default=None,
                   help="TOML file with [tool.wheelreach] python_set/ignore "
                   "(default: ./pyproject.toml if present)")
    c.add_argument("--format", choices=["text", "json"], default="text",
                   help="output format (default text)")
    return p


def check_to_dict(check: Check) -> dict:
    return {
        "version": check.version,
        "python": f"{check.python[0]}.{check.python[1]}",
        "verdict": check.verdict,
        "wheel": check.wheel,
        "detail": check.detail,
    }


def format_text(results: list[Check]) -> str:
    rows = [("version", "python", "verdict", "wheel")]
    for c in results:
        rows.append((
            c.version,
            f"{c.python[0]}.{c.python[1]}",
            c.verdict,
            c.wheel or "-",
        ))
    widths = [max(len(r[i]) for r in rows) for i in range(4)]
    lines = []
    for i, row in enumerate(rows):
        lines.append("  ".join(cell.ljust(widths[j]) for j, cell in enumerate(row)).rstrip())
        if i == 0:
            lines.append("  ".join("-" * w for w in widths))
    problems = [c for c in results if c.verdict in PROBLEM_VERDICTS]
    lines.append("")
    summary = f"checked {len(results)} version/python pairs, {len(problems)} problem(s)"
    if problems:
        summary += ": " + ", ".join(
            f"{c.version} on {c.python[0]}.{c.python[1]} ({c.verdict})" for c in problems
        )
    lines.append(summary)
    for c in problems:
        if c.detail:
            lines.append(f"  {c.version} / {c.python[0]}.{c.python[1]}: {c.detail}")
    return "\n".join(lines)


def cmd_check(args: argparse.Namespace) -> int:
    if args.python and args.python_set:
        print("wheelreach: error: --python and --python-set are mutually exclusive",
              file=sys.stderr)
        return 2
    if args.limit is not None and args.limit < 1:
        print("wheelreach: error: --limit must be >= 1", file=sys.stderr)
        return 2
    try:
        if args.python:
            pythons = parse_python_set(args.python)
            ignore = args.ignore
        else:
            config_path = args.config or find_default_config()
            file_config = load_config_file(config_path) if config_path else {"python_set": None, "ignore": []}
            config = merge_config(file_config, args.python_set, args.ignore)
            pythons = parse_python_set(config["python_set"]) if config["python_set"] else list(DEFAULT_PYTHON_SET)
            ignore = config["ignore"]
    except ValueError as exc:
        print(f"wheelreach: error: {exc}", file=sys.stderr)
        return 2

    try:
        info = fetch_pypi_info(args.package)
    except FetchError as exc:
        print(f"wheelreach: error: {exc}", file=sys.stderr)
        return 2

    only = args.pkg_version
    if only is None and not args.all:
        only = latest_version(info["versions"])
    if only is not None and only not in info["releases"]:
        print(f"wheelreach: error: version {only!r} not found for {args.package}",
              file=sys.stderr)
        return 2

    results = check_package(
        info["releases"],
        info["versions"],
        pythons,
        ignore=ignore,
        only=None if args.all else only,
        limit=args.limit if args.all else None,
    )

    if args.format == "json":
        print(json.dumps([check_to_dict(c) for c in results], indent=2))
    else:
        print(format_text(results))
    return 1 if has_problems(results) else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "check":
        return cmd_check(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
