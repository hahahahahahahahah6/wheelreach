"""Load [tool.wheelreach] config from pyproject.toml (stdlib only)."""
from __future__ import annotations

import os

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None  # type: ignore[assignment]


def find_default_config() -> str | None:
    path = os.path.join(os.getcwd(), "pyproject.toml")
    return path if os.path.isfile(path) else None


def load_config_file(path: str) -> dict:
    """Return {'python_set': str|None, 'ignore': [...]} from [tool.wheelreach]."""
    cfg: dict = {"python_set": None, "ignore": []}
    if tomllib is None:
        return cfg
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, ValueError):
        return cfg
    tool = data.get("tool", {}).get("wheelreach", {})
    if isinstance(tool, dict):
        if isinstance(tool.get("python_set"), str):
            cfg["python_set"] = tool["python_set"]
        if isinstance(tool.get("ignore"), list):
            cfg["ignore"] = [str(v) for v in tool["ignore"]]
    return cfg


def merge_config(file_config: dict, cli_python_set: str | None, cli_ignore: list) -> dict:
    return {
        "python_set": cli_python_set or file_config.get("python_set"),
        "ignore": list(cli_ignore) + list(file_config.get("ignore") or []),
    }
