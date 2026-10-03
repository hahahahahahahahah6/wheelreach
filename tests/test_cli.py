"""Tests for the CLI: exit codes, formats, argument validation."""
import json

import wheelreach.cli as cli_mod
from wheelreach.cli import main

CLEAN_RELEASE = {
    "requires_python": ">=3.9",
    "wheels": ["demo_pkg-1.0-py3-none-any.whl"],
    "has_sdist": True,
}
CLEAN_INFO = {"versions": ["1.0"], "releases": {"1.0": CLEAN_RELEASE}}


def patch_pypi(monkeypatch, info, fail=False):
    def _pypi(name):
        if fail:
            from wheelreach.http import FetchError
            raise FetchError("boom")
        return info
    monkeypatch.setattr(cli_mod, "fetch_pypi_info", _pypi)


def base_args(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # keep config discovery away from real cwd
    return ["check", "--package", "demo-pkg"]


def test_exit_0_when_clean(monkeypatch, tmp_path, capsys):
    patch_pypi(monkeypatch, CLEAN_INFO)
    assert main(base_args(monkeypatch, tmp_path) + ["--python", "3.11"]) == 0
    assert "0 problem" in capsys.readouterr().out


def test_exit_1_when_blocked(monkeypatch, tmp_path, capsys):
    blocked = dict(CLEAN_RELEASE, requires_python=">=3.14")
    patch_pypi(monkeypatch, {"versions": ["1.0"], "releases": {"1.0": blocked}})
    assert main(base_args(monkeypatch, tmp_path) + ["--python", "3.11"]) == 1
    out = capsys.readouterr().out
    assert "BLOCKED_BY_REQUIRES_PYTHON" in out


def test_exit_2_on_pypi_failure(monkeypatch, tmp_path):
    patch_pypi(monkeypatch, CLEAN_INFO, fail=True)
    assert main(base_args(monkeypatch, tmp_path)) == 2


def test_exit_2_on_unknown_version(monkeypatch, tmp_path):
    patch_pypi(monkeypatch, CLEAN_INFO)
    assert main(base_args(monkeypatch, tmp_path) + ["--version", "9.9"]) == 2


def test_exit_2_on_bad_python(monkeypatch, tmp_path):
    patch_pypi(monkeypatch, CLEAN_INFO)
    assert main(base_args(monkeypatch, tmp_path) + ["--python", "banana"]) == 2


def test_bad_expected_python_is_exit_2(monkeypatch, tmp_path, capsys):
    patch_pypi(monkeypatch, CLEAN_INFO)
    assert main(base_args(monkeypatch, tmp_path) + ["--expected-python", "garbage"]) == 2
    assert "expected-python" in capsys.readouterr().err


def test_expected_python_scopes_cli(monkeypatch, tmp_path, capsys):
    info = {"versions": ["1.0"],
            "releases": {"1.0": {"requires_python": ">=3.14",
                                 "wheels": ["p-1-py3-none-any.whl"],
                                 "has_sdist": False}}}
    patch_pypi(monkeypatch, info)
    args = base_args(monkeypatch, tmp_path) + ["--python-set", "3.10,3.11",
                                               "--expected-python", ">=3.11"]
    assert main(args) == 1
    out = capsys.readouterr().out
    assert "OUT_OF_SCOPE" in out
    assert "BLOCKED_BY_REQUIRES_PYTHON" in out


def test_json_format_shape(monkeypatch, tmp_path, capsys):
    patch_pypi(monkeypatch, CLEAN_INFO)
    assert main(base_args(monkeypatch, tmp_path) + ["--python", "3.11", "--format", "json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["verdict"] == "WHEEL_ELIGIBLE"
    assert rows[0]["python"] == "3.11"


def test_version_flag_selects_one(monkeypatch, tmp_path, capsys):
    info = {"versions": ["1.0", "2.0"],
            "releases": {"1.0": CLEAN_RELEASE, "2.0": CLEAN_RELEASE}}
    patch_pypi(monkeypatch, info)
    assert main(base_args(monkeypatch, tmp_path) + ["--version", "1.0", "--python", "3.11"]) == 0
    out = capsys.readouterr().out
    assert "1.0" in out and "2.0" not in out.splitlines()[2]


def test_version_flag(capsys):
    with __import__("pytest").raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "wheelreach" in capsys.readouterr().out
