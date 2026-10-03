"""Tests for PyPI metadata fetching."""
import json

import pytest

from wheelreach.http import FetchError
from wheelreach.pypi import fetch_pypi_info, latest_version


def fake_get(payload, fail=None):
    def _get(url):
        if fail == "404":
            raise FetchError("GET x: HTTP 404")
        if fail == "net":
            raise FetchError("GET x: network error")
        return json.dumps(payload).encode(), {}
    return _get


PAYLOAD = {
    "info": {"requires_python": ">=3.9"},
    "releases": {
        "2.0": [
            {"packagetype": "bdist_wheel", "filename": "p-2.0-py3-none-any.whl",
             "url": "u", "requires_python": ">=3.10"},
            {"packagetype": "sdist", "filename": "p-2.0.tar.gz", "url": "u2"},
        ],
        "1.0": [],
    },
}


def test_parses_releases():
    info = fetch_pypi_info("p", get=fake_get(PAYLOAD))
    assert info["releases"]["2.0"]["wheels"] == ["p-2.0-py3-none-any.whl"]
    assert info["releases"]["2.0"]["has_sdist"] is True
    assert info["releases"]["2.0"]["wheel_requires_python"] == {
        "p-2.0-py3-none-any.whl": ">=3.10"}
    assert info["releases"]["1.0"]["wheels"] == []


def test_404_becomes_not_found():
    with pytest.raises(FetchError, match="not found on PyPI"):
        fetch_pypi_info("nope", get=fake_get({}, fail="404"))


def test_network_error_propagates():
    with pytest.raises(FetchError):
        fetch_pypi_info("p", get=fake_get({}, fail="net"))


def test_latest_version_prefers_stable():
    assert latest_version(["1.0", "2.0b1", "1.5"]) == "1.5"
    assert latest_version([]) is None
