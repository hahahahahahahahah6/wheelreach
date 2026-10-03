"""Evaluate PEP 440-ish Requires-Python specifiers (stdlib only).

Supports the operators pip actually uses in Requires-Python:
==, !=, >=, <=, >, <, ~=, and comma-separated AND clauses, with optional
".*" wildcards (e.g. ==3.11.*). Only major.minor comparisons are made --
patch releases are irrelevant for reachability.
"""
from __future__ import annotations

import re

_OPS = ("==", "!=", ">=", "<=", "~=", ">", "<")
_CLAUSE = re.compile(r"^(==|!=|>=|<=|~=|>|<)\s*([0-9][0-9a-zA-Z.*]*)\s*$")


def _parse_version(text: str) -> tuple:
    """'3.11.*' -> (3, 11, '*'); '3.11' -> (3, 11)."""
    parts: list = []
    for piece in text.split("."):
        if piece == "*":
            parts.append("*")
        elif piece.isdigit():
            parts.append(int(piece))
        else:
            raise ValueError(f"bad version {text!r}")
    return tuple(parts)


def _cmp(a: tuple[int, int], b: tuple) -> int:
    """Compare (major, minor) against a parsed spec version (may have '*')."""
    b2 = tuple(0 if p == "*" else p for p in b[:2])
    while len(b2) < 2:
        b2 = b2 + (0,)
    return (a > b2) - (a < b2)


def _matches_one(python: tuple[int, int], op: str, ver: tuple) -> bool:
    if "*" in ver:
        prefix = tuple(p for p in ver if p != "*")
        plen = len(prefix)
        if op == "==":
            return python[:plen] == prefix
        if op == "!=":
            return python[:plen] != prefix
        raise ValueError(f"wildcard only supports == and !=, got {op}")
    c = _cmp(python, ver)
    if op == "==":
        return c == 0
    if op == "!=":
        return c != 0
    if op == ">=":
        return c >= 0
    if op == "<=":
        return c <= 0
    if op == ">":
        return c > 0
    if op == "<":
        return c < 0
    if op == "~=":
        # ~=3.11 means >=3.11, ==3.*
        if len(ver) < 2:
            raise ValueError(f"~= needs at least major.minor, got {ver}")
        return _cmp(python, ver) >= 0 and python[0] == ver[0]
    raise ValueError(f"unknown operator {op!r}")


def allows(spec: str | None, major: int, minor: int) -> bool:
    """True if Python (major, minor) satisfies a Requires-Python specifier.

    Empty/None specifier allows everything. Raises ValueError on garbage.
    """
    if not spec or not spec.strip():
        return True
    python = (major, minor)
    for clause in spec.split(","):
        clause = clause.strip()
        if not clause:
            continue
        m = _CLAUSE.match(clause)
        if not m:
            raise ValueError(f"unsupported Requires-Python clause {clause!r}")
        op, ver_text = m.group(1), m.group(2)
        if not _matches_one(python, op, _parse_version(ver_text)):
            return False
    return True
