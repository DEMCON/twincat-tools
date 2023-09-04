from typing import List, OrderedDict
from abc import ABC, abstractmethod
import re
import math


class FormattingRule(ABC):
    """TcFormatter rule base class.

    Extend and implement this class to check for and correct a specific error/style/etc.
    """

    PRIORITY = 100

    def __init__(self, properties: OrderedDict):
        self._properties = properties

    @abstractmethod
    def format(self, content: List[str]):
        """Fun rule to format text.

        :param content: Text to format (changed in place!)
        """
        pass


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
                pos = 0
                count = 0
                while (matches := self._re_spaces.search(line, pos)) is not None:
                    pos = matches.end()
                    num_tabs = int(math.ceil((matches.end() - matches.start()) / 4))
                    line = (
                        line[: matches.start()]
                        + "\t" * num_tabs
                        + line[matches.end() :]
                    )
                    count += 1

                if count:
                    content[i] = line
                    # self.add_correction("Line contains indent that should be a tab")

            elif self._style == "space":
                pos = 0
                count = 0
                while (pos := line.find("\t", pos)) >= 0:
                    # Number of spaces to the next tab index:
                    num_spaces = self._indent_size - (pos % self._indent_size)
                    line = line[:pos] + " " * num_spaces + line[pos + 1 :]
                    count += 1

                if count:
                    content[i] = line
                    # self.add_correction("Line contains tab character")


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
                # self.add(...)
