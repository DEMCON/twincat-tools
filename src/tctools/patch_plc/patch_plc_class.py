from ..common import TcTool
from typing import List


class PatchPlc(TcTool):
    """Function code for PLc project patching."""

    LOGGER_NAME = "patch_plc"

    FILTER_DEFAULT: List[str] = []

    CONFIG_KEY = "patch_plc"

    @classmethod
    def set_arguments(cls, parser):
        super().set_arguments(parser)

        parser.prog = "tc_patch_plc"
        parser.description = "Add or remove existing files to a PLC project."
        parser.epilog = "Example: ``tc_patch_plc ./MyPLC.plcproj -r POUs/Generated/``"

        parser.add_argument(
            "source",
            help="File(s) or folder(s) with PLC source to add to the project (=`target`)",
            nargs="+",
        )
        return parser

    def run(self) -> int:


        return 0
