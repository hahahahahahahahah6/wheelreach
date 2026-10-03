"""Version sorting (no external deps)."""
from __future__ import annotations

import re


def _split(version: str) -> list:
    parts = re.split(r"[.\-+_]", version.strip())
    key: list = []
    for part in parts:
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part.lower()))
    return key


def version_key(version: str) -> list:
    """Sort key for version strings. Numeric components sort numerically."""
    return _split(version)


def sort_versions_newest_first(versions) -> list[str]:
    """Return versions sorted newest-first (best effort, no PEP 440)."""
    return sorted(set(versions), key=version_key, reverse=True)


def parse_python_set(text: str) -> list[tuple[int, int]]:
    """'3.10,3.11' -> [(3, 10), (3, 11)]."""
    out = []
    for piece in text.split(","):
        piece = piece.strip()
        if not piece:
            continue
        m = re.fullmatch(r"(\d+)\.(\d+)", piece)
        if not m:
            raise ValueError(f"bad python version {piece!r}, want MAJOR.MINOR")
        out.append((int(m.group(1)), int(m.group(2))))
    if not out:
        raise ValueError("empty python set")
    return sorted(set(out))
