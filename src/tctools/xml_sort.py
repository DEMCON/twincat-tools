import sys
from pathlib import Path
import logging

from .common import common_argparser
from .xml_sort_class import XmlSorter, logger


def parse_arguments(args):
    """Parse CLI arguments for this entrypoint."""
    parser = common_argparser()
    parser.description = "Alphabetically sort the nodes in an XML file."
    parser.epilog = (
        "Example: [program] --folder src --ext tsproj xti plcproj --skip-nodes "
        "Device ./MyTwinCATProject"
    )

    parser.add_argument(
        "-n",
        "--skip-nodes",
        nargs="+",
        help="Do not touch the attributes and sub-nodes of nodes with these names",
    )
    parser.add_argument(
        "--dry",
        help="Do not modify files on disk, only report changes",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--check",
        help="Do not modify files on disk, but give a non-zero exit code if there "
        "would be changes",
        action="store_true",
        default=False,
    )

    return parser.parse_args(args)


def main(*args) -> int:
    arguments = parse_arguments(args)

    logging.basicConfig(stream=sys.stdout)
    if arguments.loglevel:
        logger.setLevel(arguments.loglevel)

    sorter = XmlSorter(
        quiet=arguments.quiet,
        resave=not arguments.dry and not arguments.check,
        report=arguments.dry,
        skip_nodes=arguments.skip_nodes,
    )

    files = []

    if arguments.target:
        for target in arguments.target:
            path = Path(target).resolve()
            if path.is_file():
                files.append(path)
            elif path.is_dir():
                if arguments.filter:
                    for filt in arguments.filter:
                        if arguments.recursive:
                            filt = f"**/{filt}"
                        files += path.glob(filt)
            else:
                raise ValueError(f"Could not find file or folder: `{target}`")

    for path in files:
        sorter.sort_file(str(path))

    logger.info(f"Checked {sorter.files_checked} file(s)")

    if arguments.check:
        if sorter.files_to_alter == 0:
            logger.info(f"No changes to be made in checked files!")
            return 0

        logger.info(f"{sorter.files_to_alter} file(s) can be re-sorted")
        return 1

    logger.info(f"Re-saved {sorter.files_resaved} file(s)")
    return 0


if __name__ == "__main__":
    exit_code = main(*sys.argv[1:])  # Skip script name
    exit(exit_code)
