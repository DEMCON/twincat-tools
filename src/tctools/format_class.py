from editorconfig import get_properties
from logging import getLogger
from typing import Optional, List, Tuple, Dict, Type
from collections import OrderedDict
import re
from enum import Enum

from .common import TcTool
from .format_rules import FormattingRule, CheckTabs


logger = getLogger("formatter")

re_trailing_ws = re.compile(r"\s+$")


RowCol = Tuple[int, int]


class Kind(Enum):
    NORMAL = 0,
    DECLARATION = 1,
    IMPLEMENTATION = 2


Segment = Tuple[Kind, List[str]]


class XmlMachine:
    """Helper class to identify code bits inside an XML file."""

    def __init__(self):
        self._kind = Kind.NORMAL
        self._row = 0  # Line number inside file
        self._col = 0  # Position inside line

        self.regions: Dict[RowCol, Kind] = {}

    def parse(self, content: List[str]):
        """Progress machine line by line."""
        self._kind = Kind.NORMAL
        self._row = 0
        self._col = 0
        self.regions = {(self._row, self._col): Kind.NORMAL.name}
        for self._row, line in enumerate(content):
            self._col = 0
            while self._col < len(line):
                self._parse_line(line)

    def _parse_line(self, line: str):
        """Parse a line, not necessarily starting from the left.

        :param line:
        """
        pos_before = self._col
        if self._kind == Kind.NORMAL:
            self._find_state_in_line(line, "<Declaration><![CDATA[", Kind.DECLARATION)
            self._find_state_in_line(line, "<ST><![CDATA[", Kind.IMPLEMENTATION)
        elif self._kind == Kind.DECLARATION:
            self._find_state_in_line(line, "]]></Declaration>", Kind.NORMAL)
        elif self._kind == Kind.IMPLEMENTATION:
            self._find_state_in_line(line, "]]></ST>", Kind.NORMAL)

        if self._col == pos_before:
            self._col = len(line)  # Nothing found, continue to next line

    def _find_state_in_line(self, line, key: str, new_state: Kind):
        """Find key elements inside a line to advance the states."""
        pos = line.find(key, self._col)
        if pos >= 0:
            self._kind = new_state
            self._col = pos + len(key)
            self.regions[(self._row, self._col)] = self._kind
            # First character of the new region


class Formatter(TcTool):
    """Helper to check formatting in PLC files.

    Instantiate once for a sequence of files.
    """

    _RULE_CLASSES: List[Type[FormattingRule]] = []

    def __init__(self):

        # Keep some dynamic properties around just so we don't have to constantly pass
        # them between methods
        self._file = ""
        self._properties = OrderedDict()
        self._tag = ""
        self._line_number = 0
        self._rules: List[FormattingRule] = []

        super().__init__()

    @classmethod
    def register_rule(cls, new_rule: Type[FormattingRule]):
        """Incorporate a new formatting rule (accounting for its priority)."""
        cls._RULE_CLASSES.append(new_rule)
        sorted(cls._RULE_CLASSES, key=lambda item: item.PRIORITY)

    def format(self, file: str):
        """Format (or check) a specific file.

        The file is read as text and code inside XML tags is detected manually. Other
        lines of XML remain untouched.
        """

        with open(file, "r") as fh:
            content = fh.readlines()

        self._file = file
        self._properties = get_properties(file)

        self._rules = [rule(self._properties) for rule in self._RULE_CLASSES]

        segment_last = (0, 0)
        for segment, kind in self.find_code_segments(content).items():
            # Loop over blocks of XML, declaration and implementation
            self.format_segment(content, segment, kind)
            segment_last = segment

        return

    @staticmethod
    def find_code_segments(content: List[str]) -> Dict[RowCol, Kind]:
        """Find code segments based on tags.

        Returns list of ((start_line, start_col), (end_line, end_col)).

        :return: List[Region]
        """
        machine = XmlMachine()

        machine.parse(content)

        return machine.regions

    def format_segment(self, content: List[str], segment: RowCol, kind: Kind):
        """Format a specific segment of code."""
        if kind == Kind.NORMAL:
            return  # Do nothing
        else:
            for rule in self._rules:
                rule.run(content)

    # def add_correction(self, message: str):
    #     """Register a formatting correction."""
    #     print(f"{self._file}\t{self._tag}:{self._line_number}\t{message}")
    #
    # def check_line(self, line: str):
    #     """Check a single line for formatting."""
    #     if line == "":
    #         return
    #
    #     self._check_line_tabs(line)
    #     self._check_trailing_whitespace(line)
    #
    # def _check_line_tabs(self, line: str):
    #     """Check for occurrences of the tab character."""
    #     style = self._properties.get("indent_style", None)
    #
    #     if style == "tab":
    #         tab = " " * int(self._properties.get("tab_width", "4"))
    #         if tab in line:
    #             self.add_correction("Line contains indent that should be a tab")
    #
    #     elif style == "space":
    #         if "\t" in line:
    #             self.add_correction("Line contains tab character")
    #
    # def _check_trailing_whitespace(self, line: str):
    #     """Check whitespace at the end of lines."""
    #     if self._properties.get("trim_trailing_whitespace", "false") != "true":
    #         return
    #
    #     if re_trailing_ws.search(line):
    #         self.add_correction("Line contains trailing whitespace")


Formatter.register_rule(CheckTabs)
