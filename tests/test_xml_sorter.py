import pytest
import subprocess
import sys

from tctools.xml_sort.__main__ import main as xml_sort_main
from tctools.xml_sort.xml_sort_class import XmlSorter

from .conftest import assert_order_of_lines_in_file


def test_help(capsys):
    """Test the help text."""
    with pytest.raises(SystemExit) as err:
        xml_sort_main("--help")

    assert err.type == SystemExit

    message = capsys.readouterr().out
    assert "usage:" in message


def test_cli(plc_code):
    """Test the CLI hook works."""
    file = plc_code / "plant_catalog.xml"

    path = sys.executable  # Re-use whatever executable we're using now
    result = subprocess.run(
        [path, "-m", "tctools.xml_sort", str(file)], capture_output=True
    )

    assert result.returncode == 0
    assert "Re-saved 1 path" in result.stdout.decode()


def test_single_file_plain_xml(plc_code):
    """Test how a plain XML path gets sorted."""
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

    assert_order_of_lines_in_file(expected, file, is_substring=True, check_true=False)

    sorter = XmlSorter(str(file))
    sorter.run()

    assert_order_of_lines_in_file(expected, file, is_substring=True)


def test_use_attributes(plc_code):
    """Test how attributes are used to sort nodes."""
    file = plc_code / "books.xml"

    expected = [
        '<book letter="a">',
        '<book letter="b">',
        '<book letter="c">',
    ]
    # <name>*</name> is not used for sorting

    assert_order_of_lines_in_file(expected, file, is_substring=True, check_true=False)
    xml_sort_main(str(file))
    assert_order_of_lines_in_file(expected, file, is_substring=True)


def test_sort_attributes(plc_code):
    """Test how attributes themselves are sorted."""
    file = plc_code / "books_attributes.xml"

    expected = [
        '<book a="2" b="3" c="1">',
        "<title>Alpha</title>",
        '<book a="2" b="3" c="1">',
        "<title>Bravo</title>",
    ]
    # Attributes are ordered differently
    assert_order_of_lines_in_file(expected, file, is_substring=True, check_true=False)
    xml_sort_main(str(file))
    assert_order_of_lines_in_file(expected, file, is_substring=True)


def test_single_file_dry(plc_code, caplog):
    """Test using dry run."""
    file = plc_code / "books.xml"

    sorter = XmlSorter(str(file), "--dry", "-l", "DEBUG")
    sorter.run()

    result = "\n".join(caplog.messages)
    assert '<book letter="a">' in result
    caplog.clear()

    sorter = XmlSorter(str(file), "-l", "DEBUG")
    sorter.run()  # Make change for real
    caplog.clear()

    sorter = XmlSorter(str(file), "--dry", "-l", "DEBUG")
    sorter.run()

    result3 = "\n".join(caplog.messages)
    assert '<book letter="a">' not in result3
    assert "identical" in result3


def test_skip_nodes(plc_code, caplog):
    """Test skipping selected nodes"""
    file = plc_code / "plant_catalog.xml"
    content_before = file.read_text()

    XmlSorter(str(file), "--skip-nodes", "PLANT").run()
    content_after_skipped = file.read_text()

    pos_line1 = content_after_skipped.find("<COMMON>Bloodroot</COMMON>")
    pos_line2 = content_after_skipped.find(
        "<BOTANICAL>Aquilegia canadensis</BOTANICAL>"
    )
    assert pos_line1 < pos_line2  # Make sure these nodes did not get moved around

    XmlSorter(str(file)).run()
    content_after = file.read_text()

    assert content_after_skipped != content_before
    assert content_after_skipped != content_after


def test_single_file_check(plc_code):
    """Test using check flag."""
    file = plc_code / "books.xml"

    code = xml_sort_main(str(file), "--check")
    assert code != 0

    xml_sort_main(str(file))  # Make change for real

    code2 = xml_sort_main(str(file), "--check")
    assert code2 == 0


def test_single_file_check_already_sorted(plc_code):
    """Test check flag when path would be reformatted but not resorted."""
    file = plc_code / "books_sorted.xml"

    code = xml_sort_main(str(file), "--check")
    assert code == 0


def test_single_project_file(plc_code):
    """Test XML sort on a single target path."""
    file = plc_code / "TwinCAT Project1" / "TwinCAT Project1.tsproj"
    xml_sort_main(
        str(file),
        "--skip-nodes",
        "Device",
        "DeploymentEvents",
        "TcSmItem",
        "DataType",
    )


def test_multiple_files(plc_code, caplog):
    """Test CLI interface."""
    file1 = plc_code / "books.xml"
    file2 = plc_code / "plant_catalog.xml"
    xml_sort_main(str(file1), str(file2), "-l", "DEBUG")
    result = "\n".join([rec.msg for rec in caplog.records])
    assert "books.xml" in result
    assert "plant_catalog.xml" in result


def test_folder(plc_code, caplog):
    """Test CLI interface."""
    xml_sort_main(str(plc_code), "--filter", "*.xml", "-l", "DEBUG")
    result = "\n".join([rec.msg for rec in caplog.records])
    assert "books.xml" in result
    assert "plant_catalog.xml" in result


def test_project(plc_code, caplog):
    """Test running over a full project as normal."""
    file = plc_code / "TwinCAT Project1"
    xml_sort_main(
        str(file),
        "-r",
        "--skip-nodes",
        "Device",
        "DeploymentEvents",
        "TcSmItem",
        "DataType",
        "-r",
        "--filter",
        "*.tsproj",
        "*.xti",
        "*.plcproj",
        "-l",
        "DEBUG",
    )

    result = "\n".join([rec.msg for rec in caplog.records])

    expected = [
        "TwinCAT Project1.tsproj",
        "MyPlc.plcproj",
        "Device 2 (EtherCAT).xti",
        "NC.xti",
    ]

    for exp in expected:
        assert exp in result
