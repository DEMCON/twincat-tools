import re
from collections import OrderedDict
from typing import List, Optional, Tuple, Type

from editorconfig import get_properties

from ..common import TcTool
from .format_extras import Kind
from .format_rules import (
    FormatConditionalParentheses,
    FormatEndOfLine,
    FormatInsertFinalNewline,
    FormatTabs,
    FormattingRule,
    FormatTrailingWhitespace,
    FormatVariablesAlign,
)

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

    LOGGER_NAME = "formatter"

    FILTER_DEFAULT = ["*.TcPOU", "*.TcGVL", "*.TcDUT"]

    CONFIG_KEY = "format"

    _RULE_CLASSES: List[Type[FormattingRule]] = []

    def __init__(self, *args):
        super().__init__(*args)

        # Keep some dynamic properties around just so we don't have to constantly pass
        # them between methods
        self._file = ""
        self._properties = OrderedDict()
        self._rules: List[FormattingRule] = []

        self._number_corrections = 0  # Track number of changes for the current file

    @classmethod
    def set_arguments(cls, parser):
        super().set_arguments(parser)

        parser.description = "Format the PLC code inside a TwinCAT source XML path."
        parser.epilog = "Example: ``tc_format -r ./MyTwinCATProject``"
        return parser

    @classmethod
    def register_rule(cls, new_rule: Type[FormattingRule]):
        """Incorporate a new formatting rule (accounting for its priority)."""
        cls._RULE_CLASSES.append(new_rule)
        sorted(cls._RULE_CLASSES, key=lambda item: item.PRIORITY)

    def run(self) -> int:
        files = self.find_files()

        for file in files:
            self.format_file(str(file))

        self.logger.info(f"Checked {self.files_checked} path(s)")

        if self.args.check:
            if self.files_to_alter == 0:
                self.logger.info("No changes to be made in checked files!")
                return 0

            self.logger.info(f"{self.files_to_alter} path(s) should altered")
            return 1

        self.logger.info(f"Re-saved {self.files_resaved} path(s)")
        return 0

    def format_file(self, path: str):
        """Format (or check) a specific path.

        The path is read as text and code inside XML tags is detected manually. Other
        lines of XML remain untouched.
        """
        with open(path, "r", encoding="utf-8", errors="ignore", newline="") as fh:
            content = fh.readlines()

        self._file = path

        self._properties = get_properties(path)
        if not self._properties:
            self.logger.warning(f"Editorconfig properties is empty for file `{path}`")

        self.files_checked += 1
        self._number_corrections = 0

        self.logger.debug(f"Processing path `{path}`...")

        self._rules = [rule(self._properties) for rule in self._RULE_CLASSES]

        # Do whole-file rules first:
        for rule in self._rules:
            if rule.WHOLE_FILE:
                self.apply_rule(rule, content)

        segments: List[Segment] = list(self.split_code_segments(content))

        for kind, segment, _ in segments:
            # Changes are done in-place
            self.format_segment(segment, kind)

        if self._number_corrections > 0:
            self.files_to_alter += 1

        if not self.args.dry and not self.args.check and self._number_corrections > 0:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                # Keep newline symbols inside strings
                for _, segment, _ in segments:
                    fh.write("".join(segment))

            self.files_resaved += 1

    @staticmethod
    def split_code_segments(content: List[str]):
        """Copy content, split into XML and code sections.

        Function is a generator, each pair is yielded.

        Note: line endings are not modified! I.e., segments should be appended together
        directly, without extra newlines.

        :param: File content as list
        :return: List[Segment]
        """
        if not content:
            return  # Nothing to yield

        machine = XmlMachine()
        machine.parse(content)

        regions = machine.regions
        regions.append(
            ((len(content), len(content[-1])), Kind.XML, "<unknown>")
        )  # Add end-of-path

        # Iterate over pairs of regions so we got the start and end together
        for (rowcol_prev, kind_prev, name_prev), (rowcol, _, _) in zip(
            regions[:-1], regions[1:]
        ):
            lines = content[rowcol_prev[0] : (rowcol[0] + 1)]  # Inclusive range

            if rowcol[0] == rowcol_prev[0]:  # If there is only a single line!
                lines[0] = lines[0][rowcol_prev[1] : rowcol[1]]
                # Use two columns in one step, otherwise the columns move
            else:
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
                if not rule.WHOLE_FILE:  # Skip otherwise
                    self.apply_rule(rule, content, kind)

    def apply_rule(self, rule, content, kind: Optional[Kind] = None):
        """Run a rule over some content and handle results."""
        rule.format(content, kind)
        corrections = rule.consume_corrections()
        self._number_corrections += len(corrections)

        tag = f"[{kind.name.lower()}]" if kind else "[file]"

        for line_nr, message in corrections:
            # `line_r` is zero-indexed
            self.logger.debug(f"{self._file}{tag}:{line_nr + 1}\t{message}")


Formatter.register_rule(FormatTabs)
Formatter.register_rule(FormatTrailingWhitespace)
Formatter.register_rule(FormatInsertFinalNewline)
Formatter.register_rule(FormatEndOfLine)
Formatter.register_rule(FormatVariablesAlign)
Formatter.register_rule(FormatConditionalParentheses)
