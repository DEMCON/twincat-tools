import sys

from .patch_plc_class import PatchPlc


def main(*args) -> int:
    patcher = PatchPlc(*args)
    return patcher.run()


def main_argv():
    """Entrypoint for the executable, defined through ``pyproject.toml``."""
    exit(main(*sys.argv[1:]))


def get_parser():
    return PatchPlc.get_argument_parser()


if __name__ == "__main__":
    exit_code = main(*sys.argv[1:])  # Skip script name
    exit(exit_code)
