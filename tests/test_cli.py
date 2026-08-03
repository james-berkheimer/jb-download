import pytest
from click.testing import CliRunner

from jb_download import cli as cli_module
from jb_download.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def captured_run(monkeypatch):
    """Replace run_download and record the keyword arguments the CLI passed."""
    calls = {}

    def _fake(**kwargs):
        calls.update(kwargs)
        return calls.pop("_failures", 0)

    monkeypatch.setattr(cli_module, "run_download", _fake)
    return calls


class TestExitCodes:
    def test_success_exits_zero(self, runner, captured_run):
        result = runner.invoke(cli, ["https://ok.example"])

        assert result.exit_code == 0

    def test_failures_exit_nonzero(self, runner, monkeypatch):
        monkeypatch.setattr(cli_module, "run_download", lambda **kwargs: 1)

        result = runner.invoke(cli, ["https://fail.example"])

        assert result.exit_code == 1

    def test_missing_url_is_a_usage_error(self, runner, monkeypatch):
        def _raise(**kwargs):
            raise ValueError("You must provide a URL or a URL list file.")

        monkeypatch.setattr(cli_module, "run_download", _raise)

        result = runner.invoke(cli, [])

        assert result.exit_code == 2
        assert "must provide a URL" in result.output

    def test_unexpected_errors_do_not_print_a_traceback(self, runner, monkeypatch):
        def _raise(**kwargs):
            raise OSError("disk on fire")

        monkeypatch.setattr(cli_module, "run_download", _raise)

        result = runner.invoke(cli, ["https://ok.example"])

        assert result.exit_code == 1
        assert "Traceback" not in result.output


class TestOptionPlumbing:
    def test_options_reach_run_download(self, runner, captured_run, tmp_path):
        jar = tmp_path / "cookies.txt"
        jar.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

        result = runner.invoke(
            cli,
            [
                "https://ok.example",
                "--resolution",
                "1080",
                "--playlist-items",
                "1-5",
                "--cookies",
                str(jar),
                "--list-formats",
            ],
        )

        assert result.exit_code == 0
        assert captured_run["resolution"] == "1080"
        assert captured_run["playlist_items"] == "1-5"
        assert captured_run["cookie_file"] == str(jar)
        assert captured_run["show_formats"] is True

    def test_legacy_underscore_options_still_work(self, runner, captured_run):
        result = runner.invoke(cli, ["https://ok.example", "--playlist_items", "2"])

        assert result.exit_code == 0
        assert captured_run["playlist_items"] == "2"

    def test_noplaylist_is_tri_state(self, runner, captured_run):
        runner.invoke(cli, ["https://ok.example"])
        assert captured_run["noplaylist"] is None

        runner.invoke(cli, ["https://ok.example", "--noplaylist"])
        assert captured_run["noplaylist"] is True

        runner.invoke(cli, ["https://ok.example", "--yes-playlist"])
        assert captured_run["noplaylist"] is False


def test_help_lists_the_documented_options(runner):
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    for option in ("--url-list", "--resolution", "--cookies", "--list-formats", "--verbose"):
        assert option in result.output
