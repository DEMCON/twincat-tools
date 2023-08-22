import pytest

import tctools


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
    tctools.xml_sort_main("--file", str(file))
    return


# def test_single_file(plc_code):
#     """Test XML sort on a single target file."""
#     file = plc_code / "TwinCAT Project1" / "TwinCAT Project1.tsproj"
#     tctools.xml_sort_main("--file", str(file))
#     return
