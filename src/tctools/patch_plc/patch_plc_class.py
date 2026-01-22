from pathlib import Path
from typing import Iterable, List, Set, Tuple

from lxml import etree

from ..common import Element, TcTool


class PatchPlc(TcTool):
    """Function code for PLc project patching."""

    LOGGER_NAME = "patch_plc"

    # TwinCAT PLC source files:
    FILTER_DEFAULT: List[str] = ["*.TcPOU", "*.TcGVL", "*.TcDUT"]

    CONFIG_KEY = "patch_plc"

    def __init__(self, *args):
        super().__init__(*args)

        self._project_file: Path | None = None

        # The XML elements for files and folders:
        self._element_files: Element | None = None
        self._element_folders: Element | None = None

    @classmethod
    def set_arguments(cls, parser):
        super().set_arguments(parser)

        parser.prog = "tc_patch_plc"
        parser.description = "Add or remove existing files to a PLC project."
        parser.epilog = "Example: ``tc_patch_plc ./MyPLC.plcproj -r POUs/Generated/``"

        parser.add_argument(
            "source",
            help="File(s) or folder(s) with PLC source to add to the project "
            "(=`target`)",
            nargs="+",
        )
        return parser

    def run(self) -> int:
        """Perform actual patching."""
        source_files = set(
            self.find_files(
                self.args.source,
                self.args.filter,
                self.args.recursive,
            )
        )

        target = self.args.target
        if not isinstance(target, (str, Path)):
            if len(target) != 1:
                raise ValueError("`target` must be exactly one project file")
            target = target[0]

        self._project_file = Path(target).resolve()
        if not self._project_file.is_file():
            raise ValueError(f"Project file {self._project_file} does not exist")

        # List of all source folders - including intermediate ones
        source_files, source_folders = self.determine_source_folders(source_files)

        project_tree = self.get_xml_tree(self._project_file)

        current_files, current_folders = self.get_files_and_folders(project_tree)

        new_source_files = source_files.difference(current_files)
        new_source_folders = source_folders.difference(current_folders)

        self.logger.info(
            f"Discovered {len(source_files)} source files, of which "
            f"{len(new_source_files)} are unregistered"
        )
        self.logger.info(
            f"Discovered {len(source_folders)} source (sub-)folders, of which "
            f"{len(new_source_folders)} are unregistered"
        )

        # Decide what to do next:
        if not new_source_files and not new_source_folders:
            self.logger.info("No new source files or folders, stopping")
            return 0

        if self.args.check:
            self.logger.info("Some file or folders would be added")
            return 1  # Something to do, exit with error (= check has failed)

        self.add_files_and_folders_to_xml(new_source_files, new_source_folders)

        # Re-indent by a double space
        etree.indent(project_tree, space="  ", level=0)

        if self.args.dry:
            return 0  # Skip saving to file

        # Actually commit to the file now:

        with open(self._project_file, "wb") as fh:
            project_tree.write(fh)

        self.logger.info(f"Re-wrote file {self._project_file}")
        return 0

    def determine_source_folders(
        self, source_files: Iterable[Path]
    ) -> Tuple[Set[Path], Set[Path]]:
        """Collect all folders (incl. intermediate folders) of files."""
        source_folders: Set[Path] = set()
        new_source_files: Set[Path] = set()
        project_dir = self._project_file.parent
        for file in source_files:
            try:
                relative_path = file.relative_to(project_dir)
            except ValueError:
                raise ValueError(
                    f"Source file `{file}` is not relative to project "
                    f"directory `{project_dir}`"
                )
            else:
                new_source_files.add(relative_path)
                for folder in reversed(relative_path.parents):
                    if not folder.name:  # "./" is typically the first parent
                        continue

                    source_folders.add(folder)  # Use a set to skip duplicates

            self.logger.debug(f"Found source file: {file}")

        return new_source_files, source_folders

    def get_files_and_folders(self, tree) -> Tuple[Set[Path], Set[Path]]:
        """Get all files and folders currently in a PLC project."""

        files = set()
        folders = set()

        # The project file has a "xmlns" defined, use a wildcard to ignore namespaces
        for item_group in tree.iterfind("ItemGroup", namespaces={"": "*"}):
            # We expect 4 instances of ItemGroup (in order): i) source files,
            # ii) source folders, iii) TMC files, iv) Library references
            # Except for the order and contents, we have no real way to distinguish
            # between these
            for item in item_group:
                if item.tag.endswith("Compile"):
                    if self._element_files is None:
                        self._element_files = item_group
                    path_str = item.attrib.get("Include")
                    files.add(Path(path_str))
                elif item.tag.endswith("Folder"):
                    if self._element_folders is None:
                        self._element_folders = item_group
                    path_str = item.attrib.get("Include")
                    folders.add(Path(path_str))
                # Skip other types

        return files, folders

    def add_files_and_folders_to_xml(
        self, files: Iterable[Path], folders: Iterable[Path]
    ):
        """Modify the files and folders elements in-place."""
        for folder in folders:
            self._element_folders.append(etree.XML(f'<Folder Include="{folder}"/>'))

        for file in files:
            self._element_files.append(
                etree.XML(
                    f'<Compile Include="{file}"><SubType>Code</SubType></Compile>'
                )
            )
