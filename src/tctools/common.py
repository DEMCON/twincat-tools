from typing import Optional, List
from argparse import ArgumentParser
from pathlib import Path


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


def find_files(args: "Namespace") -> List[str]:
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


class TcTool:
    """Base class for tools with shared functionality."""
