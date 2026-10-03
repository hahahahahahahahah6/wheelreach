"""Tests for Requires-Python specifier evaluation."""
import pytest

from wheelreach.specifier import allows


@pytest.mark.parametrize("spec,major,minor,expected", [
    (None, 3, 11, True),
    ("", 3, 11, True),
    (">=3.9", 3, 9, True),
    (">=3.9", 3, 8, False),
    (">=3.14", 3, 14, True),
    (">=3.14", 3, 11, False),   # coreai-models: wheel blocks 3.11
    (">=3.14", 3, 12, False),
    (">3.10", 3, 10, False),
    (">3.10", 3, 11, True),
    ("<3.15", 3, 15, False),    # triton nightly: cp315 wheel, metadata <3.15
    ("<3.15", 3, 14, True),
    ("<=3.12", 3, 12, True),
    ("<=3.12", 3, 13, False),
    (">=3.10,<3.15", 3, 14, True),
    (">=3.10,<3.15", 3, 15, False),
    (">=3.10,<3.15", 3, 9, False),
    ("==3.11", 3, 11, True),
    ("==3.11", 3, 12, False),
    ("==3.11.*", 3, 11, True),
    ("==3.11.*", 3, 12, False),
    ("!=3.12.*", 3, 12, False),
    ("!=3.12.*", 3, 11, True),
    ("~=3.11", 3, 11, True),
    ("~=3.11", 3, 14, True),
    ("~=3.11", 3, 10, False),
    (">=3.8", 3, 14, True),     # upper unbounded: future Pythons allowed
])
def test_allows(spec, major, minor, expected):
    assert allows(spec, major, minor) is expected


def test_garbage_raises():
    with pytest.raises(ValueError):
        allows("banana", 3, 11)
    with pytest.raises(ValueError):
        allows("=>3.11", 3, 11)
