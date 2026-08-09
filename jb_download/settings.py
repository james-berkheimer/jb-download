"""Load jb-download settings and translate them into yt-dlp options."""

import importlib.metadata
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from jb_download.logger import get_logger

log = get_logger()

#: Settings file shipped inside the installed package.
PACKAGED_DEFAULTS = Path(__file__).with_name("default_settings.json")

#: Settings file written by the installer on a system install.
SYSTEM_SETTINGS = Path("/opt/jb-download/jb-download_settings.json")

#: Environment variable pointing at a settings file.
SETTINGS_ENV_VAR = "JBDOWNLOAD_SETTINGS"

#: Environment variable holding the root media directory.
MEDIA_ROOT_ENV_VAR = "MEDIA_DOWNLOAD_PATH"

DEFAULT_MEDIA_ROOT = "/mnt/media/transmission"

#: Format selectors that resolve to audio only and must not take a height filter.
_AUDIO_ONLY_PREFIXES = ("bestaudio", "worstaudio", "ba", "wa")


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``overrides`` into a copy of ``base``.

    Args:
        base: Baseline mapping, typically the packaged defaults.
        overrides: Mapping whose values win on conflict.

    Returns:
        A new merged mapping. Neither argument is modified.
    """
    merged = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _parse_js_runtimes(specs: list[str]) -> dict[str, dict[str, str | None]]:
    """Build the ``js_runtimes`` mapping yt-dlp expects.

    YouTube extraction without a JavaScript runtime is deprecated and can hide
    formats, so the runtimes to try are configurable. Each entry is a runtime
    name with an optional explicit path (``node:/usr/local/bin/node``). yt-dlp
    ignores names it does not support and runtimes that are not installed.

    Args:
        specs: Runtime specifications from the settings file.

    Returns:
        A mapping of runtime name to its options.
    """
    runtimes: dict[str, dict[str, str | None]] = {}
    for spec in specs:
        name, separator, path = str(spec).partition(":")
        name = name.strip().lower()
        if name:
            runtimes[name] = {"path": path.strip() if separator else None}
    return runtimes


def _parse_browser_spec(spec: str) -> tuple[str | None, str | None, str | None, str | None]:
    """Parse a ``--cookies-from-browser`` value into the tuple yt-dlp expects.

    Accepts a bare browser name (``firefox``) or a name with a profile name or
    path (``firefox:/srv/profiles/abcd.default``), mirroring the yt-dlp CLI. The
    profile form matters when the cookies were copied off another machine.

    Args:
        spec: Browser specification string.

    Returns:
        A ``(browser, profile, keyring, container)`` tuple.
    """
    name, separator, profile = spec.partition(":")
    return (name.strip().lower(), profile.strip() if separator else None, None, None)


#: Cookie database filename inside a Firefox profile directory.
_FIREFOX_COOKIE_DB = "cookies.sqlite"


def _browser_profile_ready(spec: tuple[str | None, str | None, str | None, str | None]) -> bool:
    """Report whether a browser cookie source can actually be read.

    An explicit Firefox profile directory is checked for its cookie database so
    that a not-yet-populated profile degrades to "no cookies" instead of failing
    every download. Anything else is left for yt-dlp to resolve.

    Args:
        spec: A parsed ``(browser, profile, keyring, container)`` tuple.

    Returns:
        ``True`` if the spec should be handed to yt-dlp.
    """
    browser, profile = spec[0], spec[1]
    if browser != "firefox" or not profile or not Path(profile).is_absolute():
        return True

    if (Path(profile) / _FIREFOX_COOKIE_DB).is_file():
        return True

    log.debug(f"No {_FIREFOX_COOKIE_DB} in Firefox profile '{profile}'; continuing without cookies.")
    return False


def _limit_height(selector: str, height: str) -> str:
    """Apply a maximum height filter to every video term of one format selector.

    ``bestvideo[ext=mp4]+bestaudio[ext=m4a]`` becomes
    ``bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]``: the filter has to be
    attached to each video term individually, because a filter appended to the end
    of the whole string binds only to the final term.

    Args:
        selector: A single format selector, possibly a ``+`` joined pair.
        height: Maximum height in pixels, as a string.

    Returns:
        The selector with height filters applied.
    """
    terms = []
    for raw_term in selector.split("+"):
        term = raw_term.strip()
        if not term or "[height" in term or term.startswith(_AUDIO_ONLY_PREFIXES):
            terms.append(term)
        else:
            terms.append(f"{term}[height<={height}]")
    return "+".join(terms)


class DownloadConfig:
    """Load jb-download settings and build the yt-dlp option mapping from them."""

    settings_path: Path | None
    output_dir: Path
    version: str
    _data: dict[str, Any]

    def __init__(self, settings_path: Path | str | None = None) -> None:
        """Load settings, layering a user settings file over the packaged defaults.

        Resolution order for the user settings file: the explicit ``settings_path``
        argument, then ``$JBDOWNLOAD_SETTINGS``, then the system install location.
        A missing or unreadable file is a warning, not an error -- the packaged
        defaults are always the baseline.

        Args:
            settings_path: Explicit path to a settings file, if any.
        """
        self.settings_path = self._resolve_settings_path(settings_path)
        self._data = _deep_merge(self._load_json(PACKAGED_DEFAULTS), self._load_user_settings())

        media_root = os.getenv(MEDIA_ROOT_ENV_VAR, DEFAULT_MEDIA_ROOT)
        subdir = Path(self._data.get("output_dir", "youtube"))
        self.output_dir = subdir if subdir.is_absolute() else Path(media_root) / subdir

        self.version = self._load_version()

    @staticmethod
    def _resolve_settings_path(settings_path: Path | str | None) -> Path | None:
        if settings_path is not None:
            return Path(settings_path)
        env_path = os.getenv(SETTINGS_ENV_VAR)
        if env_path:
            return Path(env_path)
        if SYSTEM_SETTINGS.is_file():
            return SYSTEM_SETTINGS
        return None

    def _load_user_settings(self) -> dict[str, Any]:
        if self.settings_path is None:
            log.debug("No user settings file found; using packaged defaults.")
            return {}
        return self._load_json(self.settings_path)

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        try:
            log.debug(f"Loading jb-download settings from {path}")
            with path.open(encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            log.warning(f"Unable to load settings from '{path}': {exc}")
            return {}

    @staticmethod
    def _load_version() -> str:
        try:
            return importlib.metadata.version("jb-download")
        except importlib.metadata.PackageNotFoundError:
            log.warning("Unable to determine the jb-download package version.")
            return "unknown"

    def get(self, key: str, default: Any = None) -> Any:  # noqa: ANN401 - JSON values are Any
        """Return a raw top-level settings value.

        Args:
            key: Top-level settings key.
            default: Value returned when the key is absent.

        Returns:
            The configured value, or ``default``.
        """
        return self._data.get(key, default)

    @property
    def log_level(self) -> str:
        """Configured console log level name, e.g. ``"INFO"``."""
        logger_settings = self._data.get("logger", {})
        if not logger_settings.get("enabled", True):
            return "CRITICAL"
        return str(logger_settings.get("level", "INFO")).upper()

    def get_format_string(self, resolution: str | None = None) -> str:
        """Build the yt-dlp format selector chain.

        Every entry of the ``formats`` list becomes one alternative in a ``/``
        separated fallback chain, so a site that cannot satisfy the preferred
        codec/container still matches a later, looser alternative. When
        ``fallback_to_best`` is enabled a bare ``best`` is appended as the final
        alternative so format selection never fails outright.

        Args:
            resolution: Optional maximum height in pixels.

        Returns:
            A yt-dlp format selector string.
        """
        formats = [fmt for fmt in self._data.get("formats", []) if fmt]
        if not formats:
            formats = ["bestvideo+bestaudio"]

        if self._data.get("fallback_to_best", True) and formats[-1].strip() not in ("best", "b"):
            formats = [*formats, "best"]

        chain = "/".join(formats)
        if resolution:
            chain = "/".join(_limit_height(alt, resolution) for alt in chain.split("/"))
        return chain

    def _build_postprocessors(self) -> list[dict[str, Any]]:
        subtitles = self._data.get("subtitles", {})
        postprocessors: list[dict[str, Any]] = []

        # Remuxing has to happen before anything is embedded, so that subtitles
        # and metadata land in the final container. This matches yt-dlp's own order.
        remux = self._data.get("remux_video")
        if remux:
            postprocessors.append({"key": "FFmpegVideoRemuxer", "preferedformat": remux})

        if self._data.get("embed_subs") or subtitles.get("embed_subs"):
            postprocessors.append({"key": "FFmpegEmbedSubtitle"})
        if self._data.get("embed_metadata"):
            postprocessors.append({"key": "FFmpegMetadata"})
        if self._data.get("embed_thumbnail"):
            postprocessors.append({"key": "EmbedThumbnail"})

        postprocessors.extend(self._data.get("postprocessors", []))
        return postprocessors

    def _build_cookie_opts(
        self, cookie_file: str | None = None, browser: str | None = None
    ) -> dict[str, Any]:
        """Resolve cookie options, preferring browser cookies when both are configured."""
        opts: dict[str, Any] = {}
        browser = browser or (
            self._data.get("cookie_browser", "chrome") if self._data.get("use_browser_cookies") else None
        )

        if browser:
            spec = _parse_browser_spec(browser)
            if _browser_profile_ready(spec):
                opts["cookiesfrombrowser"] = spec
                return opts

        configured = cookie_file or self._data.get("cookie_file")
        if configured:
            path = Path(configured).expanduser()
            if self._cookie_file_usable(path):
                opts["cookiefile"] = str(path)
        return opts

    @staticmethod
    def _cookie_file_usable(path: Path) -> bool:
        """Report whether a cookie file should be handed to yt-dlp.

        A path we cannot stat (for example one under another user's home) is
        passed through anyway and left for yt-dlp to report on.

        Args:
            path: Configured cookie file path.

        Returns:
            ``True`` if the path should be used.
        """
        try:
            if path.is_file():
                return True
        except OSError as exc:
            log.warning(f"Cannot inspect cookie file '{path}' ({exc}); passing it to yt-dlp anyway.")
            return True

        # Only a problem for content that actually needs authentication, and the
        # error hint covers that case -- so this stays out of normal output.
        log.debug(f"Cookie file '{path}' does not exist; continuing without cookies.")
        return False

    def build_ydl_opts(
        self,
        *,
        resolution: str | None = None,
        noplaylist: bool | None = None,
        playlist_items: str | None = None,
        output_path: str | None = None,
        cookie_file: str | None = None,
        browser: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Translate the settings file plus CLI overrides into yt-dlp options.

        Args:
            resolution: Maximum video height in pixels.
            noplaylist: Download only the single video a playlist URL points at.
                ``None`` defers to the settings file.
            playlist_items: yt-dlp playlist item selection, e.g. ``"1-5"``.
            output_path: Destination directory, overriding the configured one.
            cookie_file: Cookie file path, overriding the configured one.
            browser: Browser to read cookies from, overriding the configured one.
            extra: Raw yt-dlp options merged in last, overriding everything.

        Returns:
            A mapping suitable for ``YoutubeDL(...)``.
        """
        data = self._data
        subtitles = data.get("subtitles", {})
        playlist = data.get("playlist", {})
        sleep = data.get("sleep_interval", {})

        output_dir = Path(output_path) if output_path else self.output_dir
        template = data.get("output_template", "%(title)s.%(ext)s")

        opts: dict[str, Any] = {
            "format": self.get_format_string(resolution),
            "outtmpl": str(output_dir / template),
            "merge_output_format": data.get("merge_output_format", "mp4"),
            "restrictfilenames": bool(data.get("restrict_filenames", False)),
            "writedescription": bool(data.get("write_description", False)),
            "writeinfojson": bool(data.get("write_info_json", False)),
            "writethumbnail": bool(data.get("write_thumbnail", False)),
            "writesubtitles": bool(subtitles.get("write_subs", False)),
            "subtitleslangs": list(subtitles.get("sub_langs", ["en"])),
            "geo_bypass": bool(data.get("geo_bypass", False)),
            "postprocessors": self._build_postprocessors(),
        }

        runtimes = _parse_js_runtimes(data.get("js_runtimes", []))
        if runtimes:
            opts["js_runtimes"] = runtimes

        if data.get("no_overwrites", False):
            opts["overwrites"] = False

        concurrency = data.get("concurrent_fragment_downloads")
        if concurrency:
            opts["concurrent_fragment_downloads"] = int(concurrency)

        if sleep.get("min") is not None:
            opts["sleep_interval"] = sleep["min"]
        if sleep.get("max") is not None:
            opts["max_sleep_interval"] = sleep["max"]

        proxy = data.get("proxy")
        if proxy:
            opts["proxy"] = proxy

        opts["noplaylist"] = (
            bool(playlist.get("noplaylist", False)) if noplaylist is None else noplaylist
        )
        items = playlist_items if playlist_items is not None else playlist.get("playlist_items")
        if items:
            opts["playlist_items"] = items

        opts.update(self._build_cookie_opts(cookie_file=cookie_file, browser=browser))

        if extra:
            opts.update(extra)
        return opts
