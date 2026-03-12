import logging
import shutil
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path, PureWindowsPath

import pytest

from tctools.patch_plc.__main__ import main as patch_plc_main
from tctools.patch_plc.patch_plc_class import PatchPlc
from tctools.xml_sort.xml_sort_class import XmlSorter


def path_to_str(p: Path) -> str:
    """Force any path into a Windows path string."""
    return str(PureWindowsPath(p))


def to_paths(*paths: str) -> list[Path]:
    """Turn a set of strings into Path objects."""
    return [Path(p) for p in paths]


@pytest.fixture()
def plc_dir(plc_code) -> Generator[Path, None, None]:
    yield plc_code / "TwinCAT Project1" / "MyPlc"


@pytest.fixture()
def project(plc_dir) -> Generator[Path, None, None]:
    yield plc_dir / "MyPlc.plcproj"


def test_help(capsys):
    """Test the help text."""
    with pytest.raises(SystemExit) as err:
        patch_plc_main("--help")

    assert err.type is SystemExit

    message = capsys.readouterr().out
    assert "usage:" in message


def test_cli(plc_dir, project):
    """Test the CLI hook works."""
    source = plc_dir / "POUs" / "untracked_source"

    assert "untracked_source" not in project.read_text()

    path = sys.executable  # Re-use whatever executable we're using now
    result = subprocess.run(
        [path, "-m", "tctools.patch_plc", str(project), "merge", "-r", str(source)],
        capture_output=True,
    )

    assert result.returncode == 0
    assert "untracked_source" in project.read_text()
    # More detailed assertions we will perform in the next tests


def test_merge_single_file(plc_dir, project):
    """Test happy-flow adding."""
    source = plc_dir / "POUs" / "untracked_source" / "F_UntrackedFunc.TcPOU"

    patcher = PatchPlc(str(project), "merge", str(source))
    patcher.run()

    project_content = project.read_text()

    assert (
        """<Compile Include="POUs\\untracked_source\\F_UntrackedFunc.TcPOU">
      <SubType>Code</SubType>
    </Compile>"""
        in project_content
    )

    assert '<Folder Include="POUs\\untracked_source"/>' in project_content


@pytest.mark.parametrize("target", ["POUs/untracked_source/", "./"])
def test_merge_recursive(plc_dir, project, target, caplog):
    """Test happy-flow adding for a complete folder.

    Try both on a completely new folder and the entire project root
    """
    source = plc_dir / Path(target)

    untracked_files = to_paths(
        "POUs/untracked_source/F_UntrackedFunc.TcPOU",
        "POUs/untracked_source/E_UntrackedEnum.TcDUT",
        "POUs/untracked_source/subfolder/FB_Untracked.TcPOU",
        "POUs/untracked_source/subfolder/DUT_UntrackedStruct.TcDUT",
    )
    untracked_folders = to_paths(
        "POUs/untracked_source",
        "POUs/untracked_source/subfolder",
    )

    project_content = project.read_text()

    for path in untracked_files + untracked_folders:
        assert path_to_str(path) not in project_content

    with caplog.at_level(logging.WARNING):
        PatchPlc(str(project), "merge", str(source), "-r").run()

    project_content = project.read_text()

    for file in untracked_files:
        assert f'<Compile Include="{path_to_str(file)}">' in project_content
    for folder in untracked_folders:
        assert f'<Folder Include="{path_to_str(folder)}"/>' in project_content

    assert len(caplog.records) == 0  # No warnings or errors

    # Now compare with stored, sorted result:
    expected_file = plc_dir / "MyPlc_with_untracked.plcproj.xml"

    XmlSorter(str(project)).run()

    assert project.read_text() == expected_file.read_text()


def test_remove(plc_dir, project):
    """Test remove happy-flow."""
    tracked_files = to_paths(
        "POUs/FB_Example.TcPOU",
        "DUTs/ST_Example.TcDUT",
    )

    project_content = project.read_text()
    lines_before = project_content.count("\n")

    for file in tracked_files:
        assert path_to_str(file) in project_content

    path_args = (str(plc_dir / p) for p in tracked_files)
    patcher = PatchPlc(str(project), "remove", *path_args)
    patcher.run()

    project_content = project.read_text()

    for file in tracked_files:
        assert path_to_str(file) not in project_content

    lines_after = project_content.count("\n")
    assert lines_after == lines_before - 6  # Make sure not more got deleted


