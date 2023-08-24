from editorconfig import get_properties
from logging import getLogger
from typing import Optional
from collections import OrderedDict
import re

from .common import TcTool


logger = getLogger("formatter")

re_trailing_ws = re.compile("\s+$")


class Formatter(TcTool):
    """Helper to check formatting in PLC files.

    Instantiate once for a sequence of files.
    """

    def __init__(self):

        # Keep some dynamic properties around just so we don't have to constantly pass
        # them between methods
        self._file = ""
        self._properties = OrderedDict()
        self._tag = ""
        self._line_number = 0

        super().__init__()

    def format(self, file: str):
        """Format (or check) a specific file."""

        tree = self.get_xml_tree(file)
        root = tree.getroot()

        if root.tag != "TcPlcObject":
            raise ValueError(f"File {file} does not have a `TcPlcObject` at the base")

        self._file = file
        self._properties = get_properties(file)

        for name, segment in self.get_code_segments(root):
            if not segment.text:
                continue
            self._tag = name
            lines = segment.text.split("\n")
            for nr, line in enumerate(lines):
                self._line_number = nr + 1
                self.check_line(line)

        return

    @classmethod
    def get_code_segments(cls, parent):
        """Use recursion to dig into an XML element to find all PLC code.

        :param parent: XML element to search in and under
        """
        for element in parent:
            if element.tag == "Declaration":
                yield (parent.get("Name", "<unknown>") + " [declaration]", element)
            if element.tag == "Implementation":
                st = element.find("ST")
                if st is not None:
                    yield (parent.get("Name", "<unknown>") + " [implementation]", st)
            else:
                yield from cls.get_code_segments(element)

    def add_correction(self, message: str):
        """Register a formatting correction."""
        print(f"{self._file}\t{self._tag}:{self._line_number}\t{message}")

    def check_line(self, line: str):
        """Check a single line for formatting."""
        if line == "":
            return

        self._check_line_tabs(line)
        self._check_trailing_whitespace(line)

    def _check_line_tabs(self, line: str):
        """Check for occurences of the tab character."""
        style = self._properties.get("indent_style", None)

        if style == "tab":
            tab = " " * int(self._properties.get("tab_width", "4"))
            if tab in line:
                self.add_correction("Line contains indent that should be a tab")

        elif tab == "space":
            if "\t" in line:
                self.add_correction("Line contains tab character")

    def _check_trailing_whitespace(self, line: str):
        """Check whitespace at the end of lines."""
        if self._properties.get("trim_trailing_whitespace", "false") != "true":
            return

        if re_trailing_ws.search(line):
            self.add_correction("Line contains trailing whitespace")
