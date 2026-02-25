import logging
import sys
from abc import ABC, abstractmethod
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from lxml import etree

from . import __version__

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python 3.10 and before doesn't have tomllib yet

# Create type hinting shortcuts:
Element = etree._Element  # noqa
ElementTree = etree._ElementTree  # noqa


# The result of a files argument - like: `provided_path: [files]`
FileGroups = Dict[Path, List[Path]]


# Path.glob() only allows symlink recursion from Python 3.13:
path_glob_symlinks = {} if sys.version_info < (3, 13) else {"recurse_symlinks": True}


class Tool(ABC):
    """Tools base class.

    ``argparse`` is done in the constructor, CLI arguments should be passed there.
    """

    LOGGER_NAME: Optional[str] = None

    # Default value for file filter argument:
    FILTER_DEFAULT: List[str]

    CONFIG_KEY: Optional[str] = None

    PATH_VARIABLES: List[str] = []  # Names of options that are considered file paths

    def __init__(self, *args):
        """Pass e.g. ``sys.args[1:]`` (skipping the script part of the arguments).

        :param args: See :meth:`set_arguments`
        """
        parser = self.get_argument_parser()

        # All the fields were are going to have in the arguments output:
        fields = {
            action.dest for action in parser._actions if action.dest != "help"  # noqa
        }

        self.config_file: Optional[Path] = None

        config = self.make_config()
        if self.CONFIG_KEY:
            config = config.get(self.CONFIG_KEY, {})

        # Change the default values of the parser to the config results:
        for key, value in config.items():
            if key not in fields:
                raise ValueError(
                    f"Config field `{key}` is not recognized as a valid option"
                )
            if key in self.PATH_VARIABLES:
                value = self._make_path_from_config(value)
                # We should treat these paths as relative to the config file, ignoring
                # the current working directory

            parser.set_defaults(**{key: value})

            for action in parser._actions:
                if action.dest == key:
                    action.required = False
                    # Unfortunately this wouldn't disable required flags yet

        # Now parse CLI options on top of file configurations:
        self.args: Namespace = parser.parse_args(args)

        # Only after parsing all arguments we can establish a logger,
        self.logger = self.get_logger()

        if self.config_file:
            # Use property for config file path so we can still log it now:
            self.logger.debug(f"Loading from config: {self.config_file}")

    @classmethod
    def get_argument_parser(cls) -> ArgumentParser:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        cls.set_arguments(parser)
        return parser

    @classmethod
    def set_arguments(cls, parser):
        """Create application-specific arguments."""
        parser.add_argument(
            "--version", "-V", action="version", version="%(prog)s " + __version__
        )
        parser.add_argument(
            "--dry",
            help="Do not modify files on disk, only report changes to be made",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "--log-level",
            "-l",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Set log level to change verbosity",
            default="INFO",
        )

    def make_config(self) -> Dict[str, Any]:
        """Get configuration from possible files."""
        config = {}
        self.config_file = self._find_files_upwards(
            Path.cwd(), ["tctools.toml", "pyproject.toml"]
        )
        if not self.config_file:
            return config

        with open(self.config_file, "rb") as fh:
            data = tomllib.load(fh)
            if "tctools" in data:
                config = data["tctools"]

        return config

    @classmethod
    def _find_files_upwards(
        cls, directory: Path, filenames: List[str]
    ) -> Optional[Path]:
        """Find a file with a given name in the directory or it's parents.

        First hit on any of the filenames is returned.
        """
        for option in ([directory], directory.parents):
            for test_dir in option:
                for filename in filenames:
                    test_path = test_dir / filename
                    if test_path.is_file():
                        return test_path

        return None

    def _make_path_from_config(self, path: Any) -> Path:
        """Turn a relative path from a config file into a global path.

        Otherwise, return it as-is.

        :param path: Config value, can be (list of) `Path` or `str`
        """

        def _fix_path(p):
            p = Path(p)
            if not p.is_absolute() and self.config_file:
                p = self.config_file.parent / p
            return p

        if isinstance(path, list):
            path = [_fix_path(p) for p in path]
        else:
            path = _fix_path(path)

        return path

    @abstractmethod
    def run(self) -> int:
        """Main tool execution."""

    def get_logger(self):
        """Get logger for this class."""
        logging.basicConfig(stream=sys.stdout)
        logger = logging.getLogger(self.LOGGER_NAME or __name__)
        if "log_level" in self.args and self.args.log_level:
            level = logging.getLevelName(self.args.log_level)
            logger.setLevel(level)

        return logger


