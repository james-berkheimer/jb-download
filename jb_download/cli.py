import click

from jb_download.downloader import run_download


@click.command()
@click.argument("url", required=False)
@click.option(
    "--url_list",
    "url_list_path",
    type=click.Path(exists=True),
    help="Path to a text file with a list of URLs.",
)
@click.option("--resolution", default=None, help="Maximum resolution to download (e.g., 1080).")
@click.option("--noplaylist", is_flag=True, default=False, help="Download single video, not a playlist.")
@click.option("--playlist_items", default=None, help="Number of the playlist item to download.")
@click.option(
    "--output_path",
    type=click.Path(),
    help="Path to the directory where the downloaded videos will be saved.",
)
def cli(
    url: str,
    url_list_path: str,
    resolution: str,
    noplaylist: bool,
    playlist_items: str,
    output_path: str,
) -> None:
    run_download(
        url=url,
        url_list_path=url_list_path,
        resolution=resolution,
        noplaylist=noplaylist,
        playlist_items=playlist_items,
        output_path=output_path,
    )


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
