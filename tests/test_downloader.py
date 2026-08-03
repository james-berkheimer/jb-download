import pytest

from jb_download import downloader
from jb_download.downloader import read_url_list, run_download


class FakeYoutubeDL:
    """Stand-in for yt-dlp that records calls and fails for flagged URLs."""

    instances = []

    def __init__(self, opts):
        self.opts = opts
        self.downloaded = []
        self.inspected = []
        FakeYoutubeDL.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def download(self, urls):
        for url in urls:
            if "fail" in url:
                raise RuntimeError("Requested format is not available")
            self.downloaded.append(url)

    def extract_info(self, url, download=True):
        self.inspected.append(url)
        return {"title": "t"}


@pytest.fixture
def fake_ydl(monkeypatch):
    FakeYoutubeDL.instances = []
    monkeypatch.setattr(downloader, "YoutubeDL", FakeYoutubeDL)
    return FakeYoutubeDL


class TestReadUrlList:
    def test_blank_lines_and_comments_are_skipped(self, tmp_path):
        path = tmp_path / "urls.txt"
        path.write_text("https://a.example\n\n  # a comment\nhttps://b.example  \n", encoding="utf-8")

        assert read_url_list(path) == ["https://a.example", "https://b.example"]


class TestRunDownload:
    def test_single_url_is_downloaded(self, fake_ydl, make_config):
        failures = run_download(url="https://ok.example", config=make_config())

        assert failures == 0
        assert fake_ydl.instances[0].downloaded == ["https://ok.example"]

    def test_failure_count_is_returned(self, fake_ydl, make_config):
        failures = run_download(url="https://fail.example", config=make_config())

        assert failures == 1

    def test_one_bad_url_does_not_stop_the_rest(self, fake_ydl, make_config, tmp_path):
        path = tmp_path / "urls.txt"
        path.write_text("https://a.example\nhttps://fail.example\nhttps://b.example\n")

        failures = run_download(url_list_path=str(path), config=make_config())

        assert failures == 1
        assert fake_ydl.instances[0].downloaded == ["https://a.example", "https://b.example"]

    def test_list_formats_inspects_instead_of_downloading(self, fake_ydl, make_config):
        run_download(url="https://ok.example", show_formats=True, config=make_config())

        assert fake_ydl.instances[0].inspected == ["https://ok.example"]
        assert fake_ydl.instances[0].downloaded == []
        assert fake_ydl.instances[0].opts["listformats"] is True

    def test_no_url_is_rejected(self, fake_ydl, make_config):
        with pytest.raises(ValueError, match="must provide a URL"):
            run_download(config=make_config())

    def test_conflicting_playlist_options_are_rejected(self, fake_ydl, make_config):
        with pytest.raises(ValueError, match="playlist-items"):
            run_download(
                url="https://ok.example",
                noplaylist=True,
                playlist_items="1-5",
                config=make_config(),
            )

    def test_empty_url_list_is_not_an_error(self, fake_ydl, make_config, tmp_path):
        path = tmp_path / "urls.txt"
        path.write_text("# nothing here\n")

        assert run_download(url_list_path=str(path), config=make_config()) == 0


class TestErrorHints:
    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("Sign in to confirm your age", "age-restricted"),
            ("Requested format is not available", "--list-formats"),
            ("Please confirm you're not a bot", "rate-limiting"),
        ],
    )
    def test_known_errors_produce_a_hint(self, caplog, message, expected):
        with caplog.at_level("WARNING", logger="jb-download"):
            downloader._log_error_hint(message)

        assert expected in caplog.text

    def test_unknown_errors_produce_no_hint(self, caplog):
        with caplog.at_level("WARNING", logger="jb-download"):
            downloader._log_error_hint("something else entirely")

        assert caplog.text == ""
