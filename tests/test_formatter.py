import pytest

import tctools.format

from .conftest import assert_strings_have_substrings


def test_help(capsys):
    """Test the help text."""

    with pytest.raises(SystemExit) as err:
        tctools.format.main("--help")

    assert err.type == SystemExit

    message = capsys.readouterr().out
    assert "usage:" in message and "options:" in message


def test_dry_no_tab_char(plc_code, capsys):
    """Test finding illegal tab characters."""
    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text(
        """root = true
[*.TcPOU]
indent_style = space
indent_size = 4
"""
    )
    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Example.TcPOU"
    content_before = file.read_text()

    tctools.format.main(str(file), "--dry")

    # fmt: off
    expected = [
        ["FB_Example.TcPOU", "declaration", ":3", "Line contains a tab that should be spaces"],
        ["FB_Example.TcPOU", "declaration", ":10", "Line contains a tab that should be spaces"],
        ["FB_Example.TcPOU", "implementation", ":2", "Line contains a tab that should be spaces"],
        ["FB_Example.TcPOU", "implementation", ":4", "Line contains a tab that should be spaces"],
        ["FB_Example.TcPOU", "implementation", ":5", "Line contains a tab that should be spaces"],
        ["FB_Example.TcPOU", "implementation", ":12", "Line contains a tab that should be spaces"],
    ]
    # fmt: on

    result = capsys.readouterr().out.split("\n")
    assert_strings_have_substrings(expected, result)
    assert content_before == file.read_text() and "Source file was modified"


def test_dry_tab_spaces(plc_code, capsys):
    """Test finding illegal spaces."""
    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text(
        """root = true
[*.TcPOU]
indent_style = tab
indent_size = 4
"""
    )
    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Example.TcPOU"
    tctools.format.main(str(file), "--dry")

    # fmt: off
    expected = [
        ["FB_Example.TcPOU", "declaration", ":3", "Line contains an indent that should be a tab"],
        ["FB_Example.TcPOU", "declaration", ":4", "Line contains an indent that should be a tab"],
        ["FB_Example.TcPOU", "declaration", ":9", "Line contains an indent that should be a tab"],
        ["FB_Example.TcPOU", "implementation", ":3", "Line contains an indent that should be a tab"],
        ["FB_Example.TcPOU", "implementation", ":4", "Line contains an indent that should be a tab"],
        ["FB_Example.TcPOU", "implementation", ":9", "Line contains an indent that should be a tab"],
    ]
    # fmt: on

    result = capsys.readouterr().out.split("\n")
    assert_strings_have_substrings(expected, result)


def test_dry_trailing_ws(plc_code, capsys):
    """Test finding illegal ws."""
    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text(
        """root = true
[*.TcPOU]
trim_trailing_whitespace = true
"""
    )
    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Example.TcPOU"
    tctools.format.main(str(file), "--dry")

    # fmt: off
    expected = [
        ["FB_Example.TcPOU", "implementation", ":2", "Line contains trailing whitespace"],
        ["FB_Example.TcPOU", "implementation", ":9", "Line contains trailing whitespace"],
        ["FB_Example.TcPOU", "implementation", ":12", "Line contains trailing whitespace"],
    ]
    # fmt: on

    result = capsys.readouterr().out.split("\n")
    assert_strings_have_substrings(expected, result)


def test_check(plc_code, capsys):
    """Test `check` flag for formatter."""
    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text(
        """root = true
[*.TcPOU]
indent_style = space
indent_size = 4
"""
    )
    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Example.TcPOU"

    content_before = file.read_text()

    code = tctools.format.main(str(file), "--check")
    assert code != 0

    assert content_before == file.read_text()

    tctools.format.main(str(file))  # Re-format
    code_new = tctools.format.main(str(file), "--check")  # Check again
    assert code_new == 0


def test_reformat_resave(plc_code):
    """Test reformatting, making sure the XML remains untouched."""
    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text(
        """root = true
[*.TcPOU]
indent_style = space
indent_size = 4
"""
    )
    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Example.TcPOU"

    content_before = file.read_text()

    tctools.format.main(str(file))

    content_after = file.read_text()

    # Make sure the XML bits are the same
    assert content_after[:243] == content_before[:243]
    assert content_after[-54:] == content_before[-54:]

    assert content_after != content_before


def test_reformat_no_tab_char(plc_code):
    """Test reformatting for illegal tab characters."""
    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text(
        """root = true
[*.TcPOU]
indent_style = space
indent_size = 4
"""
    )
    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Example.TcPOU"

    tctools.format.main(str(file))

    content_after = file.read_text()
    assert "\t" not in content_after
