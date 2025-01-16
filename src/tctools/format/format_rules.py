import math
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, OrderedDict, Tuple, Type

from .format_extras import Kind

Correction = Tuple[int, str]


class FormattingRule(ABC):
    """TcFormatter rule base class.

    Extend and implement this class to check for and correct a specific error/style/etc.

    :cvar PRIORITY: Lower priority means a rule gets applied earlier.
    :cvar WHOLE_FILE: If True, rule is applied to the entire file instead of just
                      code blocks.
    """

    PRIORITY = 100
    WHOLE_FILE = False

    def __init__(self, properties: OrderedDict):
        self._properties = properties
        self._corrections: List[Correction] = []

        # Universal properties:

        # Number of spaces per indentation:
        self._indent_size: int = self.get_property("indent_size", 4, value_type=int)
        # Number of spaces per tab character:
        self._tab_width: int = self.get_property(
            "tab_width", default=self._indent_size, value_type=int
        )

        self._indent_style: Optional[str] = self._properties.get("indent_style", None)

        self._indent_str: str = " " * self._indent_size
        if self._indent_style and self._indent_style == "tab":
            self._indent_str = "\t"

        self._end_of_line: Optional[str] = self._properties.get("end_of_line", None)
        options = {"lf": "\n", "cr": "\r", "crlf": "\r\n"}
        self._line_ending: str = options.get(self._end_of_line, "\n")

        self._re_any_line_ending = re.compile(r"(\r\n|\n|\r)")  # Find any full EOL

    @property
    def actual_indent_size(self) -> int:
        """Tab width for style=tabs or indent size for style=spaces."""
        if self._indent_style == "tab":
            return self._tab_width

        return self._indent_size

    def get_property(
        self,
        name: str,
        default: Any = None,
        value_type: Optional[Type] = None,
    ) -> Any:
        """Get item from ``_properties``, parsing as needed.

        :param name:
        :param default: Value to dfault if name doesn't exist
        :param value_type: Class of the returned value (e.g. ``bool``)
        """
        if name not in self._properties:
            return default

        value = self._properties[name]
        if value_type is None:
            return value  # Unprocessed

        if value_type == bool:
            if isinstance(value, str):
                return value in ["TRUE", "True", "true", "1"]
            return bool(value)

        return value_type(value)

    @abstractmethod
    def format(self, content: List[str], kind: Optional[Kind] = None):
        """Fun rule to format text.

        :param content: Text to format (changed in place!)
        :param kind:    Kind of content
        """
        pass

    def add_correction(self, message: str, line_nr: int):
        """Register a formatting correction.

        See :class:`Correction`.
        """
        self._corrections.append((line_nr, message))

    def consume_corrections(self) -> List[Correction]:
        """Return listed corrections and reset list."""
        corrections = self._corrections
        self._corrections = []
        return corrections


class FormatTabs(FormattingRule):
    """Check usage of tab character."""

    _re_tab = re.compile(r"\t")
    _re_spaces = re.compile(r"  +")  # Match two spaces or more

    def __init__(self, *args):
        super().__init__(*args)

    def format(self, content: List[str], kind: Optional[Kind] = None):
        if self._indent_style == "tab":
            re_search = self._re_spaces
        elif self._indent_style == "space":
            re_search = self._re_tab
        else:
            return

        for i, line in enumerate(content):
            pos = 0
            count = 0
            while (matches := re_search.search(line, pos)) is not None:
                pos = matches.end()
                num_chars = (
                    int(math.ceil((matches.end() - matches.start()) / self._tab_width))
                    if self._indent_str == "\t"
                    else self._indent_size - (matches.start() % self._indent_size)
                )

                line = (
                    line[: matches.start()]
                    + self._indent_str[0] * num_chars
                    + line[matches.end() :]
                )
                count += 1

            if count > 0:
                self.add_correction(
                    (
                        "Line contains an indent that should be a tab"
                        if self._indent_str == "\t"
                        else "Line contains a tab that should be spaces"
                    ),
                    i,
                )
                content[i] = line


class FormatTrailingWhitespace(FormattingRule):
    """Remove trailing whitespace."""

    PRIORITY = 90  # Precede `FinalNewline`

    _re_trailing_ws = re.compile(r"([^\S\r\n]+)([\r\n])*$")
    # Match whitespace (but not newlines) before (any) newline at the end of the line

    def __init__(self, *args):
        super().__init__(*args)

        self._remove_tr_ws = self.get_property(
            "trim_trailing_whitespace", False, value_type=bool
        )

    def format(self, content: List[str], kind: Optional[Kind] = None):
        if not self._remove_tr_ws:
            return  # Nothing to do
        for i, line in enumerate(content):
            line, count = re.subn(self._re_trailing_ws, r"\2", line)  # Keep group #2
            if count:
                content[i] = line
                self.add_correction("Line contains trailing whitespace", i)


