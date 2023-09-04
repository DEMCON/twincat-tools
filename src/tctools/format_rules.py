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
    def run(self, content: List[str]):
        pass


class CheckTabs(FormattingRule):
    """Check usage of tab character."""

    _re_tab = re.compile(r"\t")

    def __init__(self, *args):
        super().__init__(*args)

        self._style = self._properties.get("indent_style", None)
        self._indent = " " * int(self._properties.get("tab_width", "4"))
        self._re_indent = re.compile(self._indent)

    def run(self, content: List[str]):
        for i, line in enumerate(content):
            if self._style == "tab":
                new_line, count = re.subn(self._re_indent, "\t")
                if count:
                    pass
                    # self.add_correction("Line contains indent that should be a tab")

            elif self._style == "space":
                new_line, count = re.subn(self._re_tab, self._indent)
                if count:
                    pass
                    # self.add_correction("Line contains tab character")
