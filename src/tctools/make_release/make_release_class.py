import re
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

from git import Repo
from lxml import etree

from ..common import Tool

ElementTree = etree._ElementTree  # noqa
Element = etree._Element  # noqa


class MakeRelease(Tool):
    """Tool to create a release archive from a TwinCAT project."""

    LOGGER_NAME = "make_release"

    CONFIG_KEY = "make_release"

    def __init__(self, *args):
        super().__init__(*args)

        # Bunch of attributes to easily share data between methods:
        self.version: Optional[str] = None
        self.destination_dir: Optional[Path] = None
        self.archive_source: Optional[Path] = None
        self.config_dir: Optional[Path] = None

    @classmethod
    def set_arguments(cls, parser):
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
            "--include-hmi",
            help="Also include HMI compilation in release (default: False)",
            default=False,
            action="store_true",
        )

        parser.add_argument(
            "--add-file",
            "-a",
            help="Add additional file to release package "
            "(<filepath> <relative path inside archive>)",
            default=None,
            nargs="+",  # Can be 1 or 2
            action="append",
        )

        parser.add_argument(
            "--platform",
            help="Target platform for PLC to copy (default: `x64`)",
            default="x64",
        )

        parser.add_argument(
            "--check-cpu",
            help="Validate the CPU configuration in the compiled project "
            "(<number of cores> <number of isolated cores>)",
            nargs=2,
            type=int,
            default=None,
        )

        parser.add_argument(
            "--check-devices",
            help="Validate devices, only the listed devices by name may be enabled",
            nargs="+",
            default=None,
        )

        parser.add_argument(
            "--check-version-variable",
            help="Validate current version in PLC source code in the given variable "
            "(<filename> <variable name>)",
            nargs=2,
            default=None,
        )

        parser.add_argument(
            "--check-version-hmi",
            help="Validate current version in HMI source code in the given object "
            "(<filename> <object id>)",
            nargs=2,
            default=None,
        )

    @staticmethod
    def glob_first(path: Path, pattern: str) -> Path:
        """Get the first glob result."""
        results = path.rglob(pattern)
        return next(results)

    def run(self) -> int:
        """Create release archive."""
        source_dir = Path(self.args.plc_source)

        repo = Repo(source_dir, search_parent_directories=True)
        repo_dir = Path(repo.git_dir).parent

        self.logger.debug(f"Found Git repository `{repo_dir}`")

        self.version = repo.git.tag()
        if not self.version:
            self.logger.warning(f"Could not find any tags in `{repo}`")
            self.version = "v0.0.0"

        self.logger.info(f"Making release for tag `{self.version}`")

        self.destination_dir = Path(self.args.destination).absolute()

        if not self.destination_dir.is_dir():
            self.destination_dir.mkdir(parents=True)

        self.logger.debug(f"Going to make release in `{self.destination_dir}`")

        pattern = f"_Boot/*({self.args.platform})"
        boot_dir = self.glob_first(source_dir, pattern)
        self.logger.debug(f"Copying PLC boot files from `{boot_dir}")

        plc_project = self.glob_first(boot_dir, "*.tpzip")
        name = plc_project.stem.lower().replace(" ", "_")

        hmi_bin_dir: Optional[Path] = None
        if self.args.include_hmi:
            html_file = self.glob_first(source_dir, "bin/*.html")
            hmi_bin_dir = html_file.parent

        archive_file = self.destination_dir / f"{name}-{self.version}.zip"
        if archive_file.is_file():
            raise RuntimeError(f"Target file `{archive_file}` already exists")

        # Create self-deleting temporary folder inside the release directory:
        with TemporaryDirectory(dir=self.destination_dir.parent) as temp_dir_str:
            temp_dir = Path(temp_dir_str)

            # Copy entire boot directory content to new folder
            self.archive_source = temp_dir / "release"
            shutil.copytree(boot_dir, self.archive_source / "PLC", dirs_exist_ok=True)

            # Also copy HMI bin directory:
            if hmi_bin_dir:
                shutil.copytree(
                    hmi_bin_dir,
                    self.archive_source / "HMI",
                    dirs_exist_ok=True,
                )

            errors = self.validate_release(temp_dir)
            for error in errors:
                self.logger.error(error)

            self.add_additional_files()

            if self.args.dry:
                return 0  # Don't make any more changes

            if errors:
                self.logger.error(
                    f"Not making release because of {len(errors)} failed check(s)"
                )
                return 1

            # `make_archive` tends to add itself too, so create it outside the source:
            shutil.make_archive(
                str(archive_file.with_suffix("")), "zip", self.archive_source
            )

        self.logger.info(f"Created file `{archive_file}`")
        return 0

    def add_additional_files(self):
        if not self.args.add_file:
            return

        for file_option in self.args.add_file:
            file_source = Path(file_option[0])
            if len(file_option) == 1:
                file_dest = file_source
            elif len(file_option) == 2:
                file_dest = Path(file_option[1])
            else:
                raise RuntimeError("`--add-file` argument must have 1 or 2 values")

            if file_dest.is_absolute():
                file_dest = file_dest.relative_to(Path.cwd())

            shutil.copy(file_source, self.archive_source / file_dest)

        return

    def validate_release(self, temp_dir: Path) -> List[str]:
        """

        :param temp_dir: Root of temporary directory
        """
        # Unpack CurrentConfig into temp dir:
        self.config_dir = temp_dir / "CurrentConfig"
        shutil.unpack_archive(
            self.archive_source / "PLC" / "CurrentConfig.tszip",
            self.config_dir,
            format="zip",
        )

        project_file = self.glob_first(self.config_dir, "*.tsproj")
        root = etree.parse(project_file)

        errors = []
        errors += self.check_cpu(root)
        errors += self.check_devices(root)
        errors += self.check_version_variable(temp_dir)
        errors += self.check_version_hmi()

        return errors

    def check_cpu(self, root: ElementTree) -> List[str]:
        """Validate CPU configuration."""
        if self.args.check_cpu is None:
            return []

        node: Element = root.xpath("//TcSmProject/Project/System/Settings")[0]
        cpus = [
            int(node.attrib[key]) if key in node.attrib else 0
            for key in ["MaxCpus", "NonWinCpus"]
        ]
        expected_cpus = self.args.check_cpu

        if cpus[0] != expected_cpus[0] or cpus[1] != expected_cpus[1]:
            return [
                f"Expected cpu configuration {expected_cpus}, but found {cpus} in "
                f"project file",
            ]

        return []

    def check_devices(self, root: ElementTree) -> List[str]:
        """Validate device configuration."""
        errors = []

        if self.args.check_devices is None:
            return errors

        devices: List[Element] = root.xpath("//TcSmProject/Project/Io/Device")

        for i, device in enumerate(devices):
            if "File" in device.attrib:  # Replace by file reference
                extra_file = self.glob_first(self.config_dir, device.attrib["File"])
                extra_root: ElementTree = etree.parse(extra_file)
                new_device: Element = extra_root.xpath("//TcSmItem/Device")[0]
                new_device.find("Name").text = device.attrib["File"].rstrip(".xti")
                devices[i] = new_device

        for device in devices:
            name = device.find("Name").text
            should_be_disabled = name not in self.args.check_devices
            is_disabled = device.attrib.get("Disabled", "false").lower() == "true"
            if should_be_disabled != is_disabled:
                msg = (
                    "disabled, but is enabled"
                    if should_be_disabled
                    else "enabled, but is disabled"
                )
                errors.append(f"Device `{name}` should be {msg}!")

        return errors

    def check_version_variable(self, temp_dir: Path) -> List[str]:
        """Validate the version variable matches the release version.

        :param temp_dir:
        """
        if self.args.check_version_variable is None:
            return []

        check_file, check_variable = self.args.check_version_variable

        plc_archive = self.glob_first(
            self.archive_source / "PLC" / "CurrentConfig",
            "*.tpzip",
        )
        # Unpack CurrentConfig/<plc>.tpzip into temp dir:
        plc_dir = self.config_dir / "plc"
        shutil.unpack_archive(plc_archive, plc_dir, format="zip")

        file = self.glob_first(plc_dir, check_file)
        pattern = re.compile(check_variable + r".*" + self.version.replace(".", r"\."))

        contents = file.read_text()
        matches = pattern.findall(contents)

        if not matches:
            return [
                f"Failed to find version `{self.version}` in code "
                f"`{check_file}:{check_variable}`"
            ]

        return []

    def check_version_hmi(self):
        """Validate version string inside HMI page."""
        if self.args.check_version_hmi is None:
            return []

        check_file, check_object = self.args.check_version_hmi

        file = self.glob_first(self.archive_source / "HMI", check_file)
        pattern = re.compile(check_object + r'.*data-tchmi-text="(.+?)"')
        # Use `+?` for lazy matching

        contents = file.read_text()
        for match in pattern.finditer(contents):
            if match.group(1) == self.version:
                return []
            return [
                f"Version in HMI `{check_file}:{check_object}` is "
                f"`{match.group(1)}`, not `{self.version}`"
            ]

        return [f"Failed to find HMI object `{check_object}` in `{check_file}`"]
