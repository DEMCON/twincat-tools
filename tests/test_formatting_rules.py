"""Test the formatting rules without building the full application."""

import pytest

from tctools import format_rules
from tctools.format_class import Kind


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


content_final_newline = [
    (
        ["flag1 := FALSE;"],
        ["flag1 := FALSE;\n"],
    ),
    (
        ["flag1 := FALSE;    "],
        ["flag1 := FALSE;    \n"],
    ),
    (
        ["flag1 := FALSE;\n", "flag2 := FALSE;\n"],
        ["flag1 := FALSE;\n", "flag2 := FALSE;\n"],
    ),
    (
        [],
        [],
    ),
    (
        ["flag1 := TRUE;", "", "", ""],
        ["flag1 := TRUE;", "", "", "\n"],
    ),
    (
        ["flag1 := TRUE;\r\n", "flag2 := TRUE;"],
        ["flag1 := TRUE;\r\n", "flag2 := TRUE;\r\n"],
    ),
]


@pytest.mark.parametrize("content,expected", content_final_newline)
def test_final_newline(content, expected):
    """Addition of final empty newline."""
    properties = {"insert_final_newline": True}

    rule = format_rules.FormatInsertFinalNewline(properties)
    rule.format(content)

    assert content == expected


content_eol = [
    (
        "lf",
        [
            "func();\n",
            "func();\n",
            "func();\n\n\n",
            "func();\n",
            "func();\n",
            "func();\n\n",
            "func();\n",
        ],
    ),
    (
        "crlf",
        [
            "func();\r\n",
            "func();\r\n",
            "func();\r\n\r\n\r\n",
            "func();\r\n",
            "func();\r\n",
            "func();\r\n\r\n",
            "func();\r\n",
        ],
    ),
    (
        "cr",
        [
            "func();\r",
            "func();\r",
            "func();\r\r\r",
            "func();\r",
            "func();\r",
            "func();\r\r",
            "func();\r",
        ],
    ),
]


@pytest.mark.parametrize("eol,expected", content_eol)
def test_end_of_line(eol, expected):
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
    rule = format_rules.FormatEndOfLine({"end_of_line": eol})
    rule.format(content)

    assert content == expected


content_variables = [
    (
        [
            "FUNCTION_BLOCK FB_Cool EXTENDS FB_MyBlock2\n",
            "// Untouched\n",
            "VAR_IN_OUT\n",
            "    var1    : LREAL := 5.0;    // Comment\r\n",
            "    anotherVar    : FB_MyBlock(va1 := 1, var2 := 2);\n",
            "    // Untouched\n",
            "    other   : INT;  // Other comment\n",
            "END_VAR\n",
        ],
        [
            "FUNCTION_BLOCK FB_Cool EXTENDS FB_MyBlock2\n",
            "// Untouched\n",
            "VAR_IN_OUT\n",
            "    var1        : LREAL := 5.0;                     // Comment\r\n",
            "    anotherVar  : FB_MyBlock(va1 := 1, var2 := 2);\n",
            "    // Untouched\n",
            "    other       : INT;                              // Other comment\n",
            "END_VAR\n",
        ],
    ),
    (
        [
            "METHOD Empty\n",
            "VAR_IN\n",
            "\n",
            "VAR_OUT\n",
            "",
        ],
        [
            "METHOD Empty\n",
            "VAR_IN\n",
            "\n",
            "VAR_OUT\n",
            "",
        ],
    )
]


@pytest.mark.parametrize("content,expected", content_variables)
def test_variable_align(content, expected):
    rule = format_rules.FormatVariablesAlign({})
    rule.format(content, Kind.DECLARATION)
    assert content == expected
