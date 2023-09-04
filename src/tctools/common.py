from typing import Optional, List
from argparse import ArgumentParser, Namespace
from pathlib import Path
from lxml import etree
from abc import ABC


def common_argparser(parser: Optional[ArgumentParser] = None) -> ArgumentParser:
    """Create CLI argument parser with common options."""
    if parser is None:
        parser = ArgumentParser()

    parser.add_argument(
        "target",
        help="File or folder to target",
        nargs="+",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        help="Do not provide any CLI output",
        action="store_true",
        default=False,
    )
    # parser.add_argument("--project", help="Path to .plcproj files to target")
    parser.add_argument(
        "-r",
        "--recursive",
        help="Also target folder (and their files) inside a target folder",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--filter",
        help="Target files only with these extensions",
        nargs="+",
        default=["*.xml"],
    )
    parser.add_argument(
        "-l",
        "--log",
        dest="loglevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the print level verbosity",
    )

    return parser


def find_files(args: "Namespace") -> List[Path]:
    """User argparse arguments to get a set of target files."""
    files = []
    if not args.target:
        return files

    for target in args.target:
        path = Path(target).resolve()
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            if args.filter:
                for filt in args.filter:
                    if args.recursive:
                        filt = f"**/{filt}"
                    files += path.glob(filt)
        else:
            raise ValueError(f"Could not find file or folder: `{target}`")

    return files


class TcTool(ABC):
    """Base class for tools with shared functionality."""

    def __init__(self):

        # Preserve `CDATA` XML flags
        self.parser = etree.XMLParser(strip_cdata=False)

        self.header_before: Optional[str] = None  # Header of the last XML file

    @staticmethod
    def get_xml_header(file: str) -> Optional[str]:
        """Get raw XML header as string."""
        with open(file, "r") as fh:
            # Search only the start of the file, otherwise give up
            for _ in range(100):
                line = fh.readline()
                if line.startswith("<?xml") and line.rstrip().endswith("?>"):
                    return line.strip()

        return None

    def get_xml_tree(self, path: str):
        """Get parsed XML file."""
        tree = etree.parse(path, self.parser)

        self.header_before = self.get_xml_header(path)

        return tree
