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

    formatter = format_rules.FormatTabs(properties)
    formatter.format(content)

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

    formatter = format_rules.FormatTabs(properties)
    formatter.format(content)

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

    formatter = format_rules.FormatTrailingWhitespace(properties)
    formatter.format(content)

    assert content == [
        "flag1 := FALSE;\n",
        "       flag2 := FALSE;\n",
        "flag3 := FALSE;\n",
        "\n",
        "\n",
        "flag4 := TRUE;\n",
        "\n",
    ]
