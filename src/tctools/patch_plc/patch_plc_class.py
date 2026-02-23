from argparse import RawDescriptionHelpFormatter
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Set

from lxml import etree

from ..common import Element, TcTool


@dataclass
class FileItems:
    """A set of files and folders, typically grouped under one source input."""

    folders: Set[Path] = field(default_factory=set)
    files: Set[Path] = field(default_factory=set)

    def add(self, other: "FileItems"):
        self.folders |= other.folders
        self.files |= other.files

    def subtract(self, other: "FileItems"):
        self.folders = self.folders.difference(other.folders)
        self.files = self.files.difference(other.files)

    @staticmethod
    def merge(items: Iterable["FileItems"]) -> "FileItems":
        """Combined an iterator of FileItems into a single one."""
        summed = FileItems()
        for item in items:
            summed.add(item)

        return summed

    @staticmethod
    def intersection(a: "FileItems", b: "FileItems") -> "FileItems":
        return FileItems(
            folders=a.folders.intersection(b.folders),
            files=a.files.intersection(b.files),
        )


FileItemsGroups = Dict[Path, FileItems]


class PatchPlc(TcTool):
    """Function code for PLc project patching."""

    LOGGER_NAME = "patch_plc"

    # TwinCAT PLC source files:
    FILTER_DEFAULT: List[str] = [
        "*.TcPOU",
        "*.TcGVL",
        "*.TcDUT",
        "*.TcGTLO",
        "*.TcIO",
        "*.TcTLEO",
    ]

    CONFIG_KEY = "patch_plc"

    def __init__(self, *args):
        super().__init__(*args)

        self._project_file: Path | None = None

        # The XML elements for files and folders:
        self._element_files: Element | None = None
        self._element_folders: Element | None = None

    @classmethod
    def set_arguments(cls, parser):

        parser.formatter_class = RawDescriptionHelpFormatter

        super().set_arguments(parser)

        parser.prog = "tc_patch_plc"
        parser.description = """Add or remove existing files to a PLC project

Types of action to take with the provided files:
merge:      Add any files/folders that are not yet registered
reset:      Replace ALL registered files/folders under the given path(s) by the
            provided ones
            Note: provided folders will be deleted whole from the project, regardless
            of items present on the filesystem!
remove:     Remove the provided files/folders without adding anything"""
        parser.epilog = "Example: ``tc_patch_plc ./MyPLC.plcproj -r POUs/Generated/``"

        parser.add_argument(
            "source",
            help="File(s) or folder(s) with PLC source to add to the project",
            nargs="+",
        )
        parser.add_argument(
            "--ignore",
            help="File(s) to ignore on the filesystem (filenames are only matched "
            "exactly!)",
            nargs="+",
            default=[],
        )
        return parser

    @classmethod
    def set_main_argument(cls, parser):
        parser.add_argument(
            "project",
            help="Path to the PLC project (typically '.plcproj')",
        )
        parser.add_argument(
            "operation",
            help="Type of action to take (see description)",
            choices=[v.name.lower() for v in Operation],
        )

    def run(self) -> int:
        """Perform actual patching."""
        operation = Operation[self.args.operation.upper()]

        input_sources = self.find_files(
            self.args.source,
            self.args.filter,
            self.args.recursive,
            skip_check=(operation == Operation.REMOVE),
        )

        self._project_file = Path(self.args.project).resolve()
        if not self._project_file.is_file():
            raise ValueError(f"Project file {self._project_file} does not exist")

        new_sources: FileItemsGroups = {}
        for key, files in input_sources.items():
            if operation == Operation.REMOVE:
                new_sources[key] = FileItems()
            else:
                new_sources[key] = self.determine_source_folders(files)
                # ^ also includes the ignore pattern

        project_tree = self.get_xml_tree(self._project_file)

        current_sources = self.get_project_sources(project_tree)

        rcode = operation(
            self,
            current_sources,
            new_sources,
        )
        if rcode is not None:
            return rcode  # Early return

        # Re-indent by a double space
        etree.indent(project_tree, space="  ", level=0)

        if self.args.dry:
            return 0  # Skip saving to file

        # Actually commit to the file now:

        with open(self._project_file, "wb") as fh:
            project_tree.write(fh)

        self.logger.info(f"Re-wrote file {self._project_file}")
        return 0

    def operation_merge(
        self,
        current_sources: FileItems,
        new_sources: FileItemsGroups,
    ) -> int | None:
        """See help info for `merge`."""
        new_sources = FileItems.merge(new_sources.values())

        sizes_all = (len(new_sources.folders), len(new_sources.files))

        new_sources.subtract(current_sources)

        self.logger.info(
            f"Discovered {sizes_all[1]} source files, of which "
            f"{len(new_sources.files)} are unregistered"
        )
        self.logger.info(
            f"Discovered {sizes_all[0]} source (sub-)folders, of which "
            f"{len(new_sources.folders)} are unregistered"
        )

        # Decide what to do next:
        if not new_sources.files and not new_sources.folders:
            self.logger.info("No new source files or folders, stopping")
            return 0

        if self.args.check:
            self.logger.info("Some file or folders would be added")
            return 1  # Something left to do, so exit with error (= check has failed)

        self.xml_add_sources(new_sources)
        return None

    def operation_remove(
        self, current_sources: FileItems, new_sources: FileItemsGroups
    ):
        """See help info for `remove`."""

        sizes_all = (len(current_sources.folders), len(current_sources.files))
        to_remove = FileItems()

        remove_items = [to_remove.files]
        sources_items = [current_sources.files]
        if self.args.recursive:  # Don't touch folders without `-r`
            remove_items.append(to_remove.folders)
            sources_items.append(current_sources.folders)

        for remove_list, sources_list in zip(remove_items, sources_items):
            for item in sources_list:
                for target in new_sources.keys():
                    if item == target or (
                        self.args.recursive and item.is_relative_to(target)
                    ):  # Exact match without `-r`, also relative with
                        remove_list.add(item)

        self.logger.info(
            f"{sizes_all[1]} registered source files, of which "
            f"{len(to_remove.files)} will be unregistered"
        )
        self.logger.info(
            f"{sizes_all[0]} registered source (sub-)folders, of which "
            f"{len(to_remove.folders)} will be unregistered"
        )

        # Decide what to do next:
        if not to_remove.files and not to_remove.folders:
            self.logger.info("No files or folders to un-register, stopping")
            return 0

        if self.args.check:
            self.logger.info("Some file or folders would be un-registered")
            return 1  # Something left to do, so exit with error (= check has failed)

        self.xml_remove_source(to_remove)
        return None

    def operation_reset(self, *args):
        return 1

    def determine_source_folders(self, source_files: Iterable[Path]) -> FileItems:
        """Collect all folders (incl. intermediate folders) of files.

        Also turn files into a neat relative path, w.r.t. the project file.
        Relies on `self._project_file`.
        """
        sources = FileItems()
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
                if relative_path.name in self.args.ignore:
                    continue  # Skip this file if the name matches exactly

                sources.files.add(relative_path)
                for folder in reversed(relative_path.parents):
                    if not folder.name:  # "./" is typically the first parent
                        continue

                    sources.folders.add(folder)  # Use a set to skip duplicates

            self.logger.debug(f"Found source file: {file}")

        return sources

    def get_project_sources(self, tree) -> FileItems:
        """Get all files and folders currently in a PLC project."""

        sources = FileItems()

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
                    sources.files.add(Path(path_str))
                elif item.tag.endswith("Folder"):
                    if self._element_folders is None:
                        self._element_folders = item_group
                    path_str = item.attrib.get("Include")
                    sources.folders.add(Path(path_str))
                # Skip other types

        return sources

    def xml_add_sources(self, sources: FileItems):
        """Modify the files and folders elements in-place."""
        for folder in sources.folders:
            folder_str = str(folder).replace("/", "\\")
            # On Linux the above will have the wrong slashes
            xml = f'<Folder Include="{folder_str}"/>'
            self._element_folders.append(etree.XML(xml))

        for file in sources.files:
            file_str = str(file).replace("/", "\\")
            xml = f'<Compile Include="{file_str}"><SubType>Code</SubType></Compile>'
            self._element_files.append(etree.XML(xml))

    def xml_remove_source(self, to_remove: FileItems):
        """Modify the files and folders elements in-place."""
        for element in self._element_folders:
            if Path(element.attrib["Include"]) in to_remove.folders:
                self._element_folders.remove(element)

        for element in self._element_files:
            if Path(element.attrib["Include"]) in to_remove.files:
                self._element_files.remove(element)


class Operation(Enum):
    MERGE = (PatchPlc.operation_merge,)
    RESET = (PatchPlc.operation_reset,)
    REMOVE = (PatchPlc.operation_remove,)

    def __call__(self, *args, **kwargs) -> Any:
        """Call the method of the enum value."""
        return self.value[0](*args, **kwargs)
