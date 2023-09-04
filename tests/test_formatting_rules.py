"""Test the formatting rules without building the full applicaton."""

import pytest

from tctools import format_rules


def test_replace_tab():
    """Replace tab by spaces."""
    content = [
        "    var             : BOOL; // Spaces\n",
        "\tother_var\t\t: USINT; // Tabs\n",
    ]

    properties = {"indent_style": "space"}

    formatter = format_rules.FormatTabs(properties)
    formatter.format(content)

    # TODO: Fix alignment
    assert content == [
        "    var             : BOOL; // Spaces\n",
        "    other_var        : USINT; // Tabs\n",
    ]


def test_replace_spaces():
    """Replace spaces by tabs."""
    content = [
        "    var             : BOOL; // Spaces\n",
        "\tother_var\t\t: USINT; // Tabs\n",
    ]

    properties = {"indent_style": "tab"}

    formatter = format_rules.FormatTabs(properties)
    formatter.format(content)

    # TODO: Fix alignment
    assert content == [
        "\tvar\t\t\t : BOOL; // Spaces\n",
        "\tother_var\t\t: USINT; // Tabs\n",
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

    # TODO: Fix alignment
    assert content == [
        "flag1 := FALSE;\n",
        "       flag2 := FALSE;\n",
        "flag3 := FALSE;\n",
        "\n",
        "\n",
        "flag4 := TRUE;\n",
        "\n",
    ]
