from .common import Tool


class MakeRelease(Tool):
    """Tool to create a release archive from a TwinCAT project."""

    @staticmethod
    def set_arguments(parser):
        parser.description = """Create a release archive from the current project.

Archives the compiled result of PlC and HMI projects.
Checks can be performed to make sure the binaries work on a target PLC."""

    def run(self) -> int:
        """Create release archive."""
        return 0
