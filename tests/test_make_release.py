import pytest
import sys
import os
import subprocess

import tctools.make_release
from tctools.make_release_class import MakeRelease


VERSION = "v1.2.3"


@pytest.fixture()
def mock_git(mocker, plc_code, monkeypatch):
    """Mock ``git.Repo`` to not throw an error and return info."""
    # Mock the `Repo` class
    mocked_repo = mocker.patch("tctools.make_release_class.Repo")
    # Mock `git.tag()` from a mocked Repo instance:
    mocked_repo().git.tag.return_value = VERSION

    # Patch the CWD:
    monkeypatch.setenv("PATH", str(plc_code), prepend=os.pathsep)
    monkeypatch.chdir(plc_code)


def test_help(capsys):
    with pytest.raises(SystemExit) as err:
        tctools.make_release.main("--help")

    assert err.type == SystemExit

    message = capsys.readouterr().out
    assert "usage: " in message


def test_cli(plc_code, capsys):
    """Test the CLI hook works."""

    path = sys.executable  # Re-use whatever executable we're using now
    result = subprocess.run(
        [path, "-m", "tctools.make_release", "--help"],
        capture_output=True,
    )

    assert result.returncode == 0


def test_release(plc_code, caplog, mock_git):
    """Test the release feature."""

    src_dir = plc_code / "TwinCAT Release"

    releaser = MakeRelease(str(src_dir))
    releaser.run()

    archive = plc_code / "deploy" / f"name_{VERSION}.zip"
    assert archive.is_file()
