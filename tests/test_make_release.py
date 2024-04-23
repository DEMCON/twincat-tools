import pytest
import sys
import os
import subprocess
import shutil
from pathlib import Path

import tctools.make_release
from tctools.make_release_class import MakeRelease


VERSION = "v1.2.3"


@pytest.fixture
def release_files(plc_code):
    source = Path(__file__).resolve().parent / "plc_release"
    target = plc_code
    shutil.copytree(source, target, dirs_exist_ok=True)
    yield target


@pytest.fixture
def mock_git(mocker, plc_code, monkeypatch, request):
    """Mock ``git.Repo`` to not throw an error and return info.

    Pass indirect argument to override the used version.
    """
    # Mock the `Repo` class
    mocked_repo = mocker.patch("tctools.make_release_class.Repo")
    # Mock `git.tag()` from a mocked Repo instance:
    version = request.param[0] if hasattr(request, "param") else VERSION
    mocked_repo().git.tag.return_value = version

    # Patch the CWD:
    monkeypatch.setenv("PATH", str(plc_code), prepend=os.pathsep)
    monkeypatch.chdir(plc_code)


def test_help(capsys):
    with pytest.raises(SystemExit) as err:
        tctools.make_release.main("--help")

    assert err.type == SystemExit

    message = capsys.readouterr().out
    assert "usage: " in message


def test_cli_help(capsys):
    """Test the CLI hook works."""

    path = sys.executable  # Re-use whatever executable we're using now
    result = subprocess.run(
        [path, "-m", "tctools.make_release", "--help"],
        capture_output=True,
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout.decode()


def test_release(release_files, caplog, mock_git):
    """Test the release feature."""

    releaser = MakeRelease(
        str(release_files),
        "--check-cpu",
        "4",
        "1",
        "--check-devices",
        "Device 2 (EtherCAT)",
        "--check-version-variable",
        "GVL_Version.TcGVL",
        "versionString",
    )
    releaser.run()

    archive = release_files / "deploy" / f"myplc-{VERSION}.zip"
    assert archive.is_file()


def test_release_no_checks(release_files, caplog, mock_git):
    releaser = MakeRelease(str(release_files))
    releaser.run()

    archive = release_files / "deploy" / f"myplc-{VERSION}.zip"
    assert archive.is_file()


def test_release_add_files(release_files, caplog, mock_git):
    releaser = MakeRelease(str(release_files), "-a", "README.md")
    releaser.run()

    archive = release_files / "deploy" / f"myplc-{VERSION}.zip"
    assert archive.is_file()
    release_dir = release_files / "deploy" / "unpacked"
    shutil.unpack_archive(archive, release_dir)
    readme_file = release_dir / "README.md"
    assert readme_file.is_file()


@pytest.mark.parametrize("mock_git", [("v2.0.0",)], indirect=True)
def test_release_failing_checks(release_files, caplog, mock_git):
    releaser = MakeRelease(
        str(release_files),
        "--check-cpu",
        "8",
        "2",
        "--check-devices",
        "Device 1 (EtherCAT)",
        "--check-version-variable",
        "GVL_Version.TcGVL",
        "versionString",
    )
    code = releaser.run()
    assert code != 0

    errors_str = "\n".join(caplog.messages)

    assert "Expected cpu configuration" in errors_str
    assert "should be disabled, but is enabled" in errors_str
    assert "Failed to find version" in errors_str

    archive_dir = release_files / "deploy"
    assert not any(archive_dir.iterdir())  # Make sure it's empty


def test_release_with_hmi(release_files, caplog, mock_git):
    releaser = MakeRelease(
        str(release_files),
        "--include-hmi",
        "--check-version-hmi",
        "Desktop.view",
        "TcHmiTextblock_Version",
    )
    releaser.run()

    archive = release_files / "deploy" / f"myplc-{VERSION}.zip"
    assert archive.is_file()
