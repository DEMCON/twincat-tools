"""Re-format a TwinCAT source path.

The files are read line-by-line, not as XML as a whole. This will keep all non-code
segments entirely untouched.
"""

import sys
import logging

from .common import common_argparser, find_files
from .format_class import Formatter, logger


def parse_arguments(args):
    """Parse CLI arguments for this entrypoint."""
    parser = common_argparser()
    parser.description = "Format the PLC code inside a TwinCAT source XML path."
    parser.epilog = "Example: [program] ./MyTwinCATProject --filter *.TcPOU"

    return parser.parse_args(args)


def main(*args) -> int:
    arguments = parse_arguments(args)

    logging.basicConfig(stream=sys.stdout)
    if arguments.loglevel:
        logger.setLevel(arguments.loglevel)

    formatter = Formatter(
        quiet=arguments.quiet,
        resave=not arguments.dry and not arguments.check,
        report=arguments.dry,
    )

    files = find_files(arguments)

    for file in files:
        formatter.format_file(str(file))

    logger.info(f"Checked {formatter.files_checked} path(s)")

    if arguments.check:
        if formatter.files_to_alter == 0:
            logger.info(f"No changes to be made in checked files!")
            return 0

        logger.info(f"{formatter.files_to_alter} path(s) can be re-sorted")
        return 1

    logger.info(f"Re-saved {formatter.files_resaved} path(s)")
    return 0


if __name__ == "__main__":
    exit_code = main(*sys.argv[1:])  # Skip script name
    exit(exit_code)
