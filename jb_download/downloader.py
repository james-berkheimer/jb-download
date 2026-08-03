"""Drive yt-dlp downloads from jb-download settings."""

from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL

from jb_download.logger import get_logger
from jb_download.settings import DownloadConfig

log = get_logger()

#: Substrings of yt-dlp errors that we can give the user a concrete next step for.
_ERROR_HINTS: tuple[tuple[str, str], ...] = (
    (
        "sign in to confirm your age",
        (
            "This video is age-restricted. Point 'cookie_file' in your settings at an exported "
            "cookies.txt, or pass --cookies /path/to/cookies.txt, or use --cookies-from-browser."
        ),
    ),
    (
        "confirm you're not a bot",
        (
            "YouTube is rate-limiting this host. Supply cookies via --cookies or "
            "--cookies-from-browser, or retry later."
        ),
    ),
    (
        "requested format is not available",
        (
            "No configured format matched this site. Run with --list-formats to see what it "
            "offers, or loosen the 'formats' list in your settings."
        ),
    ),
    (
        "private video",
        "This video is private; an account cookie for a user with access is required.",
    ),
)


def _progress_hook(status: dict[str, Any]) -> None:
    """Log yt-dlp progress transitions.

    Args:
        status: Progress dictionary supplied by yt-dlp.
    """
    if status.get("status") == "finished":
        log.info("Download finished, post-processing ...")


def _log_error_hint(message: str) -> None:
    """Print an actionable hint when a yt-dlp error has a known remedy.

    Args:
        message: The yt-dlp error message.
    """
    lowered = message.lower()
    for needle, hint in _ERROR_HINTS:
        if needle in lowered:
            log.warning(hint)
            return


def read_url_list(path: str | Path) -> list[str]:
    """Read URLs from a text file, one per line.

    Blank lines and ``#`` comments are ignored.

    Args:
        path: Path to the URL list file.

    Returns:
        The URLs found in the file.

    Raises:
        OSError: If the file cannot be read.
    """
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def download_video(ydl: YoutubeDL, url: str) -> bool:
    """Download a single URL.

    Args:
        ydl: A configured yt-dlp instance.
        url: The URL to download.

    Returns:
        ``True`` on success, ``False`` if the download failed.
    """
    try:
        ydl.download([url])
    except Exception as exc:  # noqa: BLE001 - yt-dlp raises a wide range of errors
        log.error(f"Failed to download {url}: {exc}")
        _log_error_hint(str(exc))
        return False
    return True


def list_formats(ydl: YoutubeDL, url: str) -> bool:
    """Print the formats a URL offers instead of downloading it.

    Args:
        ydl: A configured yt-dlp instance.
        url: The URL to inspect.

    Returns:
        ``True`` on success, ``False`` if extraction failed.
    """
    try:
        ydl.extract_info(url, download=False)
    except Exception as exc:  # noqa: BLE001 - yt-dlp raises a wide range of errors
        log.error(f"Failed to inspect {url}: {exc}")
        _log_error_hint(str(exc))
        return False
    return True


def run_download(
    url: str | None = None,
    url_list_path: str | None = None,
    resolution: str | None = None,
    noplaylist: bool | None = None,
    playlist_items: str | None = None,
    output_path: str | None = None,
    cookie_file: str | None = None,
    browser: str | None = None,
    show_formats: bool = False,
    config: DownloadConfig | None = None,
) -> int:
    """Download one URL or every URL in a list file.

    Args:
        url: A single URL to download.
        url_list_path: Path to a file containing one URL per line.
        resolution: Maximum video height in pixels.
        noplaylist: Download only the video a playlist URL points at. ``None``
            defers to the settings file.
        playlist_items: yt-dlp playlist item selection, e.g. ``"1-5"``.
        output_path: Destination directory, overriding the configured one.
        cookie_file: Cookie file path, overriding the configured one.
        browser: Browser to read cookies from, overriding the configured one.
        show_formats: List available formats instead of downloading.
        config: Pre-loaded settings. Loaded from disk when omitted.

    Returns:
        The number of URLs that failed.

    Raises:
        ValueError: If no URL was supplied, or if mutually exclusive playlist
            options were combined.
    """
    if noplaylist and playlist_items:
        raise ValueError("You cannot use --playlist-items together with --noplaylist.")
    if not url and not url_list_path:
        raise ValueError("You must provide a URL or a URL list file.")

    config = config or DownloadConfig()

    if url_list_path:
        urls = read_url_list(url_list_path)
        if not urls:
            log.warning(f"No URLs found in {url_list_path}.")
            return 0
    else:
        urls = [url]

    extra: dict[str, Any] = {"progress_hooks": [_progress_hook]}
    if show_formats:
        extra["listformats"] = True

    ydl_opts = config.build_ydl_opts(
        resolution=resolution,
        noplaylist=noplaylist,
        playlist_items=playlist_items,
        output_path=output_path,
        cookie_file=cookie_file,
        browser=browser,
        extra=extra,
    )
    log.debug(f"yt-dlp options: {ydl_opts}")

    action = list_formats if show_formats else download_video
    failures = 0
    with YoutubeDL(ydl_opts) as ydl:
        for target in urls:
            if not action(ydl, target):
                failures += 1

    if failures:
        log.error(f"{failures} of {len(urls)} URL(s) failed.")
    return failures
