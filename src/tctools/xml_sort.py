import sys

from .common import common_argparser
from .xml_sort_class import XmlSorter


def parse_arguments(args):
    """Parse CLI arguments for this entrypoint."""
    parser = common_argparser()
    parser.description = "Alphabetically sort the nodes in an XML file."
    parser.epilog = (
        "Example: [program] --ext tsproj xti plcproj --skip-nodes "
        "Device ./MyTwinCATProject"
    )

    parser.add_argument(
        "-n",
        "--skip-nodes",
        nargs="+",
        help="Do not touch the attributes and sub-nodes of nodes with these names",
    )

    return parser.parse_args(args if args else sys.argv)


def main(*args):
    arguments = parse_arguments(args)

    sorter = XmlSorter(
        quiet=arguments.quiet,
        skip_nodes=arguments.skip_nodes,
    )

    for file in arguments.files:
        sorter.sort_file(file)


if __name__ == "__main__":
    main(sys.argv)
