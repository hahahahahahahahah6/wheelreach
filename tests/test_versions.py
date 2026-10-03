"""Tests for version sorting and python-set parsing."""
import pytest

from wheelreach.versions import parse_python_set, sort_versions_newest_first


def test_sort_newest_first():
    assert sort_versions_newest_first(["1.0", "2.0", "1.10"]) == ["2.0", "1.10", "1.0"]


def test_parse_python_set():
    assert parse_python_set("3.11") == [(3, 11)]
    assert parse_python_set("3.10, 3.12") == [(3, 10), (3, 12)]


def test_parse_python_set_rejects_garbage():
    with pytest.raises(ValueError):
        parse_python_set("banana")
    with pytest.raises(ValueError):
        parse_python_set("")
