"""Tests for [tool.wheelreach] config loading."""
from wheelreach.config import load_config_file, merge_config


def test_load_config(tmp_path):
    p = tmp_path / "pyproject.toml"
    p.write_text('[tool.wheelreach]\npython_set = "3.11,3.12"\nignore = ["0.1a1"]\n')
    cfg = load_config_file(str(p))
    assert cfg["python_set"] == "3.11,3.12"
    assert cfg["ignore"] == ["0.1a1"]


def test_missing_file_gives_defaults(tmp_path):
    cfg = load_config_file(str(tmp_path / "nope.toml"))
    assert cfg == {"python_set": None, "ignore": []}


def test_cli_overrides_file():
    merged = merge_config({"python_set": "3.10", "ignore": ["a"]}, "3.11", ["b"])
    assert merged["python_set"] == "3.11"
    assert merged["ignore"] == ["b", "a"]
