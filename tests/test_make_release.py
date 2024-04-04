import pytest
import sys
import subprocess

import tctools.make_release
from tctools.make_release_class import MakeRelease


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
