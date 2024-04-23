import sys

from .make_release_class import MakeRelease


def main(*args) -> int:
    releaser = MakeRelease(*args)
    return releaser.run()


def main_argv():
    """Entrypoint for the executable, defined through ``pyproject.toml``."""
    exit(main(*sys.argv[1:]))


def get_parser():
    return MakeRelease.get_argument_parser()


if __name__ == "__main__":
    exit_code = main(*sys.argv[1:])  # Skip script name
    exit(exit_code)
