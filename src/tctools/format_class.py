from editorconfig import get_properties
from logging import getLogger
from typing import List, Tuple, Type
from collections import OrderedDict
from enum import Enum
import re

from .common import TcTool
from .format_rules import FormattingRule, FormatTabs, FormatTrailingWhitespace


logger = getLogger("formatter")


class Kind(Enum):
    XML = (0,)
    DECLARATION = (1,)
    IMPLEMENTATION = 2


RowCol = Tuple[int, int]
Segment = Tuple[Kind, List[str], str]


class XmlMachine:
    """Helper class to identify code bits inside an XML path."""

    _re_name = re.compile(r'Name="(\w+)"')

    def __init__(self):
        self._kind = Kind.XML
        self._name = ""
        self._row = 0  # Line number inside path
        self._col = 0  # Position inside line

        self.regions: List[Tuple[RowCol, Kind, str]] = []

    def parse(self, content: List[str]):
        """Progress machine line by line."""
        self._kind = Kind.XML
        self._row = 0
        self._col = 0
        self.regions = [((self._row, self._col), Kind.XML, "<unknown>")]
        for self._row, line in enumerate(content):
            self._col = 0

            if matches := self._re_name.search(line):
                self._name = matches.group(1)

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

            self.regions.append(((self._row, pos), self._kind, self._name))
            # First character of the new region


class Formatter(TcTool):
    """Helper to check formatting in PLC files.

    Instantiate once for a sequence of files.
    """

    _RULE_CLASSES: List[Type[FormattingRule]] = []

    def __init__(self, quiet=False, resave=True, report=False):
        """

        :param quiet:       If True, minimize CLI output
        :param resave:      If True, re-save the files in-place
        :param report:      If True, print all changes to be made
        """

        self.quiet = quiet
        self.resave = resave
        self.report = report

        # Keep some dynamic properties around just so we don't have to constantly pass
        # them between methods
        self._file = ""
        self._properties = OrderedDict()
        self._rules: List[FormattingRule] = []

        self._number_corrections = 0  # Track number of changes for the current file

        super().__init__()

    @classmethod
    def register_rule(cls, new_rule: Type[FormattingRule]):
        """Incorporate a new formatting rule (accounting for its priority)."""
        cls._RULE_CLASSES.append(new_rule)
        sorted(cls._RULE_CLASSES, key=lambda item: item.PRIORITY)

    def format_file(self, path: str):
        """Format (or check) a specific path.

        The path is read as text and code inside XML tags is detected manually. Other
        lines of XML remain untouched.
        """
        with open(path, "r") as fh:
            content = fh.readlines()

        self._file = path
        self._properties = get_properties(path)

        self.files_checked += 1
        self._number_corrections = 0

        if not self.quiet:
            logger.debug(f"Processing path `{path}`...")

        self._rules = [rule(self._properties) for rule in self._RULE_CLASSES]

        segments: List[Segment] = list(self.split_code_segments(content))

        for kind, segment, name in segments:
            # Changes are done in-place
            self.format_segment(segment, kind)

        if self._number_corrections > 0:
            self.files_to_alter += 1

        if self.resave:
            with open(path, "w", newline="") as fh:
                # Keep newline symbols inside strings
                for _, segment, _ in segments:
                    fh.write("".join(segment))

    @staticmethod
    def split_code_segments(content: List[str]):
        """Copy content, split into XML and code sections.

        Function is a generator, each pair is yielded.

        Note: line endings are not modified! I.e., segments should be appended together
        directly, without extra newlines.

        :param: File content as list
        :return: List[Segment]
        """
        machine = XmlMachine()
        machine.parse(content)

        regions = machine.regions
        regions.append(
            ((len(content), len(content[-1])), Kind.XML, "<unknown>")
        )  # Add end-of-path

        # Iterate over pairs of regions so we got the start and end together
        for (rowcol_prev, kind_prev, name_prev), (rowcol, kind, name) in zip(
            regions[:-1], regions[1:]
        ):
            lines = content[rowcol_prev[0] : (rowcol[0] + 1)]  # Inclusive range

            if rowcol_prev[1] > 0:
                lines[0] = lines[0][rowcol_prev[1] :]
                # Keep end of the first line

            if rowcol[1] < len(lines[-1]):
                lines[-1] = lines[-1][: rowcol[1]]
                # Keep start of the last line (last character is not included!)

            yield kind_prev, lines, name_prev

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
                corrections = rule.consume_corrections()
                self._number_corrections += len(corrections)

                tag = f"[{kind.name.lower()}]"

                if self.report:
                    for line_nr, message in corrections:
                        # `line_r` is zero-indexed
                        print(f"{self._file}{tag}:{line_nr+1}\t{message}")


Formatter.register_rule(FormatTabs)
Formatter.register_rule(FormatTrailingWhitespace)
