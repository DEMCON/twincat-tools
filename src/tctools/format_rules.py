from typing import List, OrderedDict
from abc import ABC, abstractmethod
import re


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

    def __init__(self, *args):
        super().__init__(*args)

        self._style = self._properties.get("indent_style", None)
        self._indent = " " * int(self._properties.get("tab_width", "4"))
        self._re_indent = re.compile(self._indent)

    def format(self, content: List[str]):
        # TODO: Honour actual tab index (some tabs are shorter)
        for i, line in enumerate(content):
            if self._style == "tab":
                line, count = re.subn(self._re_indent, "\t", line)
                if count:
                    content[i] = line
                    # self.add_correction("Line contains indent that should be a tab")

            elif self._style == "space":
                line, count = re.subn(self._re_tab, self._indent, line)
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
