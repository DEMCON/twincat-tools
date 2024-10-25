import re
from typing import Dict, List

from lxml import etree

from ..common import Element, TcTool


class XmlSorter(TcTool):
    """Tool to sort XML files.

    Use one instance for a sequence of files.
    """

    LOGGER_NAME = "xml_sorter"

    FILTER_DEFAULT: List[str] = ["*.tsproj", "*.xti", "*.plcproj"]

    CONFIG_KEY = "xml_sort"

    def __init__(self, *args):
        super().__init__(*args)

        if self.args.skip_nodes is None:
            self.args.skip_nodes = []

        self._file_changed = False  # True if any change is made in the current path
        # This is a property to avoid passing around booleans between recursive calls

    @classmethod
    def set_arguments(cls, parser):
        super().set_arguments(parser)

        parser.prog = "tc_xml_sort"
        parser.description = "Alphabetically sort the nodes in XML files."
        parser.epilog = "Example: ``tc_xml_sort -r ./MyTwinCATProject``"
        parser.add_argument(
            "--skip-nodes",
            "-n",
            help="Do not touch the attributes and sub-nodes of nodes with these names",
            nargs="+",
            default=["Device", "DataType", "DeploymentEvents"],
        )
        return parser

    def run(self) -> int:
        for file in self.find_files():
            self.sort_file(str(file))

        self.logger.info(f"Checked {self.files_checked} path(s)")

        if self.args.check:
            if self.files_to_alter == 0:
                self.logger.info("No changes to be made in checked files!")
                return 0

            self.logger.info(f"{self.files_to_alter} path(s) can be re-sorted")
            return 1

        self.logger.info(f"Re-saved {self.files_resaved} path(s)")

    def sort_file(self, path: str):
        """Sort a single path."""
        tree = self.get_xml_tree(path)

        self.files_checked += 1
        self._file_changed = False  # Reset

        root = tree.getroot()
        self.sort_node_recursively(root)

        # Re-indent by a double space
        etree.indent(tree, space="  ", level=0)

        self.logger.debug(f"Processing path `{path}`...")

        tree_bytes = etree.tostring(root, doctype=self.header_before)

        with open(path, "rb") as fh:
            current_contents = fh.readlines()

        current_bytes = b"".join(current_contents)

        if self._file_changed:
            self.files_to_alter += 1

        if current_bytes != tree_bytes:
            if self.args.dry:
                self.logger.debug(f"Old path contents of `{path}`:")
                self.logger.debug("-" * 50)
                self.logger.debug(current_bytes.decode("utf-8"))
                self.logger.debug("-" * 50)
                self.logger.debug("New path contents:")
                self.logger.debug("-" * 50)
                self.logger.debug(tree_bytes.decode("utf-8"))
                self.logger.debug("-" * 50)

            self.logger.debug(f"File can be re-sorted: `{path}`")

            if not self.args.check and not self.args.dry:
                with open(path, "wb") as fh:
                    fh.write(tree_bytes)
                    # Write by hand (instead of `tree.write()` so we control the header
                    self.files_resaved += 1
        else:
            if self.args.dry:
                self.logger.debug("Content identical for `{path}`")

    def sort_node_recursively(self, node: Element):
        """Sort a node and any sub-nodes, and their sub-nodes.

        Sorting is done in-place, the object is passed in by reference.
        """

        if self.get_tag(node) in self.args.skip_nodes:
            return  # Stop here

        if self.get_attrib(node).get("space", None):
            return  # Do not touch with `xml:space="preserve"`

        # Also sort the attributes - but this won't work flawlessly, since dicts are
        # inherently unsorted
        if self.sort_attributes(node):
            self._file_changed = True

        # First sort the next level of children, necessary to sort the current node too
        for child in node:
            self.sort_node_recursively(child)

        new_children = sorted(node, key=self.get_node_sorting_key)

        if new_children != node[:]:
            self._file_changed = True

        node[:] = new_children  # Replace children in place

    @staticmethod
    def sort_attributes(node: Element) -> bool:
        """Sort the attributes of a node.

        :returns: True if any changes were really made
        """
        sorted_attrs = sorted(node.attrib.items())
        changed = sorted_attrs != node.attrib.items()
        node.attrib.clear()
        node.attrib.update(sorted_attrs)
        return changed

    @staticmethod
    def get_node_sorting_key(node: Element) -> str:
        """Get the string by which sub-nodes will be sorted.

        Sorting will be done on the literal node XML subtree string.
        """
        key = etree.tostring(node, encoding="unicode")
        key = re.sub(r"\s+", "", key, flags=re.UNICODE)

        return key

    @staticmethod
    def get_tag(node: Element) -> str:
        """Get tag without URL prefix from node."""
        tag = node.tag
        if tag.startswith("{"):
            # Keep only the part after the `{...}`
            _, _, tag = tag.partition("}")

        return tag

    @staticmethod
    def get_attrib(node: Element) -> Dict[str, str]:
        """Yield node attributes, with namespace stripped."""
        attributes = {}
        for key, value in node.attrib.items():
            if key.startswith("{"):
                # Keep only the part after the `{...}`
                _, _, key = key.partition("}")
            attributes[key] = value

        return attributes
