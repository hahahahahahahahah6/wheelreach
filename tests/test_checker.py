"""Tests for the core checker, incl. replays of two verified real cases.

Fixtures mirror the real evidence (verified 2026-10-03):
- coreai_models.json: trimmed live PyPI JSON for coreai-models==0.1.0.
  Wheel declares Requires-Python >=3.14 (still true live) while the source
  pyproject.toml says >=3.11 (apple/coreai-models#96).
- triton_nightly.json: mirrors pytorch/pytorch#186099 -- cp315 wheel with
  METADATA Requires-Python >=3.10,<3.15, uninstallable on Python 3.15.
"""
import json
import os

from wheelreach.checker import (
    BLOCKED_BY_REQUIRES_PYTHON,
    IGNORED,
    WHEEL_ELIGIBLE,
    NO_WHEEL,
    NO_WHEEL_HAS_SDIST,
    OUT_OF_SCOPE,
    UNKNOWN_METADATA,
    check_package,
    check_version,
    has_problems,
)
from wheelreach.pypi import fetch_pypi_info

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        data = json.load(fh)
    return fetch_pypi_info("x", get=lambda url: (json.dumps(data).encode(), {}))


def test_coreai_models_blocked_on_311_and_312():
    info = load_fixture("coreai_models.json")
    results = check_package(info["releases"], info["versions"],
                            [(3, 11), (3, 12), (3, 13), (3, 14)])
    by_py = {(c.python[0], c.python[1]): c for c in results}
    assert by_py[(3, 11)].verdict == BLOCKED_BY_REQUIRES_PYTHON
    assert by_py[(3, 12)].verdict == BLOCKED_BY_REQUIRES_PYTHON
    assert by_py[(3, 13)].verdict == BLOCKED_BY_REQUIRES_PYTHON
    assert by_py[(3, 14)].verdict == WHEEL_ELIGIBLE
    assert has_problems(results)


def test_triton_nightly_blocked_on_315():
    info = load_fixture("triton_nightly.json")
    results = check_package(info["releases"], info["versions"], [(3, 14), (3, 15)])
    by_py = {(c.python[0], c.python[1]): c for c in results}
    # cp315-only wheel: nothing for 3.14 either (no sdist in this nightly index)
    assert by_py[(3, 14)].verdict == NO_WHEEL
    assert by_py[(3, 15)].verdict == BLOCKED_BY_REQUIRES_PYTHON
    assert "Requires-Python" in by_py[(3, 15)].detail


def test_installable_when_wheel_and_metadata_agree():
    release = {
        "requires_python": ">=3.9",
        "wheels": ["pkg-2.0-py3-none-any.whl"],
        "has_sdist": True,
    }
    results = check_version("2.0", release, [(3, 10), (3, 14)])
    assert all(c.verdict == WHEEL_ELIGIBLE for c in results)
    assert not has_problems(results)


def test_no_wheel_but_sdist_is_distinct_and_not_a_problem():
    release = {"requires_python": ">=3.9", "wheels": [], "has_sdist": True}
    (c,) = check_version("1.0", release, [(3, 11)])
    assert c.verdict == NO_WHEEL_HAS_SDIST
    # pip can build from the sdist: informational, not a failure (no wolf-crying)
    assert not has_problems([c])


def test_no_wheel_no_sdist():
    release = {"requires_python": ">=3.9", "wheels": [], "has_sdist": False}
    (c,) = check_version("1.0", release, [(3, 11)])
    assert c.verdict == NO_WHEEL


def test_wrong_platform_wheel_counts_as_no_wheel():
    release = {
        "requires_python": ">=3.9",
        "wheels": ["pkg-1.0-cp311-cp311-win_amd64.whl"],
        "has_sdist": False,
    }
    (c,) = check_version("1.0", release, [(3, 11)])
    assert c.verdict == NO_WHEEL


def test_unparseable_requires_python_is_unknown_not_pass():
    release = {
        "requires_python": "garbage-spec",
        "wheels": ["pkg-1.0-py3-none-any.whl"],
        "has_sdist": False,
    }
    (c,) = check_version("1.0", release, [(3, 11)])
    assert c.verdict == UNKNOWN_METADATA
    assert "garbage-spec" in c.detail
    # could not verify: a problem, never a pass
    assert has_problems([c])


def test_expected_python_scopes_blocked_verdicts():
    # Source declares >=3.11 (the Apple case): 3.10 blocked is not a bug.
    release = {
        "requires_python": ">=3.14",
        "wheels": ["pkg-1.0-py3-none-any.whl"],
        "has_sdist": False,
    }
    results = check_version("1.0", release, [(3, 10), (3, 11)], expected_python=">=3.11")
    by_py = {(c.python[0], c.python[1]): c for c in results}
    assert by_py[(3, 10)].verdict == OUT_OF_SCOPE
    assert by_py[(3, 11)].verdict == BLOCKED_BY_REQUIRES_PYTHON
    assert has_problems(results)
    # without expected_python, 3.10 blocked still counts (signal, not scoped)
    (c10,) = check_version("1.0", release, [(3, 10)])
    assert c10.verdict == BLOCKED_BY_REQUIRES_PYTHON


def test_ignore_skips_version():
    release = {"requires_python": ">=3.9", "wheels": [], "has_sdist": False}
    results = check_package({"1.0": release}, ["1.0"], [(3, 11)], ignore=["1.0"])
    assert results[0].verdict == IGNORED
    assert not has_problems(results)


def test_only_checks_single_version():
    rel = lambda: {"requires_python": ">=3.9", "wheels": ["p-1-py3-none-any.whl"], "has_sdist": False}
    results = check_package({"1.0": rel(), "2.0": rel()}, ["1.0", "2.0"], [(3, 11)], only="2.0")
    assert {c.version for c in results} == {"2.0"}


def test_limit_applies_to_all_mode():
    rel = lambda: {"requires_python": ">=3.9", "wheels": ["p-1-py3-none-any.whl"], "has_sdist": False}
    releases = {f"{i}.0": rel() for i in range(1, 6)}
    results = check_package(releases, list(releases), [(3, 11)], limit=2)
    assert sorted({c.version for c in results}) == ["4.0", "5.0"]
