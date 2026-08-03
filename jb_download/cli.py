"""Command-line entry point for jb-download."""

import sys

import click

from jb_download.downloader import run_download
from jb_download.logger import setup_logger
from jb_download.settings import DownloadConfig


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("url", required=False)
@click.option(
    "--url-list",
    "--url_list",
    "url_list_path",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to a text file with one URL per line.",
)
@click.option("--resolution", default=None, help="Maximum resolution to download (e.g. 1080).")
@click.option(
    "--noplaylist/--yes-playlist",
    default=None,
    help="Download only the single video a playlist URL points at.",
)
@click.option(
    "--playlist-items",
    "--playlist_items",
    "playlist_items",
    default=None,
    help="Playlist items to download (e.g. 1-5).",
)
@click.option(
    "--output-path",
    "--output_path",
    "output_path",
    type=click.Path(file_okay=False),
    help="Directory where the downloaded media is saved.",
)
@click.option(
    "--cookies",
    "cookie_file",
    type=click.Path(exists=True, dir_okay=False),
    help="Cookie file to authenticate with (needed for age-restricted videos).",
)
@click.option(
    "--cookies-from-browser",
    "browser",
    default=None,
    help="Read cookies from this browser instead of a cookie file (e.g. chrome, firefox).",
)
@click.option(
    "--list-formats",
    "show_formats",
    is_flag=True,
    default=False,
    help="List the formats a URL offers instead of downloading it.",
)
@click.option(
    "--settings",
    "settings_path",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to a settings file, overriding $JBDOWNLOAD_SETTINGS.",
)
@click.option("--verbose", is_flag=True, default=False, help="Enable debug logging.")
@click.version_option(package_name="jb-download")
def cli(
    url: str | None,
    url_list_path: str | None,
    resolution: str | None,
    noplaylist: bool | None,
    playlist_items: str | None,
    output_path: str | None,
    cookie_file: str | None,
    browser: str | None,
    show_formats: bool,
    settings_path: str | None,
    verbose: bool,
) -> None:
    """Download media from URL, or from every URL listed in --url-list."""
    # Configure logging before loading settings so settings warnings are visible.
    logger = setup_logger("DEBUG" if verbose else "INFO")
    config = DownloadConfig(settings_path)
    if not verbose:
        logger.setLevel(config.log_level)

    try:
        failures = run_download(
            url=url,
            url_list_path=url_list_path,
            resolution=resolution,
            noplaylist=noplaylist,
            playlist_items=playlist_items,
            output_path=output_path,
            cookie_file=cookie_file,
            browser=browser,
            show_formats=show_formats,
            config=config,
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    except KeyboardInterrupt:
        logger.warning("Interrupted.")
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001 - last resort, keeps tracebacks off the console
        logger.error(f"Unexpected error: {exc}")
        logger.debug("Traceback:", exc_info=True)
        sys.exit(1)

    if failures:
        sys.exit(1)


def main() -> None:
    """Run the jb-download command-line interface."""
    cli()


if __name__ == "__main__":
    main()
