from lxml import etree
import re
from typing import Optional
from logging import getLogger

from .common import TcTool


logger = getLogger("xml_sort")


class XmlSorter(TcTool):
    """Tool to sort XML files.

    Use one instance for a sequence of files.
    """

    def __init__(self, quiet=False, resave=True, report=False, skip_nodes=None):
        """

        :param quiet:       If true, do not mention each file we touch
        :param resave:      If true, re-save the files in-place
        :param report:      If true, print all changes to make
        :param skip_nodes:  List of node tags to ignore (and their children)
        """

        self.quiet = quiet
        self.resave = resave
        self.report = report
        self.skip_nodes = skip_nodes
        if self.skip_nodes is None:
            self.skip_nodes = []

        self.files_checked = 0  # Files read by parser
        self.files_to_alter = 0  # Files that seem to require changes
        self.files_resaved = 0  # Files actually re-saved to disk

        self._file_changed = False  # True if any change is made in the current file
        # This is a property to avoid passing around booleans between recursive calls

        super().__init__()

    def sort_file(self, path: str):
        """Sort a single file."""
        tree = self.get_xml_tree(path)

        self.files_checked += 1
        self._file_changed = False  # Reset

        root = tree.getroot()
        self.sort_node_recursively(root)

        # Re-indent by a double space
        etree.indent(tree, space="  ", level=0)

        if not self.quiet:
            logger.debug(f"Processing file `{path}`...")

        tree_bytes = etree.tostring(root, doctype=self.header_before)

        with open(path, "rb") as fh:
            current_contents = fh.readlines()

        current_bytes = b"".join(current_contents)

        if self._file_changed:
            self.files_to_alter += 1

        if current_bytes != tree_bytes:
            if self.report:
                print(f"Old file contents of `{path}`:")
                print("-" * 50)
                print(current_bytes.decode("utf-8"))
                print("-" * 50)
                print("New file contents:")
                print("-" * 50)
                print(tree_bytes.decode("utf-8"))
                print("-" * 50)

            logger.debug(f"File can be re-sorted: `{path}`")
        else:
            if self.report:
                print("Content identical> for `{path}`")
                print()

        if self.resave:
            with open(path, "wb") as fh:
                fh.write(tree_bytes)
                # Write by hand (instead of `tree.write()` so we can control the header
                self.files_resaved += 1

    def sort_node_recursively(self, node):
        """Sort a node and any sub-nodes, and their sub-nodes."""

        if node.tag in self.skip_nodes:
            return  # Stop here

        if node.get("{http://www.w3.org/XML/1998/namespace}space") == "preserve":
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
    def sort_attributes(node) -> bool:
        """Sort the attributes of a node.

        :returns: True if any changes were really made
        """
        sorted_attrs = sorted(node.attrib.items())
        changed = (sorted_attrs != node.attrib.items())
        node.attrib.clear()
        node.attrib.update(sorted_attrs)
        return changed

    @staticmethod
    def get_node_sorting_key(node):
        """Get the string by which sub-nodes will be sorted.

        Sorting will be done on the literal node XML subtree string.
        """

        key = etree.tostring(node, encoding="unicode")
        key = re.sub(r"\s+", "", key, flags=re.UNICODE)

        return key
