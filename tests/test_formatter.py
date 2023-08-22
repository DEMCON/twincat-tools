import pytest

import tctools.format


def test_help(capsys):
    """Test the help text."""

    with pytest.raises(SystemExit) as err:
        tctools.format.main("--help")

    assert err.type == SystemExit

    message = capsys.readouterr().out
    assert "usage:" in message and "options:" in message
