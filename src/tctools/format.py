import sys
from argparse import ArgumentParser

from .format_class import Formatter


def main(*args) -> int:
    formatter = Formatter(*args)
    return formatter.run()


def main_argv():
    """Entrypoint for the executable, defined through ``pyproject.toml``."""
    exit(main(*sys.argv[1:]))


def get_parser():
    parser = ArgumentParser()
    return Formatter.set_arguments(parser)


if __name__ == "__main__":
    exit_code = main(*sys.argv[1:])  # Skip script name
    exit(exit_code)
