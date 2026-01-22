import subprocess
import sys

import pytest

from tctools.patch_plc.__main__ import main as patch_plc_main
from tctools.patch_plc.patch_plc_class import PatchPlc
from tctools.xml_sort.xml_sort_class import XmlSorter


def test_help(capsys):
    """Test the help text."""
    with pytest.raises(SystemExit) as err:
        patch_plc_main("--help")

    assert err.type == SystemExit

    message = capsys.readouterr().out
    assert "usage:" in message


def test_cli(plc_code):
    """Test the CLI hook works."""
    plc_dir = plc_code / "TwinCAT Project1" / "MyPlc"
    project = plc_dir / "MyPlc.plcproj"
    source = plc_dir / "POUs" / "untracked_source"

    path = sys.executable  # Re-use whatever executable we're using now
    result = subprocess.run(
        [path, "-m", "tctools.patch_plc", str(project), "-r", str(source)],
        capture_output=True,
    )

    assert result.returncode == 0
    # assert "Re-saved 1 path" in result.stdout.decode()
    # TODO: Add some kind of output assertion here


def test_add_single_file(plc_code):
    """Test happy-flow adding."""
    plc_dir = plc_code / "TwinCAT Project1" / "MyPlc"
    project = plc_dir / "MyPlc.plcproj"
    source = plc_dir / "POUs" / "untracked_source" / "F_UntrackedFunc.TcPOU"

    patcher = PatchPlc(str(project), str(source))
    patcher.run()

    project_content = project.read_text()

    assert """<Compile Include="POUs\\untracked_source\\F_UntrackedFunc.TcPOU">
      <SubType>Code</SubType>
    </Compile>""" in project_content

    assert '<Folder Include="POUs\\untracked_source"/>' in project_content


def test_add_recursive(plc_code):
    """Test happy-flow adding for a complete folder."""
    plc_dir = plc_code / "TwinCAT Project1" / "MyPlc"
    project = plc_dir / "MyPlc.plcproj"
    source = plc_dir / "POUs" / "untracked_source"

    untracked_files = [
        "POUs\\untracked_source\\F_UntrackedFunc.TcPOU",
        "POUs\\untracked_source\\E_UntrackedEnum.TcDUT",
        "POUs\\untracked_source\\subfolder\\FB_Untracked.TcPOU",
        "POUs\\untracked_source\\subfolder\\DUT_UntrackedStruct.TcDUT",
    ]
    untracked_folders = [
        "POUs\\untracked_source",
        "POUs\\untracked_source\\subfolder",
    ]

    project_content = project.read_text()

    for path in untracked_files + untracked_folders:
        assert path not in project_content

    patcher = PatchPlc(str(project), str(source), "-r")
    patcher.run()

    project_content = project.read_text()

    for file in untracked_files:
        assert f'<Compile Include="{file}">' in project_content
    for folder in untracked_folders:
        assert f'<Folder Include="{folder}"/>' in project_content

    # Now compare with stored, sorted result:
    expected_file = plc_code / source / "MyPlc_with_untracked.plcproj.xml"

    XmlSorter(str(project)).run()

    assert project.read_text() == expected_file.read_text()
