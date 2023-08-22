"""
Configuration for these tests.
"""

import pytest
import shutil
from pathlib import Path


@pytest.fixture
def plc_code(tmp_path):
    """Copy (a subset of) the example PLC code into a temporary directory.

    Yields the new directory.
    """
    source = Path(__file__).resolve().parent / "plc_code"
    target = tmp_path / "plc_code"
    shutil.copytree(source, target)
    yield target
