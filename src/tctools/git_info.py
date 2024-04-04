import sys
from argparse import ArgumentParser


from .git_info_class import GitInfo


def parse_arguments(args):
    """Parse CLI arguments for this entrypoint."""
    parser = ArgumentParser()
    parser.description = "Create a new file with version info from Git from a template."
    parser.epilog = "Example: [program] Version.TcGVL"

    parser.add_argument(
        "template",
        help="Template file to be used for newly created file",
    )

    parser.add_argument(
        "--output",
        help="File path for the new output file (default: template file with the "
        "last extension stripped)",
        default=None,
    )

    parser.add_argument(
        "--repo",
        help="Path to use for the Git repository (default: use the first repository up "
        "from the template file)",
        default=None,
    )

    parser.add_argument(
        "--dry",
        help="Output new file to CLI instead of writing to disk.",
        action="store_true",
        default=False,
    )

    return parser.parse_args(args)


def main(*args) -> int:
    arguments = parse_arguments(args)

    info = GitInfo(dry=arguments.dry)

    info.make_file(arguments.template, arguments.output, arguments.repo)

    return 0


def main_argv():
    """Entrypoint for the executable, defined through ``pyproject.toml``."""
    exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    exit_code = main(*sys.argv[1:])  # Skip script name
    exit(exit_code)
