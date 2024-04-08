import platform
from pathlib import Path

import click
from yt_dlp import YoutubeDL

# Determine the platform
system = platform.system()

if system == "Windows":
    DEST = Path("T:/youtube")
elif system == "Linux":
    DEST = Path("/mnt/Transmission/youtube")
elif system == "Darwin":  # MacOS
    DEST = Path("/Volumes/Transmission/youtube")
elif system == "FreeBSD":
    DEST = Path("/media/transmission/")
else:
    raise Exception(f"Unsupported platform: {system}")

FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
ERROR_MESSAGE = "You must provide a URL or a list of URLs."


def my_hook(d):
    if d["status"] == "finished":
        print("Done downloading, now converting ...")


def download_video(ydl, url):
    try:
        info = ydl.extract_info(url, download=False)
        print(f"Title: {info['title']}")
        ydl.download([url])
    except Exception as e:
        print(f"Error downloading video: {e}")


@click.command()
@click.argument("url", required=False)
@click.option(
    "--url_list",
    "url_list_path",
    type=click.Path(exists=True),
    help="Path to a text file with a list of URLs.",
)
@click.option(
    "--noplaylist", is_flag=True, default=False, help="Download single video, not a playlist."
)
@click.option("--playlist_items", default=None, help="Number of the playlist item to download.")
@click.option(
    "--output_path",
    type=click.Path(),
    help="Path to the directory where the downloaded videos will be saved.",
)
def cli(url, url_list_path, noplaylist, playlist_items, output_path):
    if noplaylist and playlist_items:
        raise click.BadOptionUsage(
            "playlist_items", "You cannot use --playlist_items when --noplaylist is set."
        )
    output_path = Path(output_path) if output_path else DEST
    ydl_opts = {
        "format": FORMAT,
        "noplaylist": noplaylist,
        "progress_hooks": [my_hook],
        "outtmpl": f"{output_path}/%(title)s",
        "playlist_items": playlist_items,
    }
    with YoutubeDL(ydl_opts) as ydl:
        if url_list_path:
            try:
                with open(url_list_path, "r") as f:
                    urls = f.read().splitlines()
                for url in urls:
                    download_video(ydl, url)
            except Exception as e:
                print(f"Error reading file: {e}")
        elif url:
            download_video(ydl, url)
        else:
            raise click.BadParameter(ERROR_MESSAGE)


def main():
    cli()


if __name__ == "__main__":
    main()
