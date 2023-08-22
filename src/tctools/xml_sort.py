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

    parser.add_argument("-f", "--file", action="append", help="Target a specific file")

    return parser.parse_args(args if args else sys.argv)


def main(*args):
    arguments = parse_arguments(args)

    sorter = XmlSorter()
    sorter.sort_file(arguments.file[0])


if __name__ == "__main__":
    main(sys.argv)
