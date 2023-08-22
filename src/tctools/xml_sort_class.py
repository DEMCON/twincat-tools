from lxml import etree
import re
from typing import Optional


class XmlSorter:
    """Tool to sort XML files.

    Use one instance for a sequence of files.
    """

    def __init__(self, quiet=False, dry=False, skip_nodes=None):
        """

        :param quiet:       If true, do not mention each file we touch
        :param dry:         If true, do not actually save the altered files
        :param skip_nodes:  List of node tags to ignore (and their children)
        """

        self.quiet = quiet
        self.dry = dry
        self.skip_nodes = skip_nodes
        if self.skip_nodes is None:
            self.skip_nodes = []

        self.files_checked = 0
        self.files_altered = 0

        # Preserve `CDATA` XML flags
        self.parser = etree.XMLParser(strip_cdata=False)

    def sort_file(self, path: str) -> bool:
        """Sort a single file."""

        try:
            tree = etree.parse(path, self.parser)
        except etree.XMLSyntaxError:
            return False

        header_before = self.get_xml_header(path)

        self.files_checked += 1

        root = tree.getroot()

        self.sort_node_recursively(root)

        # Re-indent by a double space
        etree.indent(tree, space="  ", level=0)

        if not self.quiet:
            print(f"Processed file `{path}`")

        if not self.dry:
            with open(path, "wb") as fh:
                fh.write(
                    etree.tostring(
                        root,
                        doctype=header_before,
                    )
                )
                # Write by hand (instead of `tree.write()` so we can control the header
                self.files_altered += 1

        return True

    def sort_node_recursively(self, node):
        """Sort a node and any sub-nodes, and their sub-nodes."""

        if node.tag in self.skip_nodes:
            return  # Stop here

        # Also sort the attributes - but this won't work flawlessly, since dicts are
        # inherently unsorted
        self.sort_attributes(node)

        # First sort the next level of children, necessary to sort the current node too
        for child in node:
            self.sort_node_recursively(child)

        node[:] = sorted(node, key=self.get_node_sorting_key)

    @staticmethod
    def sort_attributes(node):
        """Sort the attributes of a node."""
        sorted_attrs = sorted(node.attrib.items())
        node.attrib.clear()
        node.attrib.update(sorted_attrs)

    @staticmethod
    def get_node_sorting_key(node):
        """Get the string by which sub-nodes will be sorted.

        Sorting will be done on the literal node XML subtree string.
        """

        key = etree.tostring(node, encoding="unicode")
        key = re.sub(r"\s+", "", key, flags=re.UNICODE)

        return key

    @staticmethod
    def get_xml_header(file: str) -> Optional[str]:
        """Get raw XML header as string."""
        with open(file, "r") as fh:
            # Search only the start of the file, otherwise give up
            for _ in range(100):
                line = fh.readline()
                if line.startswith("<?xml") and line.rstrip().endswith("?>"):
                    return line.strip()

        return None
