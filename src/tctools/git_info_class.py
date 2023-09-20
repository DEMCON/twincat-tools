from typing import Optional, Dict
from git import Repo
import os.path
from logging import getLogger


logger = getLogger("formatter")


class GitInfo:
    """Class to insert Git version info into a template."""

    def __init__(self, dry=False):
        self.dry = dry

    def make_file(
        self, template_path: str, output_path: Optional[str], repo_path: Optional[str]
    ):
        """Produce an info file based on template."""

        with open(template_path, "r") as fh:
            content = "".join(fh.readlines())

        if repo_path is None:
            repo_path = os.path.abspath(os.path.dirname(template_path))

        repo = Repo(repo_path, search_parent_directories=True)

        info = self._get_info(repo)

        for name, text in info.items():
            find = "{{GIT_" + name + "}}"
            content = content.replace(find, text)

        if self.dry:
            print(content)
            return

        if output_path is None:
            output_path, _ = os.path.splitext(template_path)

            _, test_ext = os.path.splitext(output_path)
            if not test_ext:
                logger.warning("Template file does not have a double extension")

            with open(output_path, "wb") as fh:
                fh.write(content.encode())

    def _get_info(self, repo: Repo) -> Dict[str, str]:
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
