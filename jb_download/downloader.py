import logging
from pathlib import Path

from yt_dlp import YoutubeDL

from jb_download.settings import DownloadConfig

log = logging.getLogger("jb-download")
CONFIG = DownloadConfig()


def my_hook(d) -> None:
    if d["status"] == "finished":
        log.info("Done downloading, now converting ...")


def download_video(ydl: YoutubeDL, url: str) -> None:
    try:
        info = ydl.extract_info(url, download=False)
        log.info(f"Title: {info['title']}")
        ydl.download([url])
    except Exception as e:
        log.error(f"Error downloading video: {e}")


def run_download(
    url: str | None,
    url_list_path: str | None,
    resolution: str | None,
    noplaylist: bool,
    playlist_items: str | None,
    output_path: str | None,
) -> None:
    if noplaylist and playlist_items:
        raise ValueError("You cannot use --playlist_items when --noplaylist is set.")

    output_dir = Path(output_path) if output_path else CONFIG.output_dir
    output_template = output_dir / CONFIG.output_template
    format_string = CONFIG.get_format_string(resolution)

    # Resolve cookie settings
    cookie_file = CONFIG._data.get("cookie_file")
    use_browser_cookies = CONFIG._data.get("use_browser_cookies", False)

    ydl_opts = {
        "format": format_string,
        "noplaylist": noplaylist,
        "progress_hooks": [my_hook],
        "outtmpl": str(output_template),
        "playlist_items": playlist_items,
        "merge_output_format": "mkv",
    }

    if use_browser_cookies:
        ydl_opts["cookiesfrom_browser"] = "chrome"
    elif cookie_file:
        ydl_opts["cookies"] = cookie_file

    ydl_opts.update(CONFIG.default_flags)

    with YoutubeDL(ydl_opts) as ydl:
        if url_list_path:
            try:
                with open(url_list_path) as f:
                    urls = f.read().splitlines()
                for u in urls:
                    download_video(ydl, u)
            except Exception as e:
                log.error(f"Error reading file: {e}")
        elif url:
            download_video(ydl, url)
        else:
            raise ValueError("You must provide a URL or a list of URLs.")
