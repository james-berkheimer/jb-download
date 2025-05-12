import importlib.metadata
import json
import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger("jb-download")


class DownloadConfig:
    """Load and manage jb-download application settings from a JSON config file."""

    settings_path: Path
    output_dir: Path
    formats: list[str]
    output_template: str
    default_flags: dict[str, Any]
    _data: dict[str, Any]

    def __init__(self, settings_path: Path | None = None) -> None:
        env_path = os.getenv("JBDOWNLOAD_SETTINGS")
        media_base = os.getenv("MEDIA_DOWNLOAD_PATH", "/mnt/media/transmission")

        if settings_path is not None:
            self.settings_path = Path(settings_path)
        elif env_path:
            self.settings_path = Path(env_path)
        else:
            self.settings_path = Path(__file__).resolve().parents[1] / "settings.json"

        self._data = self._load_settings()

        # Load general settings
        subdir = self._data.get("output_dir", "youtube")
        self.output_dir = Path(media_base) / subdir
        self.formats = self._data.get("formats", ["bv*+ba/b"])
        self.output_template = self._data.get("output_template", "%(title)s.%(ext)s")

        # Optional flags
        self.default_flags = self._data.get("default_flags", {})

        # Load version
        self.version = self._load_version()

    def _load_settings(self) -> dict[str, Any]:
        try:
            log.debug(f"Loading jb-download settings from {self.settings_path}")
            with open(self.settings_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            log.warning(f"Unable to load settings from '{self.settings_path}': {e}")
            return {}

    def _load_version(self) -> str:
        try:
            return importlib.metadata.version("jb-download")
        except importlib.metadata.PackageNotFoundError:
            log.warning("Unable to load jb-download package version.")
            return "unknown"

    def get_format_string(self, resolution: str | None = None) -> str:
        formats = self.formats

        if resolution:
            formats = [
                f"{fmt}[height<={resolution}]" if "[height<=" not in fmt else fmt for fmt in formats
            ]

        return formats[0] if formats else "best"
