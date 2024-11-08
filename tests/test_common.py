import pytest  # noqa

from tctools.common import Tool


class MyTool(Tool):
    """Dummy tool."""

    CONFIG_KEY = "dummy"

    @classmethod
    def set_arguments(cls, parser):
        super().set_arguments(parser)

        parser.add_argument(
            "--my-option",
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

    def test_config_file(self, tmp_path, monkeypatch):
        conf_dir = tmp_path / "project"
        work_dir = conf_dir / "subdir1" / "subdir2"
        work_dir.mkdir(parents=True)

        conf_file = conf_dir / "tctools.toml"
        conf_file.write_text(
            """[tctools.dummy]
my_option = "xyz123"
"""
        )

        monkeypatch.chdir(work_dir)

        tool = MyTool()
        assert tool.args.my_option == "xyz123"

    # TODO: Add test for section priority
