from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
from git import Repo

from .common import Tool


class MakeRelease(Tool):
    """Tool to create a release archive from a TwinCAT project."""

    def set_arguments(self, parser):
        super().set_arguments(parser)
        parser.description = """Create a release archive from the current project.

Archives the compiled result of PlC and HMI projects.
Checks can be performed to make sure the binaries work on a target PLC.

The resulting archive will be named after the PLC project.
"""

        parser.add_argument(
            "plc_source",
            metavar="plc-source",
            help="Path where to search for compilation directory of PLC project",
        )

        parser.add_argument(
            "--destination",
            help="Folder where release output will be saved (default: ./deploy)",
            default="deploy",
        )

        parser.add_argument(
            "--hmi-source",
            help="Path where to search for compilation directory of HMI project",
            default=None,
        )

        parser.add_argument(
            "--platform",
            help="Target platform for PLC to copy (default: `x64`",
            default="x64",
        )

    def run(self) -> int:
        """Create release archive."""
        source_dir = Path(self.args.plc_source)

        repo = Repo(source_dir, search_parent_directories=True)
        repo_dir = Path(repo.git_dir).parent

        self.logger.debug(f"Found Git repository `{repo_dir}`")

        version = repo.git.tag()
        if not version:
            self.logger.warning(f"Could not find any tags in `{repo}`")
            version = "v0.0.0"

        self.logger.info(f"Making release for tag `{version}`")

        destination_dir = Path(self.args.destination).absolute()

        if not destination_dir.is_dir():
            destination_dir.mkdir(parents=True)

        self.logger.debug(f"Going to make release in `{destination_dir}`")

        boot_paths = source_dir.rglob(f"_Boot/*({self.args.platform})")
        boot_dir = next(boot_paths)
        self.logger.debug(f"Copying PLC boot files from `{boot_dir}")

        plc_paths = boot_dir.rglob("*.tpzip")
        plc_project = next(plc_paths)
        name = plc_project.stem.lower().replace(" ", "_")

        archive_file = destination_dir / f"{name}-{version}.zip"

        # Create self-deleting temporary folder inside the release directory:
        with TemporaryDirectory(dir=destination_dir.parent) as temp_dir_str:
            temp_dir = Path(temp_dir_str)

            # Copy entire boot directory content to new folder
            archive_source = temp_dir / "release"
            shutil.copytree(boot_dir, archive_source / "PLC", dirs_exist_ok=True)

            # Unpack CurrentConfig from deploy into temp dir:
            shutil.unpack_archive(
                archive_source / "PLC" / "CurrentConfig.tszip",
                temp_dir / "CurrentConfig",
                format="zip",
            )

            # `make_archive` tends to add itself too, so create it outside the source:
            shutil.make_archive(
                str(archive_file.with_suffix("")), "zip", archive_source
            )

        return 0
