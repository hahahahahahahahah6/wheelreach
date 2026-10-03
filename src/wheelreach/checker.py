"""Core check logic: declared Python support vs installable files."""
from __future__ import annotations

from dataclasses import dataclass, field

from .specifier import allows
from .versions import sort_versions_newest_first
from .wheels import compatible_wheels

# Verdicts
WHEEL_ELIGIBLE = "WHEEL_ELIGIBLE"  # a compatible wheel exists and metadata allows this Python
BLOCKED_BY_REQUIRES_PYTHON = "BLOCKED_BY_REQUIRES_PYTHON"  # wheel exists but metadata excludes this Python
NO_WHEEL = "NO_WHEEL"  # no compatible wheel and no sdist either
NO_WHEEL_HAS_SDIST = "NO_WHEEL_HAS_SDIST"  # no compatible wheel, but an sdist could be built
UNKNOWN_METADATA = "UNKNOWN_METADATA"  # Requires-Python could not be parsed; check impossible
OUT_OF_SCOPE = "OUT_OF_SCOPE"  # outside the --expected-python range; not checked
IGNORED = "IGNORED"

# NO_WHEEL_HAS_SDIST is deliberately NOT a problem: pip can build from the
# sdist, so flagging it would cry wolf on every sdist-only package. It stays
# in the report as information. UNKNOWN_METADATA *is* a problem: an
# unparseable specifier means the check could not be completed, and
# "could not verify" must never look like a pass.
PROBLEM_VERDICTS = {BLOCKED_BY_REQUIRES_PYTHON, NO_WHEEL, UNKNOWN_METADATA}

DEFAULT_PYTHON_SET = [(3, 10), (3, 11), (3, 12), (3, 13), (3, 14)]


@dataclass
class Check:
    version: str
    python: tuple[int, int]  # (major, minor) target
    verdict: str = WHEEL_ELIGIBLE
    detail: str = ""
    wheel: str | None = None


def check_version(
    version: str,
    release: dict,
    pythons: list[tuple[int, int]],
    expected_python: str | None = None,
) -> list[Check]:
    """Check one release against each target Python (linux x86-64, CPython).

    expected_python is a Requires-Python specifier declaring which Pythons the
    project intends to support (e.g. ">=3.11"). Target Pythons outside that
    range are OUT_OF_SCOPE -- a blocked wheel there is not a bug. It must be
    pre-validated (parseable); the CLI rejects garbage with exit 2.
    """
    wheels = release.get("wheels") or []
    has_sdist = bool(release.get("has_sdist"))
    file_spec = release.get("wheel_requires_python") or {}
    results: list[Check] = []
    for major, minor in pythons:
        check = Check(version=version, python=(major, minor))
        if expected_python is not None and not allows(expected_python, major, minor):
            check.verdict = OUT_OF_SCOPE
            check.detail = f"outside --expected-python {expected_python!r}"
            results.append(check)
            continue
        compat = compatible_wheels(wheels, major, minor)
        if compat:
            # Prefer a wheel whose own file metadata (if any) doesn't block us.
            chosen = None
            blocked_fn = blocked_spec = None
            unknown_fn = unknown_spec = None
            for fn in compat:
                spec = file_spec.get(fn, release.get("requires_python"))
                try:
                    ok = allows(spec, major, minor)
                except ValueError:
                    # Unparseable metadata: the check is impossible, not a pass.
                    unknown_fn, unknown_spec = fn, spec
                    break
                if ok:
                    chosen = fn
                    break
                if blocked_fn is None:
                    blocked_fn, blocked_spec = fn, spec
            if unknown_fn is not None:
                check.verdict = UNKNOWN_METADATA
                check.detail = (
                    f"could not parse Requires-Python {unknown_spec!r} "
                    f"for {unknown_fn}"
                )
                check.wheel = unknown_fn
            elif chosen:
                check.verdict = WHEEL_ELIGIBLE
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
    expected_python: str | None = None,
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
        results.extend(check_version(version, release, pythons, expected_python))
    return results


def has_problems(results: list[Check]) -> bool:
    return any(c.verdict in PROBLEM_VERDICTS for c in results)
