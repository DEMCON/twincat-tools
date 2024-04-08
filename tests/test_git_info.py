import pytest
import subprocess
import sys
from pathlib import Path
import re

import tctools.git_info
from tctools.git_info_class import GitInfo


def test_help(capsys):
    """Test the help text."""
    with pytest.raises(SystemExit) as err:
        tctools.git_info.main("--help")

    assert err.type == SystemExit

    message = capsys.readouterr().out
    assert "usage:" in message


def test_cli(plc_code, capsys):
    """Test the CLI hook works."""
    file = (
        plc_code / "TwinCAT Project1" / "MyPlc" / "GVLs" / "GVL_Version.TcGVL.template"
    )

    current_dir = Path(__file__).parent  # Repurpose this package repo

    path = sys.executable  # Re-use whatever executable we're using now
    result = subprocess.run(
        [path, "-m", "tctools.git_info", str(file), "--repo", current_dir],
        capture_output=True,
    )

    assert result.returncode == 0
    new_file = plc_code / "TwinCAT Project1" / "MyPlc" / "GVLs" / "GVL_Version.TcGVL"
    assert new_file.is_file()


def test_version_making(plc_code):
    """Test git insertions."""
    file = (
        plc_code / "TwinCAT Project1" / "MyPlc" / "GVLs" / "GVL_Version.TcGVL.template"
    )

    current_dir = Path(__file__).parent  # Repurpose this package repo

    info = GitInfo(str(file), "--repo", str(current_dir))
    info.run()

    new_file = plc_code / "TwinCAT Project1" / "MyPlc" / "GVLs" / "GVL_Version.TcGVL"
    assert new_file.is_file()

    re_tag = re.compile(r"{{\w+}}")
    result = re_tag.search(new_file.read_text())
    assert not result  # Make sure not tags remain


def test_empty_git(plc_code):
    """Test versioning when the git repo is entirely empty."""

    result = subprocess.run(
        ["git", "init"],
        cwd=str(plc_code),
    )
    assert result.returncode == 0 and "Failed initialize repo for test"

    file = (
        plc_code / "TwinCAT Project1" / "MyPlc" / "GVLs" / "GVL_Version.TcGVL.template"
    )

    info = GitInfo(str(file))
    info.run()

    new_file = plc_code / "TwinCAT Project1" / "MyPlc" / "GVLs" / "GVL_Version.TcGVL"
    assert new_file.is_file()

    re_tag = re.compile(r"{{\w+}}")
    result = re_tag.search(new_file.read_text())
    assert not result  # Make sure not tags remain
