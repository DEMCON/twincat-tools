"""Re-format a TwinCAT source path.

The files are read line-by-line, not as XML as a whole. This will keep all non-code
segments entirely untouched.
"""

import sys

from .format_class import Formatter


def main(*args) -> int:
    formatter = Formatter(*args)
    return formatter.run()


def main_argv():
    """Entrypoint for the executable, defined through ``pyproject.toml``."""
    exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    exit_code = main(*sys.argv[1:])  # Skip script name
    exit(exit_code)
