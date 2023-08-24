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


def assert_warnings(expected: dict, actual: List[str]):
    """Assert expected formatting warnings in real output."""

    def check_line(line):
        """Check if any of the expected messages are in a line."""
        for warning, files in expected.items():
            if warning not in line:
                continue
            for file, blocks in files.items():
                if file not in line:
                    continue
                for block, nrs in blocks.items():
                    if f"[{block}]" not in line:
                        continue
                    for number in nrs:
                        if f":{number}" in line:
                            return [warning, file, block, number]

        return None

    # left_overs = [line for line in actual if line and not check_line(line)]

    # assert (
    #     len(left_overs) == 0
    #     and f"Expected warnings do not match list exactly: {left_overs}"
    # )

    i = 0
    while i < len(actual):
        line = actual[i]
        if not line:
            actual.pop(i)
            continue

        idx = check_line(line)
        if idx is not None:
            actual.pop(i)
            expected[idx[0]][idx[1]][idx[2]].remove(idx[3])
            if not expected[idx[0]][idx[1]][idx[2]]:
                expected[idx[0]][idx[1]].pop(idx[2])
            if not expected[idx[0]][idx[1]]:
                expected[idx[0]].pop(idx[1])
            if not expected[idx[0]]:
                expected.pop(idx[0])
            continue

        i += 1  # Old-fashioned looping so we can modify the list as we go

    assert len(actual) == 0 and f"Actual warnings list is not fully covered: {actual}"
    assert len(expected) == 0 and f"Expected warnings not all covered: {expected}"
