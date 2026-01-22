from pathlib import Path

import pytest  # noqa

from tctools.common import Tool


class MyTool(Tool):
    """Dummy tool."""

    CONFIG_KEY = "dummy"

    PATH_VARIABLES = ["my_file", "my_targets"]

    @classmethod
    def set_arguments(cls, parser):
        super().set_arguments(parser)

        parser.add_argument(
            "--my-option",
            action="store",
            default="default-text",
        )
        parser.add_argument(
            "--my-file",
            action="store",
            default="default-text",
        )
        parser.add_argument(
            "--my-targets",
            action="store",
            default="default-text",
        )
        return parser

    def run(self) -> int:
        return 0  # Do nothing


class TestCommon:
    """Directly test the common interface."""

    def test_cli_arguments(self):
        tool = MyTool("--my-option", "xyz123")
        assert tool.args.my_option == "xyz123"

    def test_cli_arguments_default(self):
        tool = MyTool()
        assert tool.args.my_option == "default-text"

    def test_cli_version(self, capsys):
        with pytest.raises(SystemExit) as err:
            _ = MyTool("--version")

        assert err.type == SystemExit

        message = capsys.readouterr().out
        assert message

    def test_config_file(self, tmp_path, monkeypatch):
        conf_dir = tmp_path / "project"
        work_dir = conf_dir / "subdir1" / "subdir2"
        work_dir.mkdir(parents=True)

        conf_file = conf_dir / "tctools.toml"
        conf_file.write_text("""[tctools.dummy]
my_option = "xyz123"
""")

        monkeypatch.chdir(work_dir)

        tool = MyTool()
        assert tool.args.my_option == "xyz123"

    def test_config_file_priority(self, tmp_path, monkeypatch):
        conf_dir = tmp_path / "project"
        work_dir = conf_dir / "subdir1" / "subdir2"
        work_dir.mkdir(parents=True)

        conf_file2 = conf_dir / "pyproject.toml"
        conf_file2.write_text("""[tctools.dummy]
my_option = "xyz123"
""")
        conf_file = conf_dir / "tctools.toml"
        conf_file.write_text("""[tctools.dummy]
my_option = "abc987"
""")

        monkeypatch.chdir(work_dir)

        tool = MyTool()
        assert tool.args.my_option == "abc987"

    def test_config_file_relative_path(self, tmp_path, monkeypatch):
        conf_dir = tmp_path / "project"
        work_dir = conf_dir / "subdir1" / "subdir2"
        work_dir.mkdir(parents=True)

        conf_file = conf_dir / "tctools.toml"
        conf_file.write_text("""[tctools.dummy]
    my_file = "some_file.txt"
    my_targets = ["./dir1", "dir2/subdir2/", "//abs_dir/absolute_file.txt"]
    """)

        monkeypatch.chdir(work_dir)  # Run in child dir of config file dir

        tool = MyTool()
        assert not tool.args.my_file.is_relative_to(work_dir)
        assert tool.args.my_file == conf_dir / "some_file.txt"

        assert not tool.args.my_targets[0].is_relative_to(work_dir)
        assert not tool.args.my_targets[1].is_relative_to(work_dir)
        assert not tool.args.my_targets[2].is_relative_to(work_dir)
        assert tool.args.my_targets[0] == conf_dir / "dir1"
        assert tool.args.my_targets[1] == conf_dir / "dir2" / "subdir2"
        assert tool.args.my_targets[2] == Path("//abs_dir/absolute_file.txt")
