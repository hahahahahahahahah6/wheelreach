# wheelreach

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![No dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](pyproject.toml)

**Apple published a wheel your Python can't install — and their own source says it should work.**

Real case, still live: [`coreai-models==0.1.0`](https://github.com/apple/coreai-models/issues/96).
The wheel on PyPI declares `Requires-Python: >=3.14`, but the repo's
`python/pyproject.toml` says `requires-python = ">=3.11"` and `.python-version`
pins 3.11. Anyone on Python 3.11 or 3.12 gets a resolution failure for a
package the source claims to support. (Verified against the live PyPI JSON API.)

A second flavor of the same disease:
[pytorch/pytorch#186099](https://github.com/pytorch/pytorch/issues/186099) —
triton nightly wheels are built with `cp315` tags, but their `METADATA` still
says `Requires-Python: >=3.10,<3.15`, so pip rejects them on Python 3.15.

wheelreach checks that a package's *declared* Python support actually has
*installable* release files — the release-integrity question nobody's CI asks.

Part of the release-integrity series:
[readmeta](https://github.com/hahahahahahahahah6/readmeta) (did your README
render?), [wheeltruth](https://github.com/hahahahahahahahah6/wheeltruth) (did
your wheel ship complete?), [casecrash](https://github.com/hahahahahahahahah6/casecrash)
(will your filenames survive checkout?),
[tagtruth](https://github.com/hahahahahahahahah6/tagtruth) (does the tag match
the release?), wheelreach (can your Python actually install it?).

## Quickstart

```bash
pip install wheelreach
wheelreach check --package coreai-models
```

```
version  python  verdict                     wheel
-------  ------  --------------------------  ------------------------------------
0.1.0    3.10    BLOCKED_BY_REQUIRES_PYTHON  coreai_models-0.1.0-py3-none-any.whl
0.1.0    3.11    BLOCKED_BY_REQUIRES_PYTHON  coreai_models-0.1.0-py3-none-any.whl
0.1.0    3.12    BLOCKED_BY_REQUIRES_PYTHON  coreai_models-0.1.0-py3-none-any.whl
0.1.0    3.13    BLOCKED_BY_REQUIRES_PYTHON  coreai_models-0.1.0-py3-none-any.whl
0.1.0    3.14    INSTALLABLE                 coreai_models-0.1.0-py3-none-any.whl

checked 5 version/python pairs, 4 problem(s): 0.1.0 on 3.10 (BLOCKED_BY_REQUIRES_PYTHON), ...
  0.1.0 / 3.11: wheel coreai_models-0.1.0-py3-none-any.whl exists for cp311 but Requires-Python '>=3.14' excludes Python 3.11
```

Exit codes: `0` clean, `1` problems found, `2` errors (fetch failures, bad args).

## Verdicts

| Verdict | Meaning |
|---|---|
| `INSTALLABLE` | a compatible wheel exists and metadata allows this Python |
| `BLOCKED_BY_REQUIRES_PYTHON` | a wheel exists for this Python but `Requires-Python` excludes it |
| `NO_WHEEL` | no compatible wheel and no sdist published |
| `NO_WHEEL_HAS_SDIST` | no compatible wheel, but an sdist exists that might build |

The `NO_WHEEL` / `NO_WHEEL_HAS_SDIST` split is deliberate: "no wheel" and
"nothing installable at all" are different severities, and a checker that
conflates them cries wolf on every sdist-only package.

Options:

```bash
wheelreach check --package <name> --version 1.2.3   # one version (default: latest stable)
wheelreach check --package <name> --all             # every published version
wheelreach check --package <name> --python 3.11     # single target Python
wheelreach check --package <name> --python-set 3.11,3.12
wheelreach check --package <name> --format json
```

Config file (`pyproject.toml`):

```toml
[tool.wheelreach]
python_set = "3.11,3.12"
ignore = ["2.0a1"]
```

## What wheelreach does not verify

The target model is CPython on Linux x86-64 — the most common CI/server
shape. macOS, Windows, ARM, and alternative interpreters are out of scope for
v0.1.0. Wheel-tag compatibility is syntactic (filename tags + metadata), not a
trial install: a passing check means pip *should* accept the file, not that the
code runs. `Requires-Python` clauses beyond `==/!=/>=/<=/>/</~=` (with optional
`.*` wildcards) raise an error rather than guessing.
