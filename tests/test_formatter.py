import pytest

import tctools


def test_help(capsys):
    """Test the help text."""

    with pytest.raises(SystemExit) as err:
        tctools.format_main("--help")

    assert err.type == SystemExit

    message = capsys.readouterr().out
    assert "usage:" in message and "--project" in message
