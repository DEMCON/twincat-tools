import sys
from pathlib import Path

from .common import common_argparser
from .xml_sort_class import XmlSorter


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

    return parser.parse_args(args)


def main(*args):
    arguments = parse_arguments(args)

    sorter = XmlSorter(
        quiet=arguments.quiet,
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
                        files += path.glob(filt)
            else:
                raise ValueError(f"Could not find file or folder: `{target}`")

    for path in files:
        sorter.sort_file(str(path))


if __name__ == "__main__":
    main(*sys.argv[1:])  # Skip script name
