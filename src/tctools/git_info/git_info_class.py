from pathlib import Path
from typing import Dict

from git import GitCommandError, Repo

from ..common import Tool


class GitInfo(Tool):
    """Class to insert Git version info into a template.

    We use template keys in the source file like ``{{key}}``.
    This is done to avoid conflicts with TwinCAT source files. e.g. ``<key>`` might
    collide with XML brackets in ``$key`` the dollar sign is a key for string constants.
    """

    LOGGER_NAME = "git_info"

    CONFIG_KEY = "git_info"

    PATH_VARIABLES = ["template"]

    def __init__(self, *args):
        super().__init__(*args)

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
        return parser

    def run(self) -> int:
        """Produce an info file based on template."""

        template_path = Path(self.args.template)

        with template_path.open("r", newline="") as fh:
            content = fh.read()  # Preserve line endings

        self.logger.debug(f"Read file `{template_path.absolute()}`")

        repo_path = Path(self.args.repo) if self.args.repo else template_path.parent

        repo = Repo(repo_path, search_parent_directories=True)

        keywords_used = 0

        info = self._get_info(repo)
        for keyword, value in info.items():
            new_content = content.replace(f"{{{{GIT_{keyword}}}}}", value)
            if new_content != content:
                keywords_used += 1

            content = new_content

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

    def _get_info(self, repo: Repo) -> Dict[str, str]:
        try:
            git_hash = (repo.head.object.hexsha,)
        except ValueError as err:
            self.logger.warning("Repository is probably empty: " + str(err))
            git_hash = None

        if isinstance(git_hash, tuple):
            git_hash = git_hash[0]

        empty = "[empty]"

        branch = empty
        if git_hash:
            try:
                branch = repo.active_branch.name
            except TypeError:
                pass

        tag = ""
        if git_hash:
            try:
                tag = repo.git.describe("--tags")
            except (TypeError, GitCommandError):
                pass
        if not tag.strip():
            tag = empty

        return {
            "HASH": git_hash or empty,
            "HASH_SHORT": git_hash[:8] if git_hash else empty,
            "DATE": (
                repo.head.object.committed_datetime.strftime("%d-%m-%Y %H:%M:%S")
                if git_hash
                else empty
            ),
            "TAG": tag,
            "BRANCH": branch,
            "DESCRIPTION": (
                repo.git.describe("--tags", "--always") if git_hash else empty
            ),
            "DESCRIPTION_DIRTY": (
                repo.git.describe("--tags", "--dirty", "--always")
                if git_hash
                else empty
            ),
        }
