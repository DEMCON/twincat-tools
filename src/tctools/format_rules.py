from typing import List, OrderedDict, Tuple
from abc import ABC, abstractmethod
import re
import math


Correction = Tuple[int, str]


class FormattingRule(ABC):
    """TcFormatter rule base class.

    Extend and implement this class to check for and correct a specific error/style/etc.
    """

    PRIORITY = 100

    def __init__(self, properties: OrderedDict):
        self._properties = properties
        self._corrections: List[Correction] = []

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

    _re_trailing_ws = re.compile(r"[^\S\r\n]+$")  # Match whitespace but not newlines

    def __init__(self, *args):
        super().__init__(*args)

        self._remove_tr_ws = self._properties.get("trim_trailing_whitespace", False)

    def format(self, content: List[str]):
        if not self._remove_tr_ws:
            return  # Nothing to do
        for i, line in enumerate(content):
            line, count = re.subn(self._re_trailing_ws, "", line)
            if count:
                content[i] = line
                self.add_correction("Line contains trailing whitespace", i)
