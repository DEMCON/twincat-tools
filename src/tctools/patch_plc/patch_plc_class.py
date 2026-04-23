import logging
from argparse import RawDescriptionHelpFormatter
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePath, PureWindowsPath
from typing import Any

from lxml import etree

from ..common import Element, TcTool


@dataclass
class FileItems:
    """A set of files and folders, typically grouped under one source input."""

    folders: set[Path] = field(default_factory=set)
    files: set[Path] = field(default_factory=set)

    def add(self, other: "FileItems"):
        """Merge in another set of files/folders."""
        self.folders |= other.folders
        self.files |= other.files

    def subtract(self, other: "FileItems"):
        """Remove files/folders that occur in another set."""
        self.folders = self.folders.difference(other.folders)
        self.files = self.files.difference(other.files)

    def is_empty(self) -> bool:
        """Return true if set contains nothing."""
        return not self.folders and not self.files

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


FileItemsGroups = dict[Path, FileItems]


class PatchPlc(TcTool):
    """Function code for PLc project patching."""

    LOGGER_NAME = "patch_plc"

    # TwinCAT PLC source files:
    FILTER_DEFAULT: list[str] = [
        "*.TcPOU",
        "*.TcGVL",
        "*.TcDUT",
        "*.TcGTLO",
        "*.TcIO",
        "*.TcTLEO",
        "*.TcTTO",  # Really a task, but tracked just like source
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
            help="Either a path to the PLC project or a folder containing a "
            "single '.plcproj' file",
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

        project_path = Path(self.args.project).resolve()
        if project_path.is_dir():  # Looks for a local project automatically
            results = list(project_path.glob("*.plcproj"))
            if len(results) == 0:
                raise RuntimeError(
                    f"Found no PLC project directly under '{project_path}'"
                )
            if len(results) > 1:
                raise RuntimeError(
                    f"Found multiple PLC projects directly under '{project_path}'"
                )
            project_path = Path(results[0])

        if not project_path.is_file():
            raise ValueError(f"Project file {project_path} does not exist")

        self._project_file: Path = project_path

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

        self.skip_file_duplicates(new_sources, current_sources)

        self.logger.info(
            f"Discovered {sizes_all[1]} source files, of which "
            f"{len(new_sources.files)} are unregistered"
        )
        self.logger.info(
            f"Discovered {sizes_all[0]} source (sub-)folders, of which "
            f"{len(new_sources.folders)} are unregistered"
        )

        # Decide what to do next:
        if new_sources.is_empty():
            self.logger.info("No new source files or folders, stopping")
            return 0

        self.log_sources(new_sources, True)

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
        to_remove = self.sources_to_remove(current_sources, new_sources)

        self.logger.info(
            f"{sizes_all[1]} registered source files, of which "
            f"{len(to_remove.files)} will be unregistered"
        )
        self.logger.info(
            f"{sizes_all[0]} registered source (sub-)folders, of which "
            f"{len(to_remove.folders)} will be unregistered"
        )

        # Decide what to do next:
        if to_remove.is_empty():
            self.logger.info("No files or folders to un-register, stopping")
            return 0

        self.log_sources(to_remove, False)

        if self.args.check:
            self.logger.info("Some file or folders would be un-registered")
            return 1  # Something left to do, so exit with error (= check has failed)

        self.xml_remove_source(to_remove)
        return None

    def operation_reset(self, current_sources: FileItems, new_sources: FileItemsGroups):
        """See help info for `reset`."""
        if not self.args.recursive:
            self.logger.warning(
                "reset operation can only work with the recursive option enabled"
            )
            return 1

        sizes_all = (len(current_sources.folders), len(current_sources.files))

        # All the registered sources underneath the user-given paths:
        to_remove = self.sources_to_remove(current_sources, new_sources)

        # All the sources on the filesystem under the user-given paths:
        to_add = FileItems.merge(new_sources.values())

        to_remove.subtract(to_add)  # Don't remove sources that are real
        to_add.subtract(current_sources)  # Don't add sources that are already known

        self.skip_file_duplicates(to_add, current_sources)

        # Empty folders will also be removed, make sure to keep them:
        to_remove.folders = set(
            f for f in to_remove.folders if not (self._project_file.parent / f).exists()
        )

        self.logger.info(
            f"{sizes_all[1]} registered source files, "
            f"{len(to_remove.files)} will be unregistered and {len(to_add.files)} will "
            f"be added"
        )
        self.logger.info(
            f"{sizes_all[0]} registered source (sub-)folders, "
            f"{len(to_remove.folders)} will be unregistered and {len(to_add.folders)} "
            f"will be added"
        )

        # Decide what to do next:
        if to_remove.is_empty() and to_add.is_empty():
            self.logger.info("No files or folders to change, stopping")
            return 0

        self.log_sources(to_add, True)
        self.log_sources(to_remove, False)

        if self.args.check:
            self.logger.info("Some file or folders would be (un-)registered")
            return 1  # Something left to do, so exit with error (= check has failed)

        self.xml_remove_source(to_remove)
        self.xml_add_sources(to_add)
        return None

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
                ) from None
            else:
                if relative_path.name in self.args.ignore:
                    continue  # Skip this file if the name matches exactly

                sources.files.add(relative_path)
                for folder in reversed(relative_path.parents):
                    if not folder.name:  # "./" is typically the first parent
                        continue

                    sources.folders.add(folder)
                    # Collection is a set to duplicates are skipped by default

            self.logger.debug(f"Found source file: {file}")

        return sources

    def skip_file_duplicates(
        self,
        new_sources: FileItems,
        current_sources: FileItems,
    ):
        """Avoid duplicate file names (regardless of full path).

        ``current_sources`` is modified in-place.
        """
        filenames = set(f.name for f in current_sources.files)  # Reduce to just names
        to_pop = set()
        for file in new_sources.files:
            if file.name in filenames:
                to_pop.add(file)
                self.logger.warning(f"Refusing to add existing file name: {file}")

        if to_pop:
            new_sources.files -= to_pop

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
                    ref_set = sources.files
                elif item.tag.endswith("Folder"):
                    if self._element_folders is None:
                        self._element_folders = item_group
                    ref_set = sources.folders
                else:
                    continue  # Skip other types

                path_str = item.attrib.get("Include")
                path = Path(PureWindowsPath(path_str))
                # In the XML there are always backslashes, force to native type
                ref_set.add(path)

        if self._element_files is None:  # Group doesn't yet exist, create it:
            # It must be the first of the <ItemGroup> set
            element_neighbour: Element = tree.find(
                "PropertyGroup", namespaces={"": "*"}
            )
            self._element_files = etree.XML("<ItemGroup></ItemGroup>")
            element_neighbour.addnext(self._element_files)

        if self._element_folders is None:
            self._element_folders = etree.XML("<ItemGroup></ItemGroup>")
            self._element_files.addnext(self._element_folders)

        return sources

    def sources_to_remove(
        self,
        current: FileItems,
        new_sources: FileItemsGroups,
    ) -> FileItems:
        """From a set of sources and CLI input, determine the sources to remove.

        Important: only the keys of `new_sources` are considered! I.e., the files to
        remove need not exist on the filesystem.

        listens to `self.args.recursive`.
        """
        to_remove = FileItems()

        project_folder = self._project_file.parent

        def remove_helper(remove_list, sources_list):
            for item in sources_list:
                for target in new_sources:
                    if target.is_absolute():
                        target = target.relative_to(project_folder)
                    if item == target or (
                        self.args.recursive and item.is_relative_to(target)
                    ):  # Exact match without `-r`, also relative with
                        remove_list.add(item)

        remove_helper(to_remove.files, current.files)
        if self.args.recursive:  # Don't touch folders without `-r`
            remove_helper(to_remove.folders, current.folders)

        return to_remove

    def xml_add_sources(self, sources: FileItems):
        """Modify the files and folders elements in-place."""

        def add_helper(ref_elements, ref_set, template):
            for item in ref_set:
                item_str = self.path_to_str(item)
                xml = template.format(item_str)
                ref_elements.append(etree.XML(xml))

        add_helper(
            self._element_folders,
            sources.folders,
            '<Folder Include="{}"/>',  # ...
        )
        add_helper(
            self._element_files,
            sources.files,
            '<Compile Include="{}"><SubType>Code</SubType></Compile>',
        )

    def xml_remove_source(self, to_remove: FileItems):
        """Modify the files and folders elements in-place."""

        def remove_helper(ref_elements, ref_set):
            for element in ref_elements:
                this_path = Path(PureWindowsPath(element.attrib["Include"]))
                # Force XML Windows path to native one
                if this_path in ref_set:
                    ref_elements.remove(element)

        remove_helper(self._element_folders, to_remove.folders)
        remove_helper(self._element_files, to_remove.files)

    def log_sources(self, source: FileItems, add: bool):
        """Log a set of sources in its entirety.

        Logged a INFO level when `dry` or `check` (otherwise the output is kind of
        meaningless), otherwise at DEBUG.
        """
        level = logging.INFO if self.args.check or self.args.dry else logging.DEBUG

        action = "New" if add else "Remove"
        for item in source.files:
            self.logger.log(level, f"{action} file: {item}")
        for item in source.folders:
            self.logger.log(level, f"{action} folder: {item}")

    @staticmethod
    def path_to_str(path: PurePath) -> str:
        """Turn any path into a windows-path string.

        This is useful mostly for the paths inside the PLC project XML.
        """
        return str(PureWindowsPath(path))


class Operation(Enum):
    MERGE = (PatchPlc.operation_merge,)
    RESET = (PatchPlc.operation_reset,)
    REMOVE = (PatchPlc.operation_remove,)

    def __call__(self, *args, **kwargs) -> Any:
        """Call the method of the enum value."""
        return self.value[0](*args, **kwargs)
