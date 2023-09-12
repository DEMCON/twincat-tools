from typing import List, OrderedDict, Tuple, Optional
from abc import ABC, abstractmethod
import re
import math


Correction = Tuple[int, str]


class FormattingRule(ABC):
    """TcFormatter rule base class.

    Extend and implement this class to check for and correct a specific error/style/etc.

    :cvar PRIORITY: Lower priority means a rule gets applied earlier.
    :cvar WHOLE_FILE: If True, rule is applied to the entire while instead of just
                      code blocks.
    """

    PRIORITY = 100
    WHOLE_FILE = False

    def __init__(self, properties: OrderedDict):
        self._properties = properties
        self._corrections: List[Correction] = []

        # Universal properties:

        self._indent_size: int = int(self._properties.get("tab_width", "4"))

        self._indent_style: Optional[str] = self._properties.get("indent_style", None)

        self._indent_str: str = " " * self._indent_size
        if self._indent_style and self._indent_style == "tab":
            self._indent_str = "\t"

        self._end_of_line: Optional[str] = self._properties.get("end_of_line", None)
        options = {"lf": "\n", "cr": "\r", "crlf": "\r\n"}
        self._line_ending: str = options.get(self._end_of_line, "\n")

        self._re_any_line_ending = re.compile(r"(\r\n|\n|\r)")  # Find any full EOL

    @abstractmethod
    def format(self, content: List[str]):
        """Fun rule to format text.

        :param content: Text to format (changed in place!)
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

    def format(self, content: List[str]):
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
                    int(math.ceil((matches.end() - matches.start()) / 4))
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
                    "Line contains an indent that should be a tab"
                    if self._indent_str == "\t"
                    else "Line contains a tab that should be spaces",
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

        self._remove_tr_ws = self._properties.get("trim_trailing_whitespace", False)

    def format(self, content: List[str]):
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

        self._insert_final_newline = self._properties.get("insert_final_newline", False)

    def format(self, content: List[str]):
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

    def format(self, content: List[str]):
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

    Target formatting will be split on the ":" and the inline comment.
    """

    def __init__(self, *args):
        super().__init__(*args)

        self._re_chunks = [
            (":", re.compile(r":(?!=)")),
            ("//", re.compile(r"\/\/")),
        ]

    def format(self, content: List[str]):
        self.format_argument_list(content)
        return

    def format_argument_list(self, content: List[str]):
        content_chunks = [self._split_line(line) for line in content]

        max_sizes = [
            max([len(line_chunks[i]) for line_chunks in content_chunks])
            for i in range(3)
        ]  # Biggest size of all lines per chunk

        indents = [1]  # Number of indents per chunk
        for size in max_sizes[:-1]:
            new_indent = indents[-1]
            new_indent += math.ceil((size + 2) / self._indent_size)
            indents.append(new_indent)

        for i, line_chunks in enumerate(content_chunks):
            new_line = ""
            for chunk, indent in zip(line_chunks, indents):
                if chunk:
                    new_line = self._pad_to_indent_level(new_line, indent)
                    new_line += chunk

            content[i] = new_line

    def _split_line(self, line: str) -> List[str]:
        """Split variable declaration string.

        The chunks returned are [name, type + value, comment].
        """
        pos = 0
        chunks = []
        for sep, regex in self._re_chunks:
            match = regex.search(line, pos)
            if match:
                substr = line[pos : match.end()]
                chunks.append(substr.strip() + sep)
                pos = match.end()
            else:
                chunks.append("")

        if pos < len(line):
            substr = line[pos:]
            chunks.append(substr.strip())
        else:
            chunks.append("")

        return chunks

    def _get_indent_string(self, col=0) -> str:
        """Return indent character(s), based on settings and current column.

        Either a tab or a set of spaces is returned such that the next tab index is
        reached exactly.
        """
        if self._indent_str == "\t":
            return self._indent_str

        num = self._indent_size - col % self._indent_size
        return self._indent_str[0] * num

    def _pad_to_indent_level(self, line: str, end_level: int):
        """Add indents to the end of a string to reach a tab index.

        ``end_level = 1`` would pad until ``line`` is e.g. 4 characters.
        """
        while end_level * self._indent_size - len(line) > 0:
            line += self._get_indent_string(col=len(line))

        return line


class FormatWhitespaceAlign(FormattingRule):
    """Assert whitespace aligns between code blocks.

    Most typical usage is in input/output lists.
    The rule is: any line with the same indentation as the line before, must match
    further indents in the line. 'Other indents' is defined as a single tab or 2 spaces
    or more.
    """

    def __init__(self, *args):
        super().__init__(*args)

        self._re_indent = re.compile(r"\t| {2," + str(self._indent_size) + r"}")

    def format(self, content: List[str]):
        line_prev = None
        level_prev = None
        for i, line in enumerate(content):
            level = self._get_base_indent_level(line)
            if line_prev is not None:
                if level == level_prev:
                    # Lines are matching
                    self.get_indents(line_prev)
                    pass

            line_prev = line
            level_prev = level

    def _get_base_indent_level(self, line: str) -> int:
        """Get indent level of a line."""
        indent = 0
        col = 0
        while col < len(line):
            if line[col] == "\t":
                indent += 1
                col += 1
            elif line[col : col + self._indent_size] == " " * self._indent_size:
                indent += 1
                col += self._indent_size
            else:
                break  # Different character - code must have started

        return indent

    def _find_indents(self, line: str):
        """Yield each indent *after* the base level."""
        pos = 0
        while pos < len(line):
            match = self._re_indent.search(line, pos)
            if not match:
                break
            pos = match.end()
            yield match.regs  # Get tuple