@pytest.mark.parametrize("recursive", [False, True])
def test_remove_recursive(plc_dir, project, recursive):
    folder = Path("POUs/Module")
    tracked_folders = [
        'Include="POUs\\Module"',
        'Include="POUs\\Module\\DUTs"',
    ]
    tracked_files = [
        'Include="POUs\\Module\\FB_Module.TcPOU"',
        'Include="POUs\\Module\\DUTs\\ST_ModuleCmd.TcDUT"',
        'Include="POUs\\Module\\DUTs\\ST_ModuleStatus.TcDUT"',
    ]
    content_before = project.read_text()
    lines_before = content_before.count("\n")
    for file in tracked_folders + tracked_files:
        assert file in content_before

    # Remove the actual folder first, because filesystem presence shouldn't matter:
    shutil.rmtree(plc_dir / folder)

    args = [str(project), "remove", str(folder)]
    if recursive:
        args.append("-r")

    code = PatchPlc(*args).run()
    assert code == 0

    content_after = project.read_text()
    lines_after = content_after.count("\n")

    if not recursive:
        assert content_after == content_before  # No changes
        return

    for item in tracked_files + tracked_folders:
        assert item not in content_after

    assert lines_after == lines_before - 2 * 1 - 3 * 3


def test_reset(plc_dir, project):
    # Remove the actual (tracked) folder first:
    shutil.rmtree(plc_dir / "POUs" / "Module")
    # And there is already the "POUs/untracked_source" directory

    expect_removed = [
        "POUs\\Module",
        "POUs\\Module\\DUTs",
        "POUs\\Module\\FB_Module.TcPOU",
        "POUs\\Module\\DUTs\\ST_ModuleCmd.TcDUT",
        "POUs\\Module\\DUTs\\ST_ModuleStatus.TcDUT",
    ]

    expect_added = [
        "POUs\\untracked_source",
        "POUs\\untracked_source\\subfolder",
        "POUs\\untracked_source\\E_UntrackedEnum.TcDUT",
        "POUs\\untracked_source\\F_UntrackedFunc.TcPOU",
        "POUs\\untracked_source\\subfolder\\DUT_UntrackedStruct.TcDUT",
        "POUs\\untracked_source\\subfolder\\FB_Untracked.TcPOU",
    ]

    content_before = project.read_text()
    lines_before = content_before.count("\n")
    for item in expect_removed:
        assert item in content_before
    for item in expect_added:
        assert item not in content_before

    # Reset to the entire local directory:
    code = PatchPlc(str(project), "reset", "-r", str(plc_dir)).run()
    assert code == 0

    content_after = project.read_text()
    for item in expect_removed:
        assert item not in content_after
    for item in expect_added:
        assert item in content_after

    lines_after = content_after.count("\n")
    assert lines_after == lines_before - (2 * 1) - (3 * 3) + (2 * 1) + (4 * 3)
    # Remove 2 folders and 3 files, add 2 folders and 4 files


def test_reset_duplicate(plc_dir, project, caplog):
    # Create a new file, with a name that's already known:
    module_folder = plc_dir / "POUs" / "Module"
    new_file = module_folder / "DUTs" / "MAIN.TcPOU"
    new_file.write_text("\n")  # Create the file

    content_before = project.read_text()

    with caplog.at_level(logging.WARNING):
        code = PatchPlc(str(project), "reset", str(module_folder), "-r").run()

    assert code == 0

    assert len(caplog.records) == 1
    msg = caplog.records[0].message
    assert "Refusing to add" in msg and "MAIN.TcPOU" in msg

    assert project.read_text() == content_before  # The project should not be changed


def test_reset_empty_project(plc_dir, caplog):
    project = plc_dir / "MyPlc_empty.plcproj"  # Project with 0 sources

    code = PatchPlc(str(project), "reset", str(plc_dir), "-r").run()
    assert code == 0

    content_after = project.read_text()
    assert 'Include="POUs\\untracked_source\\F_UntrackedFunc.TcPOU"' in content_after
    assert 'Include="POUs\\untracked_source"' in content_after
