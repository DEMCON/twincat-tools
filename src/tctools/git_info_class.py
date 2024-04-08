from typing import Dict
from git import Repo
from pathlib import Path
from logging import getLogger

from .common import Tool


logger = getLogger("formatter")


class GitInfo(Tool):
    """Class to insert Git version info into a template."""

    def __init__(self, *args):
        super().__init__(*args)

    @staticmethod
    def set_arguments(parser):
        parser.description = (
            "Create a new file with version info from Git from a template."
        )
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
            help="Path to use for the Git repository (default: "
            "use the first repository up "
            "from the template file)",
            default=None,
        )

        parser.add_argument(
            "--dry",
            help="Output new file to CLI instead of writing to disk.",
            action="store_true",
            default=False,
        )

    def run(self) -> int:
        """Produce an info file based on template."""

        template_path = Path(self.args.template)

        with template_path.open("r") as fh:
            content = "".join(fh.readlines())

        self.logger.debug(f"Read file {template_path.absolute()}")

        repo_path = Path(self.args.repo) if self.args.repo else template_path.parent

        repo = Repo(repo_path, search_parent_directories=True)

        info = self._get_info(repo)

        for name, text in info.items():
            find = "{{GIT_" + name + "}}"
            content = content.replace(find, text)

        if self.args.dry:
            print(content)
            return 0

        if self.args.output is None:
            if not template_path.suffix:
                logger.warning("Template file does not have a double extension")

            output_path = template_path.with_suffix("")
        else:
            output_path = Path(self.args.output)

        with open(output_path, "wb") as fh:
            fh.write(content.encode())

        return 0

    @staticmethod
    def _get_info(repo: Repo) -> Dict[str, str]:
        info = {}

        try:
            git_hash = (repo.head.object.hexsha,)
        except ValueError as err:
            logger.warning("Repository is probably empty: " + str(err))
            empty = "<empty>"
            return {
                "HASH": empty,
                "HASH_SHORT": empty,
                "DATE": empty,
                "TAG": empty,
                "BRANCH": empty,
                "DESCRIPTION": empty,
                "DESCRIPTION_DIRTY": empty,
            }

        if isinstance(git_hash, tuple):
            git_hash = git_hash[0]

        info["HASH"] = git_hash
        info["HASH_SHORT"] = git_hash[:8]
        info["DATE"] = repo.head.object.committed_datetime.strftime("%d-%m-%Y %H:%M:%S")
        info["TAG"] = repo.git.tag()
        info["BRANCH"] = repo.active_branch.name
        info["DESCRIPTION"] = repo.git.describe("--tags", "--always")
        info["DESCRIPTION_DIRTY"] = repo.git.describe("--tags", "--dirty", "--always")

        return info
