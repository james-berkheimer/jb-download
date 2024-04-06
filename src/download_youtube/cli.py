import click
from yt_dlp import YoutubeDL

DEST = "/mnt/Transmission/youtube/"


def my_hook(d):
    if d["status"] == "finished":
        print("Done downloading, now converting ...")


@click.command()
@click.argument("url")
@click.option(
    "--noplaylist", is_flag=True, default=False, help="Download single video, not a playlist."
)
@click.option("--playlist_items", default=None, help="Number of the playlist item to download.")
def cli(url, noplaylist, playlist_items):
    if noplaylist and playlist_items:
        raise click.BadOptionUsage(
            "playlist_items", "You cannot use --playlist_items when --noplaylist is set."
        )
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "noplaylist": noplaylist,
        "progress_hooks": [my_hook],
        "outtmpl": f"{DEST}/%(title)s",
        "playlist_items": playlist_items,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print(f"Title: {info['title']}")
        ydl.download([url])


def main():
    cli()


if __name__ == "__main__":
    main()
