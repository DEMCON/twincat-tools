import sys
import logging

from .common import common_argparser, find_files
from .xml_sort_class import XmlSorter, logger


def parse_arguments(args):
    """Parse CLI arguments for this entrypoint."""
    parser = common_argparser()
    parser.description = "Alphabetically sort the nodes in an XML path."
    parser.epilog = (
        "Example: [program] ./MyTwinCATProject -r --filter *.tsproj *.xti *.plcproj "
        "--skip-nodes Device DataType"
    )

    parser.add_argument(
        "--filter",
        help="Target files only with these patterns (default: .xml only)",
        nargs="+",
        default=["*.xml"],
    )
    parser.add_argument(
        "-n",
        "--skip-nodes",
        nargs="+",
        help="Do not touch the attributes and sub-nodes of nodes with these names",
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

    files = find_files(arguments)

    for file in files:
        sorter.sort_file(str(file))

    logger.info(f"Checked {sorter.files_checked} path(s)")

    if arguments.check:
        if sorter.files_to_alter == 0:
            logger.info("No changes to be made in checked files!")
            return 0

        logger.info(f"{sorter.files_to_alter} path(s) can be re-sorted")
        return 1

    logger.info(f"Re-saved {sorter.files_resaved} path(s)")
    return 0


if __name__ == "__main__":
    exit_code = main(*sys.argv[1:])  # Skip script name
    exit(exit_code)
