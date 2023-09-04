from editorconfig import get_properties
from logging import getLogger
from typing import Optional, List, Tuple, Dict, Type
from collections import OrderedDict
from enum import Enum

from .common import TcTool
from .format_rules import FormattingRule, FormatTabs, FormatTrailingWhitespace


logger = getLogger("formatter")


class Kind(Enum):
    XML = (0,)
    DECLARATION = (1,)
    IMPLEMENTATION = 2


RowCol = Tuple[int, int]
Segment = Tuple[Kind, List[str]]


class XmlMachine:
    """Helper class to identify code bits inside an XML file."""

    def __init__(self):
        self._kind = Kind.XML
        self._row = 0  # Line number inside file
        self._col = 0  # Position inside line

        self.regions: List[Tuple[RowCol, Kind]] = []

    def parse(self, content: List[str]):
        """Progress machine line by line."""
        self._kind = Kind.XML
        self._row = 0
        self._col = 0
        self.regions = [((self._row, self._col), Kind.XML)]
        for self._row, line in enumerate(content):
            self._col = 0
            while self._col < len(line):
                self._parse_line(line)

    def _parse_line(self, line: str):
        """Parse a line, not necessarily starting from the left.

        :param line:
        """
        pos_before = self._col
        if self._kind == Kind.XML:
            self._find_state_in_line(line, "<Declaration><![CDATA[", Kind.DECLARATION)
            self._find_state_in_line(line, "<ST><![CDATA[", Kind.IMPLEMENTATION)
        elif self._kind == Kind.DECLARATION:
            self._find_state_in_line(line, "]]></Declaration>", Kind.XML, True)
        elif self._kind == Kind.IMPLEMENTATION:
            self._find_state_in_line(line, "]]></ST>", Kind.XML, True)

        if self._col == pos_before:
            self._col = len(line)  # Nothing found, continue to next line

    def _find_state_in_line(
        self, line, key: str, new_state: Kind, include_key: bool = False
    ):
        """Find key elements inside a line to advance the states.

        When ``include_key`` is True, the text of the key is considered part of the new
        state.
        """
        pos = line.find(key, self._col)
        if pos >= 0:
            self._kind = new_state
            self._col = pos + len(key)

            if not include_key:
                pos += len(key)

            self.regions.append(((self._row, pos), self._kind))
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

        segments: List[Segment] = list(self.split_code_segments(content))

        for kind, segment in segments:
            # Changes are done in-place
            self.format_segment(segment, kind)

        with open(file, "w", newline="") as fh:
            # Keep newline symbols inside strings
            for _, segment in segments:
                fh.write("".join(segment))

    @staticmethod
    def split_code_segments(content: List[str]):
        """Copy content, split into XML and code sections.

        Function is a generator, each pair is yielded.

        Note: line endings are not modified! I.e., segments should be appended together
        directly, without extra newlines.

        :param: File content as list
        :return: List[Region]
        """
        machine = XmlMachine()
        machine.parse(content)

        regions = machine.regions
        regions.append(
            ((len(content), len(content[-1])), Kind.XML)  # Add end-of-file
        )

        # Iterate over pairs of regions so we got the start and end together
        for (rowcol_prev, kind_prev), (rowcol, kind) in zip(regions[:-1], regions[1:]):
            lines = content[rowcol_prev[0]: (rowcol[0] + 1)]  # Inclusive range

            if rowcol_prev[1] > 0:
                lines[0] = lines[0][rowcol_prev[1] :]
                # Keep end of the first line

            if rowcol[1] < len(lines[-1]):
                lines[-1] = lines[-1][: rowcol[1]]
                # Keep start of the last line (last character is not included!)

            yield kind_prev, lines

    def format_segment(self, content: List[str], kind: Kind):
        """Format a specific segment of code.

        :param content: Text to reformat (changed in place!)
        :param kind: Type of the content
        """
        if kind == Kind.XML:
            return  # Do nothing
        else:
            for rule in self._rules:
                rule.format(content)

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


Formatter.register_rule(FormatTabs)
Formatter.register_rule(FormatTrailingWhitespace)
