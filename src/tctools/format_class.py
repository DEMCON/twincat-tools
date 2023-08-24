from editorconfig import getproperties

from .common import TcTool


class Formatter(TcTool):
    """Helper to check formatting in PLC files.

    Instantiate once for a sequence of files.
    """

    def __init__(self):
        pass