class FormatInsertFinalNewline(FormattingRule):
    """Asserting a final empty newline in a file."""

    def __init__(self, *args):
        super().__init__(*args)

        self._insert_final_newline = self.get_property(
            "insert_final_newline", False, value_type=bool
        )

    def format(self, content: List[str], kind: Optional[Kind] = None):
        if not self._insert_final_newline:
            return

        if not content or len(content) == 1 and content[0] == "":
            return

        idx = len(content) - 1
        while idx >= 0:
            if content[idx].endswith("\n") or content[idx].endswith("\r"):
                return  # Newline found
            if content[idx] == "":
                idx -= 1  # Empty line, try the one before
            else:
                break  # Last content should be a newline, stay in function

        match = self._re_any_line_ending.search(content[0])
        # Get present EOL from first line
        eol = match.group(1) if match else self._line_ending

        content[-1] += eol
        self.add_correction("Block does not end with a newline", len(content) - 1)


class FormatEndOfLine(FormattingRule):
    """Asserting line endings are as expected."""

    WHOLE_FILE = True
    PRIORITY = 50  # Better do it a bit early

    def __init__(self, *args):
        super().__init__(*args)

        self._re_line_end = None

        if self._end_of_line is not None:
            if self._end_of_line == "lf":
                self._re_line_end = re.compile(r"\r\n|\r")
                # Works because Windows is first in the list
            elif self._end_of_line == "cr":
                self._re_line_end = re.compile(r"\r\n|\n")
            elif self._end_of_line == "crlf":
                self._re_line_end = re.compile(r"\r(?!\n)|(?<!\r)\n")
                # Match "\r" NOT followed by "\n" and match "\n" NOT preceded by "\r"
            else:
                raise ValueError(f"Unrecognized file ending `{self._line_ending}`")

    def format(self, content: List[str], kind: Optional[Kind] = None):
        if self._end_of_line is None:
            return  # Nothing specified

        count = 0
        for i, line in enumerate(content):
            line, new = re.subn(self._re_line_end, self._line_ending, line)
            if new > 0:
                content[i] = line
                count += new

        eol = self._line_ending.encode("unicode_escape")

        if count > 0:
            self.add_correction(
                f"{count} line endings need to be corrected to {eol}`", 0
            )


class FormatVariablesAlign(FormattingRule):
    """Assert whitespace align in variable declarations.

    Target formatting will create columns on the ":" and the "//" of comments.
    """

    PRIORITY = 110  # Go after FormatTabs

    def __init__(self, *args):
        super().__init__(*args)

        self._align = self.get_property(
            "twincat_align_variables", False, value_type=bool
        )

        self._re_variable = re.compile(
            r"""
                ^\s*                # Start of string + any ws
                (\S+)               # Sequence of non-ws
                \s*:                # Any ws + literal ":"
                \s*(.+?);           # Any ws + any sequence + literal ";"
                \s*([^\r\n]+)?      # Any ws + (Optional) any sequence
        """,
            re.VERBOSE,
        )

        self._re_newlines = re.compile(r"[\r\n]+$")

    def format(self, content: List[str], kind: Optional[Kind] = None):
        if not self._align:
            return  # Disabled by config

        if kind is None or kind is not Kind.DECLARATION:
            return  # Don't touch, only affect variable listing

        self.format_argument_list(content)

    def format_argument_list(self, content: List[str]):
        """Format entire declaration section"""

        # Get variable definitions, split up and keyed by content index:
        variable_definitions: Dict[int, List[Optional[str]]] = {}

        # Biggest size of each chunk across all lines:
        max_chunk_sizes: List[Optional[int]] = [None] * 3

        for i, line in enumerate(content):
            match = self._re_variable.match(line)
            if not match:
                continue

            chunks = list(match.groups())
            chunks[1] = f": {chunks[1]};"  # Bring match the matched characters

            variable_definitions[i] = chunks
            for j, chunk in enumerate(chunks):
                if not chunk:
                    continue
                if max_chunk_sizes[j] is None or len(chunk) > max_chunk_sizes[j]:
                    max_chunk_sizes[j] = len(chunk)

        if not variable_definitions:
            return  # No variables found, nothing to do

        new_indent = 1  # Variable name should start with one tab
        chunk_indent_levels = [new_indent]  # Number of indentations for each chunk
        for size in max_chunk_sizes[:-1]:
            new_indent += math.ceil((size + 2) / self.actual_indent_size)
            chunk_indent_levels.append(new_indent)

        for i, line_chunks in variable_definitions.items():
            new_line = ""
            for chunk, indent in zip(line_chunks, chunk_indent_levels):
                if chunk:
                    if indent > 0:
                        new_line += self._pad_to_indent_level(new_line, indent)
                    new_line += chunk

            if match_eol := self._re_newlines.search(content[i]):
                # The newline didn't get matched in the variable chunks, put it back:
                new_line += match_eol.group()

            if content[i] != new_line:
                self.add_correction("Variable declaration needs alignment", i)

            content[i] = new_line

    def _get_indent_string(self, col=0) -> str:
        """Return indent character(s), based on settings and current column.

        Either a tab or a set of spaces is returned such that the next tab index is
        reached exactly.
        """
        if self._indent_str == "\t":
            return self._indent_str

        num = self._indent_size - col % self._indent_size
        return self._indent_str[0] * num

    def _pad_to_indent_level(self, line: str, tab_index: int):
        """Add indents to the end of a string to reach a tab index.

        ``end_level = 1`` would pad until ``line`` is e.g. 4 characters.
        """
        index = math.floor(len(line) / self.actual_indent_size)

        padding_str = ""
        for i in range(tab_index - index):
            new_indent = (
                self._get_indent_string(col=len(line)) if i == 0 else self._indent_str
            )
            padding_str += new_indent

        return padding_str


