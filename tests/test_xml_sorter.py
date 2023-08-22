import pytest
import xml.etree.ElementTree as ET

import tctools

from .conftest import compare_without_whitespace, check_order_of_lines_in_file


def test_help(capsys):
    """Test the help text."""

    with pytest.raises(SystemExit) as err:
        tctools.xml_sort_main("--help")

    assert err.type == SystemExit

    message = capsys.readouterr().out
    assert "usage:" in message and "--project" in message


def test_single_file_plain_xml(plc_code):
    """Test how a plain XML file gets sorted."""
    file = plc_code / "plant_catalog.xml"

    expected = [
        "<AVAILABILITY>010299</AVAILABILITY>",
        "<AVAILABILITY>012099</AVAILABILITY>",
        "<AVAILABILITY>012699</AVAILABILITY>",
        "<AVAILABILITY>020199</AVAILABILITY>",
        "<AVAILABILITY>030699</AVAILABILITY>",
        "<AVAILABILITY>030699</AVAILABILITY>",
        "<AVAILABILITY>031599</AVAILABILITY>",
        "<AVAILABILITY>041899</AVAILABILITY>",
        "<AVAILABILITY>051799</AVAILABILITY>",
    ]

    assert not check_order_of_lines_in_file(expected, file, is_substring=True)

    tctools.xml_sort_main("--file", str(file))

    assert check_order_of_lines_in_file(expected, file, is_substring=True)


# def test_single_file(plc_code):
#     """Test XML sort on a single target file."""
#     file = plc_code / "TwinCAT Project1" / "TwinCAT Project1.tsproj"
#     tctools.xml_sort_main("--file", str(file))
#     return
