"""Test the formatting rules without building the full applicaton."""

import pytest

from tctools import format_rules


def test_replace_tab():
    """Replace tab by spaces."""
    content = [
        "    var             : BOOL;\n",
        "\tother_var\t\t: USINT;\n",
        "\tanother_var\t\t: USINT;\n",
        "\tsome_var1   \t: USINT;\n",
    ]  # < These look aligned

    properties = {"indent_style": "space"}

    rule = format_rules.FormatTabs(properties)
    rule.format(content)

    assert content == [
        "    var             : BOOL;\n",
        "    other_var       : USINT;\n",
        "    another_var     : USINT;\n",
        "    some_var1       : USINT;\n",
    ]


def test_replace_spaces():
    """Replace spaces by tabs."""
    content = [
        "    var             : BOOL;\n",
        "\tother_var\t\t: USINT;\n",
        "\tsome_var1   \t: USINT;\n",
    ]  # < These look aligned

    properties = {"indent_style": "tab"}

    rule = format_rules.FormatTabs(properties)
    rule.format(content)

    assert content == [
        "\tvar\t\t\t\t: BOOL;\n",
        "\tother_var\t\t: USINT;\n",
        "\tsome_var1\t\t: USINT;\n",
    ]


def test_trailing_ws():
    """Removal of ws."""
    content = [
        "flag1 := FALSE;         \n",
        "       flag2 := FALSE;         \n",
        "flag3 := FALSE;\t\t\n",
        "\n",
        "\n",
        "flag4 := TRUE;\n",
        "\n",
    ]

    properties = {"trim_trailing_whitespace": True}

    rule = format_rules.FormatTrailingWhitespace(properties)
    rule.format(content)

    assert content == [
        "flag1 := FALSE;\n",
        "       flag2 := FALSE;\n",
        "flag3 := FALSE;\n",
        "\n",
        "\n",
        "flag4 := TRUE;\n",
        "\n",
    ]


def test_final_newline():
    """Addition of final empty newline."""
    content = [
        "flag1 := FALSE;         \n",
        "       flag2 := FALSE;         \n",
        "flag3 := FALSE;\t\t",
    ]

    properties = {"insert_final_newline": True}

    rule = format_rules.FormatInsertFinalNewline(properties)
    rule.format(content)

    assert content == [
        "flag1 := FALSE;         \n",
        "       flag2 := FALSE;         \n",
        "flag3 := FALSE;\t\t\n",
    ]


def test_end_of_line():
    """Test EOL correction."""
    content_before = [
        "func();\n",
        "func();\r\n",
        "func();\r\n\r\n\r\n",
        "func();\n",
        "func();\r",
        "func();\r\r",
        "func();\n",
    ]

    content = content_before.copy()
    rule = format_rules.FormatEndOfLine({"end_of_line": "lf"})
    rule.format(content)

    assert content == [
        "func();\n",
        "func();\n",
        "func();\n\n\n",
        "func();\n",
        "func();\n",
        "func();\n\n",
        "func();\n",
    ]

    content = content_before.copy()
    rule = format_rules.FormatEndOfLine({"end_of_line": "crlf"})
    rule.format(content)

    assert content == [
        "func();\r\n",
        "func();\r\n",
        "func();\r\n\r\n\r\n",
        "func();\r\n",
        "func();\r\n",
        "func();\r\n\r\n",
        "func();\r\n",
    ]

    content = content_before.copy()
    rule = format_rules.FormatEndOfLine({"end_of_line": "cr"})
    rule.format(content)

    assert content == [
        "func();\r",
        "func();\r",
        "func();\r\r\r",
        "func();\r",
        "func();\r",
        "func();\r\r",
        "func();\r",
    ]
