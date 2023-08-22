from typing import Optional
from argparse import ArgumentParser


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
