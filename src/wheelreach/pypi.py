"""Fetch PyPI release metadata (stdlib only)."""
from __future__ import annotations

import json

from .http import FetchError, fetch


def fetch_pypi_info(name: str, get=fetch) -> dict:
    """Return {'versions': [...], 'releases': {version: {...}}} for a package.

    Per version: {'requires_python': str|None, 'wheels': [filenames],
    'has_sdist': bool}. Raises FetchError when the package is missing or the
    fetch fails.
    """
    url = f"https://pypi.org/pypi/{name}/json"
    try:
        body, _ = get(url)
    except FetchError as exc:
        if "HTTP 404" in str(exc):
            raise FetchError(f"package {name!r} not found on PyPI") from exc
        raise
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise FetchError(f"GET {url}: invalid JSON: {exc}") from exc
    info = data.get("info") or {}
    releases = data.get("releases") or {}
    out: dict = {"versions": [], "releases": {}}
    for version, files in releases.items():
        if not isinstance(files, list):
            continue
        wheels: list[str] = []
        has_sdist = False
        for entry in files:
            if not isinstance(entry, dict):
                continue
            fn = entry.get("filename") or ""
            pt = entry.get("packagetype")
            if pt == "bdist_wheel" and fn.endswith(".whl"):
                wheels.append(fn)
            elif pt == "sdist":
                has_sdist = True
        out["versions"].append(version)
        out["releases"][version] = {
            "requires_python": info.get("requires_python"),
            "wheels": wheels,
            "has_sdist": has_sdist,
        }
    # Per-file requires_python overrides the release-level one when present.
    for version, files in releases.items():
        if not isinstance(files, list):
            continue
        per_file = {
            entry["filename"]: entry.get("requires_python")
            for entry in files
            if isinstance(entry, dict) and entry.get("requires_python")
        }
        if per_file:
            out["releases"][version]["wheel_requires_python"] = per_file
    return out


def latest_version(versions: list[str]) -> str | None:
    """Newest version, preferring stable releases over pre-releases."""
    from .versions import sort_versions_newest_first

    ordered = sort_versions_newest_first(versions)
    for v in ordered:
        lv = v.lower()
        if not any(t in lv for t in ("a", "b", "rc", "dev", "alpha", "beta", "pre")):
            return v
    return ordered[0] if ordered else None
