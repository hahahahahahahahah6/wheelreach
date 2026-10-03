"""Core check logic: declared Python support vs installable files."""
from __future__ import annotations

from dataclasses import dataclass, field

from .specifier import allows
from .versions import sort_versions_newest_first
from .wheels import compatible_wheels

# Verdicts
INSTALLABLE = "INSTALLABLE"  # a compatible wheel exists and metadata allows it
BLOCKED_BY_REQUIRES_PYTHON = "BLOCKED_BY_REQUIRES_PYTHON"  # wheel exists but metadata excludes this Python
NO_WHEEL = "NO_WHEEL"  # no compatible wheel and no sdist either
NO_WHEEL_HAS_SDIST = "NO_WHEEL_HAS_SDIST"  # no compatible wheel, but an sdist could be built
IGNORED = "IGNORED"

PROBLEM_VERDICTS = {BLOCKED_BY_REQUIRES_PYTHON, NO_WHEEL, NO_WHEEL_HAS_SDIST}

DEFAULT_PYTHON_SET = [(3, 10), (3, 11), (3, 12), (3, 13), (3, 14)]


@dataclass
class Check:
    version: str
    python: tuple[int, int]  # (major, minor) target
    verdict: str = INSTALLABLE
    detail: str = ""
    wheel: str | None = None


def check_version(
    version: str,
    release: dict,
    pythons: list[tuple[int, int]],
) -> list[Check]:
    """Check one release against each target Python (linux x86-64, CPython)."""
    wheels = release.get("wheels") or []
    has_sdist = bool(release.get("has_sdist"))
    file_spec = release.get("wheel_requires_python") or {}
    results: list[Check] = []
    for major, minor in pythons:
        check = Check(version=version, python=(major, minor))
        compat = compatible_wheels(wheels, major, minor)
        if compat:
            # Prefer a wheel whose own file metadata (if any) doesn't block us.
            chosen = None
            blocked_fn = blocked_spec = None
            for fn in compat:
                spec = file_spec.get(fn, release.get("requires_python"))
                try:
                    ok = allows(spec, major, minor)
                except ValueError:
                    ok = True  # unparseable metadata: don't invent a failure
                if ok:
                    chosen = fn
                    break
                if blocked_fn is None:
                    blocked_fn, blocked_spec = fn, spec
            if chosen:
                check.verdict = INSTALLABLE
                check.wheel = chosen
            else:
                check.verdict = BLOCKED_BY_REQUIRES_PYTHON
                check.detail = (
                    f"wheel {blocked_fn} exists for cp{major}{minor} but "
                    f"Requires-Python {blocked_spec!r} excludes Python {major}.{minor}"
                )
                check.wheel = blocked_fn
        elif has_sdist:
            check.verdict = NO_WHEEL_HAS_SDIST
            check.detail = "no compatible wheel; sdist is published and might build"
        else:
            check.verdict = NO_WHEEL
            check.detail = "no compatible wheel and no sdist published"
        results.append(check)
    return results


def check_package(
    releases: dict,
    versions: list[str],
    pythons: list[tuple[int, int]] | None = None,
    *,
    ignore: list | None = None,
    only: str | None = None,
    limit: int | None = None,
) -> list[Check]:
    """Check releases. only=one version; otherwise newest-first (+limit)."""
    pythons = pythons or list(DEFAULT_PYTHON_SET)
    ignored = set(ignore or [])
    ordered = sort_versions_newest_first(versions)
    if only is not None:
        ordered = [only] if only in releases else []
    if limit is not None:
        ordered = ordered[:limit]
    results: list[Check] = []
    for version in ordered:
        if version in ignored:
            results.append(Check(version=version, python=pythons[0], verdict=IGNORED,
                                 detail="ignored by config"))
            continue
        release = releases.get(version) or {}
        results.extend(check_version(version, release, pythons))
    return results


def has_problems(results: list[Check]) -> bool:
    return any(c.verdict in PROBLEM_VERDICTS for c in results)
