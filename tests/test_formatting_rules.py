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
    content_new = content.copy()
    rule.format(content_new)
    assert content_new == expected


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
    content_new = content.copy()
    rule.format(content_new)
    assert content_new == expected


content_variables = [
    (
        [
            "FUNCTION_BLOCK FB_Cool EXTENDS FB_MyBlock2\n",
            "// Untouched\n",
            "VAR_IN_OUT\n",
            "    var1    : LREAL := 5.0;    // Comment\r\n",
            "anotherVar    : FB_MyBlock(va1 := 1, var2 := 2);\n",
            "    // Untouched\n",
            "    other \t\t : INT;  // Other comment\n",
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
        {"twincat_align_variables": True},
    ),
    (
        [
            "FUNCTION_BLOCK FB_Cool EXTENDS FB_MyBlock2\n",
            "//\tUntouched\n",
            "VAR_IN_OUT\n",
            "\tvar1 : LREAL := 5.0;// Comment\r\n",
            "anotherVar\t: \t FB_MyBlock(va1 := 1, var2 := 2);\n",
            "\t// Untouched\n",
            "\tother\t\t:\t\tINT;\t\t\t// Other comment\n",
            "END_VAR\n",
        ],
        [
            "FUNCTION_BLOCK FB_Cool EXTENDS FB_MyBlock2\n",
            "//\tUntouched\n",
            "VAR_IN_OUT\n",
            "\tvar1\t\t\t: LREAL := 5.0;\t\t\t\t\t\t\t\t// Comment\r\n",
            "\tanotherVar\t\t: FB_MyBlock(va1 := 1, var2 := 2);\n",
            "\t// Untouched\n",
            "\tother\t\t\t: INT;\t\t\t\t\t\t\t\t\t\t// Other comment\n",
            "END_VAR\n",
        ],
        {"indent_style": "tab", "twincat_align_variables": True},
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
        {"twincat_align_variables": True},
    ),
    # (  # These multi-line definitions do not work unfortunately
    #     [
    #         "VAR_IN\n",
    #         "    regularVar: LREAL := 5.0; // Comment\n",
    #         "    multiLineFB: FB_MyBlock := (\n",
    #         "        arg1 := TRUE,\n",
    #         "        arg2 := 'hello',\n",
    #         "    ); // Other comment\n",
    #         "VAR_OUT\n",
    #     ],
    #     [
    #         [
    #             "VAR_IN\n",
    #             "    regularVar      : LREAL := 5.0;     // Comment\n",
    #             "    multiLineFB     : FB_MyBlock := (\n",
    #             "        arg1 := TRUE,\n",
    #             "        arg2 := 'hello',\n",
    #             "    );                                  // Other comment\n",
    #             "VAR_OUT\n",
    #         ],
    #     ],
    #     {"twincat_align_variables": True},
    # ),
]


@pytest.mark.parametrize("content,expected,settings", content_variables)
def test_variable_align(content, expected, settings):
    rule = format_rules.FormatVariablesAlign(settings)
    content_new = content.copy()
    rule.format(content_new, Kind.DECLARATION)
    assert content_new == expected


content_parentheses = [
    (
        [
            "IF inputs.button = 1 THEN\n",
            "    output.led := 1;\n",
            "END_IF\n",
        ],
        [
            "IF (inputs.button = 1) THEN\n",
            "    output.led := 1;\n",
            "END_IF\n",
        ],
    ),
    (
        [
            "IF inputs.button = 1 THEN // comment!\n",
        ],
        [
            "IF (inputs.button = 1) THEN // comment!\n",
        ],
    ),
    (
        [
            "IF func(arg1 := 1, args2 := func2()) THEN\n",
        ],
        [
            "IF (func(arg1 := 1, args2 := func2())) THEN\n",
        ],
    ),
    (
        [
            "WHILE func() DO // comment!\n",
        ],
        [
            "WHILE (func()) DO // comment!\n",
        ],
    ),
    (
        [
            "CASE idx OF\n",
        ],
        [
            "CASE (idx) OF\n",
        ],
    ),
    # (  # This case fails, because we cannot identify matching parentheses:
    #     [
    #         "IF (1+1)*2 = 3*(x-1) THEN\n",
    #     ],
    #     [
    #         "IF ((1+1)*2 = 3*(x-1)) THEN\n",
    #     ],
    # ),
]


@pytest.mark.parametrize("content,expected", content_parentheses)
def test_parentheses_add(content, expected):
    rule = format_rules.FormatConditionalParentheses({"twincat_parentheses_conditionals": True})
    content_new = content.copy()
    rule.format(content_new)
    assert content_new == expected


@pytest.mark.parametrize("expected,content", content_parentheses)
def test_parentheses_remove(expected, content):
    rule = format_rules.FormatConditionalParentheses(
        {"twincat_parentheses_conditionals": False}
    )
    content_new = content.copy()
    rule.format(content_new)
    assert content_new == expected


def test_parentheses_remove_no_ws():
    rule = format_rules.FormatConditionalParentheses(
        {"twincat_parentheses_conditionals": False}
    )
    content = ["IF(inputs.button = 1)THEN"]
    rule.format(content)
    assert content == ["IF inputs.button = 1 THEN"]