class TcTool(Tool, ABC):
    """Base class for tools sharing TwinCAT functionality."""

    PATH_VARIABLES = ["target"]

    def __init__(self, *args):
        super().__init__(*args)

        # Preserve `CDATA` XML flags:
        self.xml_parser = etree.XMLParser(strip_cdata=False)

        self.header_before: Optional[str] = None  # Header of the last XML path

        self.files_checked = 0  # Files read by parser
        self.files_to_alter = 0  # Files that seem to require changes
        self.files_resaved = 0  # Files actually re-saved to disk

    @classmethod
    def set_arguments(cls, parser):
        super().set_arguments(parser)

        cls.set_main_argument(parser)

        parser.add_argument(
            "--check",
            help="Do not modify files on disk, but give a non-zero exit code if there "
            "would be changes",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "-r",
            "--recursive",
            help="Also target folder (and their files) inside a target folder",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "--filter",
            help="Target files only with these patterns",
            nargs="+",
            default=cls.FILTER_DEFAULT,
        )

        return parser

    @classmethod
    def set_main_argument(cls, parser):
        """First argument that's supplied.

        Separate method to allow overriding it.
        """
        parser.add_argument(
            "target",
            help="File(s) or folder(s) to target",
            nargs="+",
        )

    @staticmethod
    def get_xml_header(file: str) -> Optional[str]:
        """Get raw XML header as string."""
        with open(file, "r") as fh:
            # Search only the start of the path, otherwise give up
            for _ in range(100):
                line = fh.readline()
                if line.startswith("<?xml") and line.rstrip().endswith("?>"):
                    return line.strip()

        return None

    def get_xml_tree(self, path: str | Path) -> ElementTree:
        """Get parsed XML path."""
        tree = etree.parse(path, self.xml_parser)

        self.header_before = self.get_xml_header(path)

        return tree

    @classmethod
    def find_files(
        cls,
        targets: str | List[str],
        filters: None | List[str] = None,
        recursive: bool = True,
        skip_check: bool = False,
    ) -> FileGroups:
        """Find a set of files, based on one or more targets and an optional filter.

        The entire set will never contain duplicate files

        Returned dict looks like:
        {
            "given pattern 1": [file_1, folder/file2, etc.],
            "given pattern 2": ... ,
        }
        """
        files = {}
        if not targets:
            return files

        files_unique = set()  # Make sure we don't get duplicate paths here

        if isinstance(targets, (str, Path)):
            targets = [targets]

        def add_file(g: List[Path], f: Path):
            """Little local method to prevent duplicate paths."""
            if f not in files_unique:
                files_unique.add(f)
                g.append(f)

        for target in targets:
            path = Path(target)
            group = files.setdefault(path, [])
            path = path.resolve()  # Get absolute path, resolved e.g. `~`
            if skip_check or path.is_file():
                add_file(group, path)
            elif path.is_dir():
                if filters:
                    for filt in filters:
                        if recursive:
                            filt = f"**/{filt}"

                        for p in path.glob(filt, **path_glob_symlinks):
                            add_file(group, p)
                        # With `recurse_symlinks`, symlinks will be followed as if
                        # files/folders are really there
            else:
                raise ValueError(f"Could not find path or folder: `{target}`")

        return files

    def find_target_files(self) -> Generator[Path, None, None]:
        """Use argparse arguments to get a set of target files."""
        for group in self.find_files(
            self.args.target, self.args.filter, self.args.recursive
        ).values():
            yield from group
