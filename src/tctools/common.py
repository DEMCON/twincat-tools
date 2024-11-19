import logging
import sys
from abc import ABC, abstractmethod
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path
from typing import List, Optional

from lxml import etree

# Create type hinting shortcuts:
Element = etree._Element  # noqa
ElementTree = etree._ElementTree  # noqa


class Tool(ABC):
    """Tools base class.

    ``argparse`` is done in the constructor, CLI arguments should be passed there.
    """

    LOGGER_NAME: Optional[str] = None

    # Default value for file filter argument:
    FILTER_DEFAULT: List[str]

    def __init__(self, *args):
        """Pass e.g. ``sys.args[1:]`` (skipping the script part of the arguments).

        :param args: See :meth:`set_arguments`
        """
        self.args = self.get_argument_parser().parse_args(args)
        self.logger = self.get_logger()

    @classmethod
    def get_argument_parser(cls) -> ArgumentParser:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        cls.set_arguments(parser)
        return parser

    @classmethod
    def set_arguments(cls, parser):
        """Create application-specific arguments."""
        parser.add_argument(
            "--dry",
            help="Do not modify files on disk, only report changes to be made",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "--log-level",
            "-l",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Set log level to change verbosity",
            default="INFO",
        )
        return parser

    @abstractmethod
    def run(self) -> int:
        """Main tool execution."""

    def get_logger(self):
        """Get logger for this class."""
        logging.basicConfig(stream=sys.stdout)
        logger = logging.getLogger(self.LOGGER_NAME or __name__)
        if "log_level" in self.args and self.args.log_level:
            level = logging.getLevelName(self.args.log_level)
            logger.setLevel(level)

        return logger


class TcTool(Tool, ABC):
    """Base class for tools sharing TwinCAT functionality."""

    def __init__(self, *args):
        super().__init__(*args)

        # Preserve `CDATA` XML flags:
        self.xml_parser = etree.XMLParser(strip_cdata=False)

        self.header_before: Optional[str] = None  # Header of the last XML path

        self.files_checked = 0  # Files read by parser
        self.files_to_alter = 0  # Files that seem to require changes
        self.files_resaved = 0  # Files actually re-saved to disk

    @classmethod
    def set_arguments(cls, parser):
        super().set_arguments(parser)

        parser.add_argument(
            "target",
            help="File(s) or folder(s) to target",
            nargs="+",
        )
        parser.add_argument(
            "--check",
            help="Do not modify files on disk, but give a non-zero exit code if there "
            "would be changes",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "-r",
            "--recursive",
            help="Also target folder (and their files) inside a target folder",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "--filter",
            help="Target files only with these patterns",
            nargs="+",
            default=cls.FILTER_DEFAULT,
        )

        return parser

    @staticmethod
    def get_xml_header(file: str) -> Optional[str]:
        """Get raw XML header as string."""
        with open(file, "r") as fh:
            # Search only the start of the path, otherwise give up
            for _ in range(100):
                line = fh.readline()
                if line.startswith("<?xml") and line.rstrip().endswith("?>"):
                    return line.strip()

        return None

    def get_xml_tree(self, path: str) -> ElementTree:
        """Get parsed XML path."""
        tree = etree.parse(path, self.xml_parser)

        self.header_before = self.get_xml_header(path)

        return tree

    def find_files(self) -> List[Path]:
        """Use argparse arguments to get a set of target files."""
        files = []
        if not self.args.target:
            return files

        for target in self.args.target:
            path = Path(target).resolve()
            if path.is_file():
                files.append(path)
            elif path.is_dir():
                if self.args.filter:
                    for filt in self.args.filter:
                        if self.args.recursive:
                            filt = f"**/{filt}"
                        files += path.glob(filt)
            else:
                raise ValueError(f"Could not find path or folder: `{target}`")

        return files
