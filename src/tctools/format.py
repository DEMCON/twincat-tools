import sys

from .common import common_argparser


def parse_arguments(args):
    """Parse CLI arguments for this entrypoint."""
    parser = common_argparser()
    parser.description = "Format the PLC code inside a TwinCAT source XML file."
    parser.epilog = "Example: ..."

    return parser.parse_args(args if args else sys.argv)


def main(*args) -> int:
    arguments = parse_arguments(args)
    return 0


if __name__ == "__main__":
    exit_code = main(*sys.argv[1:])  # Skip script name
    exit(exit_code)
