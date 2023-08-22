"""
Configuration for these tests.
"""

import pytest
import shutil
from pathlib import Path
from typing import List
import re


@pytest.fixture
def plc_code(tmp_path):
    """Copy (a subset of) the example PLC code into a temporary directory.

    Yields the new directory.
    """
    source = Path(__file__).resolve().parent / "plc_code"
    target = tmp_path / "plc_code"
    shutil.copytree(source, target)
    yield target


def assert_order_of_lines_in_file(
    expected: List[str], file: str, is_substring=False, check_true=True
):
    """Assert the expected lines occur in the given order in the file.

    Leading and trailing whitespace is ignored.

    :param expected:
    :param file:
    :param is_substring: When True, use ``... in ...`` instead of equal
    :param check_true: Set to False to assert the opposite
    """
    idx = 0

    def check_line(expected_line: str, line_to_check: str) -> bool:
        if is_substring:
            return expected_line in line_to_check
        return expected[idx].strip() == line.strip()

    with open(file, "r") as fh:
        count = 0
        while True:
            count += 1
            line = fh.readline()

            if not line or idx >= len(expected):
                break

            if check_line(expected[idx], line):
                idx += 1
            else:
                # Make sure the other lines aren't around either
                for i, ex_line in enumerate(expected):
                    if i == idx:
                        continue
                    if check_line(ex_line, line):
                        assert not check_true

    assert (
        idx == len(expected)
    ) == check_true, "Did not encounter right number of expected lines"
