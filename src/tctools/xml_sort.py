import sys
from argparse import ArgumentParser

from .xml_sort_class import XmlSorter


def main(*args) -> int:
    sorter = XmlSorter(*args)
    return sorter.run()


def main_argv():
    """Entrypoint for the executable, defined through ``pyproject.toml``."""
    exit(main(*sys.argv[1:]))


def get_parser():
    parser = ArgumentParser()
    return XmlSorter.set_arguments(parser)


if __name__ == "__main__":
    exit_code = main(*sys.argv[1:])  # Skip script name
    exit(exit_code)
