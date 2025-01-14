# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

# Learn more about testing at: https://juju.is/docs/sdk/testing

# pylint: disable=duplicate-code,missing-function-docstring
"""Unit tests snap module."""

import io
import unittest.mock as mock
from pathlib import Path

import pytest
import snap


@mock.patch("pathlib.Path.exists", mock.Mock(return_value=False))
def test_parse_no_file():
    """Test no file exists."""
    with pytest.raises(snap.snap_lib.SnapError):
        snap._parse_management_arguments()


@mock.patch("pathlib.Path.exists", mock.Mock(return_value=True))
@mock.patch("pathlib.Path.open")
def test_parse_invalid_file(mock_open):
    """Test file is invalid."""
    mock_open().__enter__.return_value = io.StringIO("example: =")
    with pytest.raises(snap.snap_lib.SnapError):
        snap._parse_management_arguments()


@mock.patch("pathlib.Path.exists", mock.Mock(return_value=True))
@mock.patch("pathlib.Path.open")
@mock.patch("subprocess.check_output")
def test_parse_invalid_arch(mock_checkoutput, mock_open):
    """Test file has invalid arch."""
    mock_open().__enter__.return_value = io.StringIO("{}")
    mock_checkoutput().decode.return_value = "amd64"
    with pytest.raises(snap.snap_lib.SnapError):
        snap._parse_management_arguments()


@mock.patch("pathlib.Path.exists", mock.Mock(return_value=True))
@mock.patch("pathlib.Path.open")
@mock.patch("subprocess.check_output")
def test_parse_validation_error(mock_checkoutput, mock_open):
    """Test file cannot be parsed."""
    mock_open().__enter__.return_value = io.StringIO("amd64:\n- {}")
    mock_checkoutput().decode.return_value = "amd64"
    with pytest.raises(snap.snap_lib.SnapError):
        snap._parse_management_arguments()


@mock.patch("pathlib.Path.exists", mock.Mock(return_value=True))
@mock.patch("pathlib.Path.open")
@mock.patch("subprocess.check_output")
def test_parse_valid_store(mock_checkoutput, mock_open):
    """Test file parses as store content."""
    content = """
amd64:
- install-type: store
  name: k8s
  channel: edge
"""
    mock_open().__enter__.return_value = io.StringIO(content)
    mock_checkoutput().decode.return_value = "amd64"
    args = snap._parse_management_arguments()
    assert args == [
        snap.SnapStoreArgument(name="k8s", channel="edge"),
    ]


@mock.patch("pathlib.Path.exists", mock.Mock(return_value=True))
@mock.patch("pathlib.Path.open")
@mock.patch("subprocess.check_output")
def test_parse_valid_file(mock_checkoutput, mock_open):
    """Test file parses as file content."""
    content = """
amd64:
- install-type: file
  name: k8s
  filename: path/to/thing
"""
    mock_open().__enter__.return_value = io.StringIO(content)
    mock_checkoutput().decode.return_value = "amd64"
    args = snap._parse_management_arguments()
    assert args == [
        snap.SnapFileArgument(name="k8s", filename=Path("path/to/thing")),
    ]


@mock.patch("snap._parse_management_arguments")
@mock.patch("snap.snap_lib.install_local")
@mock.patch("snap.snap_lib.SnapCache")
def test_management_installs_local(cache, install_local, args):
    """Test installer uses local installer."""
    cache.return_value.__getitem__.return_value = mock.MagicMock(spec=snap.snap_lib.Snap)
    args.return_value = [
        snap.SnapFileArgument(name="k8s", filename=Path("path/to/thing")),
    ]
    snap.management()
    cache.called_once_with()
    cache["k8s"].ensure.assert_not_called()
    install_local.assert_called_once_with(filename=Path("path/to/thing"))


@mock.patch("snap._parse_management_arguments")
@mock.patch("snap.snap_lib.install_local")
@mock.patch("snap.snap_lib.SnapCache")
def test_management_installs_store(cache, install_local, args):
    """Test installer uses store installer."""
    cache.return_value.__getitem__.return_value = mock.MagicMock(spec=snap.snap_lib.Snap)
    args.return_value = [
        snap.SnapStoreArgument(name="k8s", channel="edge"),
    ]
    snap.management()
    cache.called_once_with()
    install_local.assert_not_called()
    cache()["k8s"].ensure.assert_called_once_with(
        state=snap.snap_lib.SnapState.Present, channel="edge"
    )
