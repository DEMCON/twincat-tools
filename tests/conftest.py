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
    """Assert the expected lines occur in the given order in the path.

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


def assert_strings_have_substrings(expected: List[List[str]], actual: List[str]):
    """Assert substrings occur in exactly one but any set of lines."""

    actual = [line for line in actual if len(line) > 0]  # Remove emtpy strings

    def check_line(line):
        for idx_expected, substrings in enumerate(expected):
            if all([substring in line for substring in substrings]):
                return idx_expected

        return None

    i = 0  # Old-fashioned loop because we resize
    while i < len(actual):
        idx = check_line(actual[i])
        if idx is not None:  # Found match, remove both
            actual.pop(i)
            expected.pop(idx)
            continue

        i += 1

    assert (
        actual == []
        and "Some lines in `actual` are not covered by the expected substrings"
    )
    assert expected == [] and "Some expected substring sets were not found in `actual`"
