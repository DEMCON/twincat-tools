import subprocess
import sys

import pytest

import tctools.format.__main__
from tctools.format.format_class import Formatter

from .conftest import assert_strings_have_substrings


def test_help(capsys):
    """Test the help text."""
    with pytest.raises(SystemExit) as err:
        tctools.format.__main__.main("--help")

    assert err.type == SystemExit

    message = capsys.readouterr().out
    assert "usage:" in message


def test_cli(plc_code, capsys):
    """Test the CLI hook works."""
    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text(
        """root = true
[*.TcPOU]
indent_style = space
indent_size = 4
"""
    )
    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Example.TcPOU"

    path = sys.executable  # Re-use whatever executable we're using now
    result = subprocess.run(
        [path, "-m", "tctools.format", str(file)], capture_output=True
    )

    assert result.returncode == 0
    assert "Re-saved 1 path" in result.stdout.decode()


def test_dry_no_tab_char(plc_code, caplog):
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

    formatter = Formatter(str(file), "--dry", "-l", "DEBUG")
    formatter.run()

    txt = "Line contains a tab that should be spaces"
    expected = [
        ["Processing path"],
        ["FB_Example.TcPOU", "declaration", ":3", txt],
        ["FB_Example.TcPOU", "declaration", ":10", txt],
        ["FB_Example.TcPOU", "implementation", ":2", txt],
        ["FB_Example.TcPOU", "implementation", ":4", txt],
        ["FB_Example.TcPOU", "implementation", ":5", txt],
        ["FB_Example.TcPOU", "implementation", ":12", txt],
        ["Checked 1 path(s)"],
        ["Re-saved 0 path(s)"],
    ]

    assert_strings_have_substrings(expected, caplog.messages)
    assert content_before == file.read_text() and "Source file was modified"


def test_dry_tab_spaces(plc_code, caplog):
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

    formatter = Formatter(str(file), "--dry", "-l", "DEBUG")
    formatter.run()

    txt = "Line contains an indent that should be a tab"
    expected = [
        ["Processing path"],
        ["FB_Example.TcPOU", "declaration", ":3", txt],
        ["FB_Example.TcPOU", "declaration", ":4", txt],
        ["FB_Example.TcPOU", "declaration", ":9", txt],
        ["FB_Example.TcPOU", "implementation", ":3", txt],
        ["FB_Example.TcPOU", "implementation", ":4", txt],
        ["FB_Example.TcPOU", "implementation", ":9", txt],
        ["Checked 1 path(s)"],
        ["Re-saved 0 path(s)"],
    ]

    assert_strings_have_substrings(expected, caplog.messages)


def test_dry_trailing_ws(plc_code, caplog):
    """Test finding illegal ws."""
    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text(
        """root = true
[*.TcPOU]
trim_trailing_whitespace = true
"""
    )
    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Example.TcPOU"

    formatter = Formatter(str(file), "--dry", "-l", "DEBUG")
    formatter.run()

    txt = "Line contains trailing whitespace"
    expected = [
        ["Processing path"],
        ["FB_Example.TcPOU", "implementation", ":2", txt],
        ["FB_Example.TcPOU", "implementation", ":9", txt],
        ["FB_Example.TcPOU", "implementation", ":12", txt],
        ["Checked 1 path(s)"],
        ["Re-saved 0 path(s)"],
    ]

    assert_strings_have_substrings(expected, caplog.messages)


def test_check(plc_code, caplog):
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

    formatter = Formatter(str(file), "--check")
    code = formatter.run()

    assert code != 0

    assert content_before == file.read_text()

    tctools.format.__main__.main(str(file))  # Re-format
    code_new = tctools.format.__main__.main(str(file), "--check")  # Check again
    assert code_new == 0


def test_check_recursive(plc_code, caplog):
    """Test `check` flag for formatter, on a folder"""
    project_folder = plc_code / "TwinCAT Project1"
    config = project_folder / ".editorconfig"
    config.write_text(
        """root = true
[*.TcPOU]
indent_style = space
indent_size = 4
"""
    )
    formatter = Formatter(str(project_folder), "--check", "-r", "-l", "DEBUG")
    code = formatter.run()

    for expected_file in [
        "FB_Example.TcPOU",
        "FB_Full.TcPOU",
        "MAIN.TcPOU",
        "GVL_Version.TcGVL",
        "ST_Example.TcDUT",
    ]:
        assert any(expected_file in msg for msg in caplog.messages)

    assert code != 0


def test_reformat_empty_config(plc_code):
    """Test reformatting with no or empty `editorconfig`.

    This also verified the formatter correctly puts the XML bits back.
    """
    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Full.TcPOU"

    content_before = file.read_text()

    formatter = Formatter(str(file))
    formatter.run()  # No error is given

    assert content_before == file.read_text() and "File was changed"

    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text("root = true")

    formatter = Formatter(str(file))
    formatter.run()  # No error is given

    assert content_before == file.read_text() and "File was changed"


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

    formatter = Formatter(str(file))
    formatter.run()

    content_after = file.read_text()
    assert "\t" not in content_after


def test_reformat_everything(plc_code):
    """Test reformatting for a typical file with a bunch of stuff."""
    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text(
        """root = true
[*.TcPOU]
indent_style = space
indent_size = 4
trim_trailing_whitespace = true
insert_final_newline = true
twincat_align_variables = true
"""
    )
    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Full.TcPOU"

    formatter = Formatter(str(file))
    formatter.run()

    file_fixed = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Full_fixed.txt"
    # ^ This file has manually fixed formatting

    assert (
        file.read_text() == file_fixed.read_text()
        and "Formatted result not as expected"
    )


@pytest.mark.parametrize("eol", [("lf", "\r\n", "\n"), ("crlf", "\n", "\r\n")])
def test_reformat_eol(plc_code, eol):
    """Test EOL correction."""
    config_eol, write_eol, expected_eol = eol

    config = plc_code / "TwinCAT Project1" / ".editorconfig"
    config.write_text(
        f"""root = true
    [*.TcPOU]
    end_of_line = {config_eol}
    """
    )

    # Version control will affect line endings, so just make the file here
    content_list = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<TcPlcObject>",
        '<POU Name="FB_Test>',
        "<Declaration><![CDATA[FUNCTION_BLOCK FB_Example",
        "VAR_OUTPUT",
        "    out     : BOOL;",
        "END_VAR",
        "]]></Declaration>",
        "<Implementation>",
        "<ST><![CDATA[",
        "out := TRUE;",
        "]]></ST>",
        "</Implementation>",
        "</POU>",
        "</TcPlcObject>",
    ]

    file = plc_code / "TwinCAT Project1" / "MyPlc" / "POUs" / "FB_Test.TcPOU"
    file.write_bytes(write_eol.join(content_list).encode())

    formatter = Formatter(str(file))
    formatter.run()

    content_after = file.read_bytes()
    assert content_after == expected_eol.join(content_list).encode()
