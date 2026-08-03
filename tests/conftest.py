import json
from pathlib import Path

import pytest

from jb_download.settings import DownloadConfig


@pytest.fixture(autouse=True)
def _isolate_environment(monkeypatch, tmp_path):
    """Keep tests off the developer's real settings file and media root."""
    monkeypatch.delenv("JBDOWNLOAD_SETTINGS", raising=False)
    monkeypatch.setenv("MEDIA_DOWNLOAD_PATH", str(tmp_path / "media"))
    monkeypatch.setattr("jb_download.settings.SYSTEM_SETTINGS", tmp_path / "does-not-exist.json")


@pytest.fixture
def make_config(tmp_path):
    """Build a DownloadConfig from an override dict written to a temp file."""

    def _make(overrides: dict | None = None) -> DownloadConfig:
        if overrides is None:
            return DownloadConfig()
        path = Path(tmp_path) / "settings.json"
        path.write_text(json.dumps(overrides), encoding="utf-8")
        return DownloadConfig(path)

    return _make
