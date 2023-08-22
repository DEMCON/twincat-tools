from typing import Optional
from argparse import ArgumentParser


def common_argparser(parser: Optional[ArgumentParser] = None) -> ArgumentParser:
    """Create CLI argument parser with common options."""
    if parser is None:
        parser = ArgumentParser()

    parser.add_argument(
        "-q",
        "--quiet",
        help="Do not provide any CLI output",
        action="store_true",
        default=False,
    )
    parser.add_argument("-f", "--files", action="append", help="Target a specific file")
    # parser.add_argument("--project", help="Path to .plcproj files to target")

    return parser
