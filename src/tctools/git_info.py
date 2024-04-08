import sys

from .git_info_class import GitInfo


def main(*args) -> int:
    info = GitInfo(*args)
    return info.run()


def main_argv():
    """Entrypoint for the executable, defined through ``pyproject.toml``."""
    exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    exit_code = main(*sys.argv[1:])  # Skip script name
    exit(exit_code)