class FormatConditionalParentheses(FormattingRule):
    """Formatter to make uses of parentheses inside IF, CASE and WHILE consistent.

    First regex is used to find potential corrections, which are then investigated
    by a loop to make sure parentheses remain matching and no essential parentheses
    are removed.
    """

    def __init__(self, *args):
        super().__init__(*args)

        self._parentheses = self.get_property(
            "twincat_parentheses_conditionals", value_type=bool
        )

        # Regex to find likely missing parentheses:
        self._re_needs_parentheses = re.compile(
            r"""
                # Look for start of string or new line:
                ^
                # Match keyword with surrounding ws:
                \s*(?:IF|WHILE|CASE)\s+
                # Match any characters NOT starting with "("
                # We cannot match the closing bracket, as this could be from a
                # function call
                ([^(\r\n].+?)
                # Match keyword with preceding ws:
                \s+(?:THEN|DO|OF)
            """,
            re.VERBOSE | re.MULTILINE,
        )

        # Regex to find likely redundant parentheses:
        self._re_removes_parentheses = re.compile(
            r"""
                # Look for start of string or new line:
                ^
                # Match keyword with surrounding ws:
                \s*(?:IF|WHILE|CASE)\s*
                # Match any characters within ():
                \((.+)\)
                # Match THEN with preceding ws:
                \s*(?:THEN|DO|OF)
            """,
            re.VERBOSE | re.MULTILINE,
        )

    def format(self, content: List[str], kind: Optional[Kind] = None):
        if self._parentheses is None:
            return  # Nothing to do

        pattern = (
            self._re_needs_parentheses
            if self._parentheses
            else self._re_removes_parentheses
        )

        for i, line in enumerate(content):
            # Do a manual match + replace, instead of e.g. subn(), because we might
            # need to add extra spaces after removing parentheses
            if match := pattern.search(line):
                prefix = line[: match.start(1)]
                condition = match.group(1)
                suffix = line[match.end(1) :]

                if self._parentheses:
                    condition = "(" + condition + ")"
                else:
                    # These parentheses could be of importance, check the leading
                    # "(" is not part of a smaller sub-statement:
                    if any(
                        level < 0 for _, level in self.find_and_match_braces(condition)
                    ):
                        continue

                    prefix = prefix[:-1]  # Remove parentheses
                    suffix = suffix[1:]

                    # Removing the () could cause a syntax error:
                    if not prefix.endswith(" "):
                        prefix += " "
                    if not suffix.startswith(" "):
                        suffix = " " + suffix

                self.add_correction(
                    (
                        "Parentheses around conditions are expected"
                        if self._parentheses
                        else "Parentheses around condition should be removed"
                    ),
                    i,
                )

                content[i] = prefix + condition + suffix

    @staticmethod
    def find_and_match_braces(
        text: str, brace_left: str = "(", brace_right: str = ")"
    ) -> Tuple[int, int]:
        """Step through braces in a string.

        Note that levels can step into negative.

        :return:    Tuple of (strpos, level), where strpos is the zero-index position of
                    the brace itself and level is the nested level it indicates
        """
        level = 0
        re_any_brace = re.compile(r"[" + brace_left + brace_right + "]")
        for match in re_any_brace.finditer(text):
            if match.group() == brace_left:
                level += 1  # Nest deeper
            else:
                level -= 1  # Nest back out
            yield match.start(), level
