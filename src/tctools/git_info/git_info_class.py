import re
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Optional, Set

from git import GitCommandError, Repo

from ..common import Tool


class GitSetter:
    """Helper class that uses properties to expose parsed Git info.

    This is a separate class to control protected methods.

    The 'dirty' feature by Git is modified to ignore some changed files for the
    dirty-state.
    """

    _EMPTY = "[empty]"
    _DATETIME_FORMAT = "%d-%m-%Y %H:%M:%S"

    def __init__(
        self, repo: Repo, logger: Logger, tolerate_dirty: Optional[Set[Path]] = None
    ):
        self._repo: Repo = repo
        self._logger = logger
        self._tolerate_dirty = {p.absolute() for p in tolerate_dirty}
        self._is_empty: bool = False

        try:
            _ = self._repo.head.object
        except ValueError as err:
            self._logger.warning(f"Repository is probably empty: {err}")
            self._is_empty = True

    @property
    def empty(self) -> bool:
        return self._is_empty

    def keyword_replace(self, match) -> str:
        """Callback for regex replacement."""
        keyword: str = match.group(1)  # Skipping the "{{" and "}}"

        if keyword.startswith("GIT_"):
            # Get value through local property
            if self._is_empty:
                return self._EMPTY
            try:
                return getattr(self, keyword.lower())
            except GitCommandError as err:
                self._logger.warning(f"Error in keyword '{keyword}': {err}")
                return self._EMPTY

        if keyword.startswith("git "):
            # Run function instead
            commands_str = keyword[4:]  # Strip "git "
            commands = commands_str.split(" ")
            func = getattr(self._repo.git, commands[0])  # Retrieve function handle
            return func(*commands[1:])  # Call, passing in remaining words as arguments

        raise ValueError(f"Unrecognized class of placeholder: {keyword}")

    def _exempt_dirty(self) -> bool:
        """

        :return: `True` if all modified files are in the tolerate list
                 Will return `False` if files were only created/deleted
        """
        if not self._tolerate_dirty:
            return False  # No extra info

        repo_path = Path(self._repo.working_dir).absolute()

        exempt = False
        for item in self._repo.index.diff(None):
            if item.change_type != "M":
                continue  # Only for modified files

            diff_path = repo_path / Path(item.a_path)
            if diff_path not in self._tolerate_dirty:
                return False  # Modified file that we're not exempting, 'dirty' is real

            exempt = True

        return exempt

    @property
    def git_hash(self) -> str:
        return self._repo.head.object.hexsha

    @property
    def git_hash_short(self) -> str:
        return self.git_hash[:8]

    @property
    def git_date(self) -> str:
        return self._repo.head.object.committed_datetime.strftime(self._DATETIME_FORMAT)

    @property
    def git_now(self) -> str:
        """Technically not a Git command at all, but useful anyway."""
        return datetime.now().strftime(self._DATETIME_FORMAT)

    @property
    def git_tag(self) -> str:
        """Get the last most relevant tag to the current commit."""
        # Getting the most relevant tag through `self._repo` is not so straightforward
        # Easier to get it with `describe`
        return self._repo.git.describe("--tags", "--abbrev=0")

    @property
    def git_version(self) -> str:
        """Use `git_tag` but parse the three version digits."""
        tag = self.git_tag
        re_version = re.compile(r"\d+\.\d+\.+\d+")
        match = re_version.search(tag)
        if not match:
            return "0.0.0"

        return match.group()

    @property
    def git_branch(self) -> str:
        try:
            return self._repo.active_branch.name
        except TypeError as err:
            if "HEAD is a detached" not in str(err):
                raise  # Re-raise error again, can't handle this

            return self._EMPTY  # In detached head, current branch is not valid

    @property
    def git_description(self):
        return self._repo.git.describe("--tags", "--always")

    @property
    def git_description_dirty(self):
        txt: str = self._repo.git.describe("--tags", "--always", "--dirty")
        if self._exempt_dirty():
            txt = txt.replace("-dirty", "")
        return txt

    @property
    def git_dirty(self) -> str:
        return "1" if self._repo.is_dirty() and not self._exempt_dirty() else "0"


class GitInfo(Tool):
    """Class to insert Git version info into a template.

    We use template keys in the source file like ``{{key}}``.
    This is done to avoid conflicts with TwinCAT source files. e.g. ``<key>`` might
    collide with XML brackets in ``$key`` the dollar sign is a key for string constants.
    """

    LOGGER_NAME = "git_info"

    CONFIG_KEY = "git_info"

    PATH_VARIABLES = ["template", "tolerate_dirty"]

    def __init__(self, *args):
        super().__init__(*args)

        self._re_keyword = re.compile(r"{{([^}]+)}}")

    @classmethod
    def set_arguments(cls, parser):
        super().set_arguments(parser)

        parser.description = (
            "Create a new file with version info from Git from a template."
        )
        parser.epilog = "Example: ``tc_git_info Version.TcGVL.template``"
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
            help="Path to use for the Git repository (default: "
            "use the first repository up from the template file)",
            default=None,
        )
        parser.add_argument(
            "--tolerate-dirty",
            "-t",
            help="Paths to files that are allowed to be modified without showing the "
            "'dirty' flag",
            action="append",
            type=str,
            default=[],
        )
        return parser

    def run(self) -> int:
        """Produce an info file based on template.

        This is largely a copy of https://github.com/RobertoRoos/git-substitute.
        This DRY violation is accepted to prevent a code dependency.
        """

        template_path = Path(self.args.template)

        with template_path.open("r", newline="") as fh:
            content = fh.read()  # Preserve line endings

        self.logger.debug(f"Read file `{template_path.absolute()}`")

        repo_path = Path(self.args.repo) if self.args.repo else template_path.parent

        repo = Repo(repo_path, search_parent_directories=True)

        git_setter = GitSetter(
            repo,
            logger=self.logger,
            tolerate_dirty={Path(f) for f in self.args.tolerate_dirty},
        )

        # Perform placeholder substitution:
        content, keywords_used = self._re_keyword.subn(
            git_setter.keyword_replace, content
        )

        # Now fix escaped characters:
        content = content.replace(r"\{\{", "{{").replace(r"\}\}", "}}")

        self.logger.info(f"Applied {keywords_used} keyword(s) to template")

        if self.args.dry:
            print(content)
            return 0

        if self.args.output is None:
            if not template_path.suffix:
                self.logger.warning("Template file does not have a double extension")

            output_path = template_path.with_suffix("")
        else:
            output_path = Path(self.args.output)

        if keywords_used == 0:
            self.logger.error("Couldn't find any keywords to replace in template")
            return 1

        with open(output_path, "w", newline="") as fh:
            fh.write(content)

        self.logger.debug(f"Wrote to file `{output_path.absolute()}`")
        return 0
