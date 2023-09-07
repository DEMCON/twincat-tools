from typing import List, OrderedDict, Tuple
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
        self._end_of_line = self._properties.get("end_of_line", None)
        options = {"lf": "\n", "cr": "\r", "crlf": "\r\n"}
        self._line_ending = options.get(self._end_of_line, "\n")

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

        self._style = self._properties.get("indent_style", None)
        self._indent_size = int(self._properties.get("tab_width", "4"))
        self._indent = " " * self._indent_size
        self._re_indent = re.compile(self._indent)

    def format(self, content: List[str]):
        for i, line in enumerate(content):
            if self._style == "tab":
                re_search = self._re_spaces
                new_char = "\t"
            elif self._style == "space":
                re_search = self._re_tab
                new_char = " "
            else:
                continue

            pos = 0
            count = 0
            while (matches := re_search.search(line, pos)) is not None:
                pos = matches.end()
                num_chars = 0
                if new_char == " ":  # Tab > spaces
                    num_chars = self._indent_size - (
                        matches.start() % self._indent_size
                    )
                elif new_char == "\t":  # Spaces > tabs
                    num_chars = int(math.ceil((matches.end() - matches.start()) / 4))
                line = (
                    line[: matches.start()]
                    + new_char * num_chars
                    + line[matches.end() :]
                )
                count += 1

            if count > 0:
                self.add_correction(
                    "Line contains an indent that should be a tab"
                    if new_char == "\t"
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

        self._insert = self._properties.get("insert_final_newline", False)

    def format(self, content: List[str]):
        if not self._insert:
            return

        if len(content) == 1 and content[0] == "":
            return

        if content[-1].endswith("\n") or content[-1].endswith("\r"):
            return

        if content[-1] == "" and (
            content[-2].endswith("\n") or content[-2].endswith("\r")
        ):
            return  # Then the line before does it already

        content[-1] += "\n"
        # TODO: Support different file endings
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
