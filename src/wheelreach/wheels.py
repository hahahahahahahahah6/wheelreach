"""Parse wheel filenames and test compatibility with a target interpreter.

Target model is deliberately narrow and honest: CPython on Linux x86-64.
A wheel is compatible with CPython 3.X on linux_x86_64 when:
- a python tag matches: cp3X itself, a forward-compatible abi3 tag built for
  an older 3.Y, or a generic py3 / py2.py3 tag; and
- the abi tag is compatible: cp3X (or cp3Xm/cp3Xt...), abi3, or none; and
- the platform tag covers linux_x86_64: any, linux_x86_64, or a
  manylinux* / musllinux* x86_64 tag.
"""
from __future__ import annotations

import re

_CP_TAG = re.compile(r"^cp3(\d+)$")
_ABI3_PY = re.compile(r"^cp3(\d+)$")


def parse_wheel_filename(filename: str) -> dict | None:
    """Split a wheel filename into its tags. Returns None if not parseable."""
    if not filename.endswith(".whl"):
        return None
    stem = filename[:-4]
    parts = stem.split("-")
    if len(parts) < 5:
        return None
    pythontag, abitag, platformtag = parts[-3], parts[-2], parts[-1]
    return {
        "python_tags": pythontag.split("."),
        "abi_tags": abitag.split("."),
        "platform_tags": platformtag.split("."),
        "filename": filename,
    }


def _python_tag_matches(python_tags: list[str], major: int, minor: int) -> bool:
    want = f"cp{major}{minor}"
    for tag in python_tags:
        if tag == want:
            return True
        if tag in ("py3", "py2.py3"):
            return True
        m = _CP_TAG.match(tag)
        # abi3 wheels built for an older 3.Y run on newer 3.X
        if m and int(m.group(1)) <= minor:
            return True
    return False


def _abi_tag_matches(abi_tags: list[str], major: int, minor: int) -> bool:
    want_prefix = f"cp{major}{minor}"
    for tag in abi_tags:
        if tag in ("abi3", "none"):
            return True
        if tag == want_prefix or tag.startswith(want_prefix):
            return True
    return False


def _platform_tag_matches(platform_tags: list[str]) -> bool:
    for tag in platform_tags:
        if tag == "any":
            return True
        if tag == "linux_x86_64":
            return True
        if tag.endswith("x86_64") and (
            tag.startswith("manylinux") or tag.startswith("musllinux")
        ):
            return True
    return False


def wheel_supports(parsed: dict, major: int = 3, minor: int = 10) -> bool:
    """True if a parsed wheel filename installs on CPython major.minor / linux x86-64."""
    return (
        _python_tag_matches(parsed["python_tags"], major, minor)
        and _abi_tag_matches(parsed["abi_tags"], major, minor)
        and _platform_tag_matches(parsed["platform_tags"])
    )


def compatible_wheels(filenames: list[str], major: int, minor: int) -> list[str]:
    """Filenames of wheels compatible with CPython major.minor on linux x86-64."""
    out = []
    for name in filenames:
        parsed = parse_wheel_filename(name)
        if parsed and wheel_supports(parsed, major, minor):
            out.append(name)
    return out
