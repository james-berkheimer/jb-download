"""jb-download: a yt-dlp front end driven by a JSON settings file."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("jb-download")
except importlib.metadata.PackageNotFoundError:  # pragma: no cover - source checkout
    __version__ = "unknown"

__all__ = ["__version__"]
