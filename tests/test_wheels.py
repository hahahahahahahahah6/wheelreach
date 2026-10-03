"""Tests for wheel filename parsing and interpreter compatibility."""
import pytest

from wheelreach.wheels import compatible_wheels, parse_wheel_filename, wheel_supports


def p(fn, major=3, minor=11):
    parsed = parse_wheel_filename(fn)
    assert parsed is not None
    return wheel_supports(parsed, major, minor)


def test_pure_python_wheel_matches_everything():
    assert p("coreai_models-0.1.0-py3-none-any.whl", 3, 11)
    assert p("coreai_models-0.1.0-py3-none-any.whl", 3, 14)


def test_cp_specific_wheel_matches_exact():
    assert p("pkg-1.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl", 3, 11)
    assert not p("pkg-1.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl", 3, 12)


def test_multi_python_tag():
    fn = "pkg-1.0-cp310.cp311.cp312-cp310.cp311.cp312-manylinux_2_17_x86_64.whl"
    assert p(fn, 3, 10)
    assert p(fn, 3, 12)
    assert not p(fn, 3, 13)


def test_abi3_forward_compatible():
    fn = "pkg-1.0-cp39-abi3-manylinux_2_17_x86_64.whl"
    assert p(fn, 3, 11)
    assert p(fn, 3, 14)
    assert not p(fn, 3, 8)


def test_triton_cp315_wheel_matches_cp315():
    fn = "triton-3.7.0+git88b227e2-cp315-cp315-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl"
    assert p(fn, 3, 15)
    assert not p(fn, 3, 14)


def test_wrong_platform_rejected():
    assert not p("pkg-1.0-cp311-cp311-win_amd64.whl", 3, 11)
    assert not p("pkg-1.0-cp311-cp311-macosx_11_0_arm64.whl", 3, 11)
    assert not p("pkg-1.0-cp311-cp311-manylinux_2_17_aarch64.whl", 3, 11)


def test_musllinux_accepted():
    assert p("pkg-1.0-cp311-cp311-musllinux_1_2_x86_64.whl", 3, 11)


def test_unparseable_filename_ignored():
    assert parse_wheel_filename("notawheel.zip") is None
    assert parse_wheel_filename("pkg-1.0.whl") is None
    assert compatible_wheels(["garbage.txt"], 3, 11) == []


def test_compatible_wheels_filters():
    files = [
        "pkg-1.0-cp310-cp310-manylinux_2_17_x86_64.whl",
        "pkg-1.0-cp311-cp311-manylinux_2_17_x86_64.whl",
        "pkg-1.0-cp311-cp311-win_amd64.whl",
    ]
    assert compatible_wheels(files, 3, 11) == [files[1]]
