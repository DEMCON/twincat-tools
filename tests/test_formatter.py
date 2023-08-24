import pytest

import tctools.format

from .conftest import assert_warnings


def test_help(capsys):
    """Test the help text."""

    with pytest.raises(SystemExit) as err:
        tctools.format.main("--help")

    assert err.type == SystemExit

    message = capsys.readouterr().out
    assert "usage:" in message and "options:" in message


def test_check_no_tab_char(plc_code, capsys):
    """Test finding illegal tab characters."""
    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text("""root = true
[*.TcPOU]
indent_style = space
indent_size = 4
""")
    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Example.TcPOU"
    tctools.format.main(str(file))

    expected = {
        "Line contains tab character": {
            "FB_Example.TcPOU": {
                "declaration": [3, 10],
                "implementation": [2, 4, 5, 12],
            }
        }
    }

    result = capsys.readouterr().out.split("\n")
    assert_warnings(expected, result)


def test_check_tab_spaces(plc_code, capsys):
    """Test finding illegal spaces."""
    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text("""root = true
[*.TcPOU]
indent_style = tab
indent_size = 4
""")
    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Example.TcPOU"
    tctools.format.main(str(file))

    expected = {
        "Line contains indent that should be a tab": {
            "FB_Example.TcPOU": {
                "declaration": [3, 4, 9],
                "implementation": [3, 4, 9],
            }
        }
    }

    result = capsys.readouterr().out.split("\n")
    assert_warnings(expected, result)


def test_check_trailing_ws(plc_code, capsys):
    """Test finding illegal ws."""
    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text("""root = true
[*.TcPOU]
trim_trailing_whitespace = true
""")
    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Example.TcPOU"
    tctools.format.main(str(file))

    expected = {
        "Line contains trailing whitespace": {
            "FB_Example.TcPOU": {
                "implementation": [2, 9, 12],
            }
        }
    }

    result = capsys.readouterr().out.split("\n")
    assert_warnings(expected, result)
