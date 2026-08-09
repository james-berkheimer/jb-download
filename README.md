# JB Download

A command-line utility for downloading media using [yt-dlp](https://github.com/yt-dlp/yt-dlp), with a
JSON settings file, virtual environment isolation, and one-command updating.

---

## Quick Start: Install Locally

To install `jb-download` into `/opt/jb-download` with a virtual environment:

### 1. Download the installer bundle

```bash
curl -L https://github.com/james-berkheimer/jb-download/releases/latest/download/install-jb-download.tar.gz | tar xz
cd jb-download-installer
chmod +x install.sh
```

### 2. Run the installer

```bash
sudo ./install.sh
```

This will:

- Install Python, ffmpeg, and required tools
- Create a virtual environment in `/opt/jb-download/venv`
- Download the latest jb-download wheel from GitHub Releases
- Install jb-download into the venv
- Write default settings to `/opt/jb-download/jb-download_settings.json` (an existing file is never overwritten)
- Install the update and uninstall scripts into `/opt/jb-download`
- Add aliases and environment config via `/etc/profile.d/jb-download.sh`

---

## Usage

```bash
jb-download <URL>                              # download a single video
jb-download <URL> --resolution 1080            # cap the resolution
jb-download <PLAYLIST_URL> --playlist-items 1-5
jb-download <PLAYLIST_URL> --noplaylist        # just the one video the URL points at
jb-download --url-list urls.txt                # one URL per line; '#' comments are ignored
jb-download <URL> --output-path /mnt/media/clips
jb-download <URL> --list-formats               # inspect what a site offers, download nothing
jb-download <URL> --verbose                    # debug logging, including the yt-dlp options used
```

### Options

| Option | Description |
| --- | --- |
| `--url-list PATH` | Text file with one URL per line. Blank lines and `#` comments are skipped. |
| `--resolution N` | Maximum video height in pixels (e.g. `1080`). |
| `--noplaylist` / `--yes-playlist` | Override the configured playlist behaviour. Unset defers to settings. |
| `--playlist-items SPEC` | Playlist selection, e.g. `1-5` or `2,4`. |
| `--output-path DIR` | Destination directory, overriding `output_dir`. |
| `--cookies PATH` | Cookie file in Netscape format. Required for age-restricted videos. |
| `--cookies-from-browser NAME` | Read cookies from a local browser (`chrome`, `firefox`, ...). |
| `--list-formats` | Print the available formats instead of downloading. |
| `--settings PATH` | Use a specific settings file, overriding `$JBDOWNLOAD_SETTINGS`. |
| `--verbose` | Enable debug logging. |
| `--version` | Print the installed version. |

The command exits `0` when every URL succeeded and `1` if any failed, so it is safe to use in scripts.

### Authentication (age-restricted videos)

YouTube refuses age-restricted videos with *"Sign in to confirm your age"* unless it gets cookies from a
signed-in account. Export cookies to a Netscape-format `cookies.txt` and either point `cookie_file` at it
in your settings or pass it per run:

```bash
jb-download <URL> --cookies /root/.jbtools/cookies/youtube.com_cookies.txt
```

If the machine running jb-download has the browser installed, read cookies straight from it:

```bash
jb-download <URL> --cookies-from-browser firefox
```

#### Producing a cookies file without a browser extension

On a headless box the browser lives on a *different* machine, so use one of these. Neither
needs any third-party software.

**If that machine runs Firefox** — copy the profile directory over and point at it. Firefox
stores cookies unencrypted, so the profile is portable across machines and operating systems:

```bash
# on the machine with Firefox, find the profile directory:
#   Windows: %APPDATA%\Mozilla\Firefox\Profiles\<something>.default-release
#   macOS:   ~/Library/Application Support/Firefox/Profiles/<something>.default-release
#   Linux:   ~/.mozilla/firefox/<something>.default-release
# copy it to the download host, then:
jb-download <URL> --cookies-from-browser "firefox:/root/.jbtools/firefox-profile"
```

Close Firefox before copying, so `cookies.sqlite` is not mid-write.

**If that machine runs Chrome or Edge** — the cookie database is encrypted against the local
user account and cannot be decrypted elsewhere, so the export has to happen on that machine.
Install yt-dlp there and have it write the cookies out:

```bash
yt-dlp --cookies-from-browser chrome --cookies cookies.txt --skip-download "https://www.youtube.com/watch?v=BaW_jenozKc"
```

Copy the resulting `cookies.txt` to the download host and set `cookie_file` to its path.

See the [yt-dlp cookie FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
for background.

---

## Settings

Defaults ship inside the package (`jb_download/default_settings.json`). Your settings file is layered
**on top of** those defaults, so it only needs the keys you want to change. Resolution order:

1. `--settings PATH`
2. `$JBDOWNLOAD_SETTINGS`
3. `/opt/jb-download/jb-download_settings.json`
4. the packaged defaults

| Key | Description |
| --- | --- |
| `output_dir` | Destination directory. Relative paths are resolved under `$MEDIA_DOWNLOAD_PATH` (default `/mnt/media/transmission`); absolute paths are used as-is. |
| `formats` | List of yt-dlp format selectors, tried in order as a fallback chain. |
| `fallback_to_best` | Append a bare `best` as the last resort so selection never fails outright. |
| `merge_output_format` | Container for merged video+audio, e.g. `mp4`. |
| `remux_video` | Remux the finished file into this container (requires ffmpeg). Empty disables it. |
| `output_template` | yt-dlp output template, e.g. `%(title)s.%(ext)s`. |
| `restrict_filenames` | Strip spaces and special characters from filenames. |
| `no_overwrites` | Never overwrite an existing file. |
| `write_description` / `write_info_json` / `write_thumbnail` | Write the sidecar files alongside the video. Off by default. |
| `embed_metadata` / `embed_thumbnail` / `embed_subs` | Post-process the media file (requires ffmpeg). |
| `subtitles.write_subs` / `subtitles.sub_langs` / `subtitles.embed_subs` | Subtitle handling. |
| `postprocessors` | Extra raw yt-dlp postprocessor entries. |
| `concurrent_fragment_downloads` | Parallel fragment downloads for HLS/DASH. |
| `sleep_interval.min` / `sleep_interval.max` | Random delay between downloads, to avoid rate limiting. |
| `proxy` | Proxy URL. Empty means no proxy. |
| `geo_bypass` | Attempt to bypass geographic restrictions. |
| `js_runtimes` | JavaScript runtimes to try for YouTube extraction, e.g. `["deno", "node"]` or `["node:/usr/bin/node"]`. yt-dlp ignores ones that are not installed. An empty list disables them. |
| `playlist.noplaylist` / `playlist.playlist_items` | Default playlist behaviour. |
| `logger.enabled` / `logger.level` | Console logging. |
| `cookie_file` | Path to a Netscape-format cookie file. |
| `use_browser_cookies` / `cookie_browser` | Read cookies from a browser profile instead. `cookie_browser` accepts `firefox` or `firefox:/path/to/profile`. |

### About `formats`

Each entry is one alternative in a `/` separated yt-dlp fallback chain, tried left to right. This matters
because many sites report `unknown` codecs, so a strict selector like `bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]`
matches nothing there and the download fails with *"Requested format is not available"*. Keep a loose
alternative at the end (or leave `fallback_to_best` enabled) so those sites still work.

`--resolution` is applied to every video term of every alternative, so it constrains the whole chain
rather than just the last entry.

---

## Aliases

After reboot or `source /etc/profile`, the following commands will be available:

```bash
jb-download             # Run the CLI
jb-download-update      # Pull the latest jb-download release and install it
jb-download-uninstall   # Remove jb-download from system
jb-download-settings    # Open your active jb-download settings.json
```

---

## Updating

```bash
jb-download-update
```

This checks the latest GitHub Release, installs it into the existing venv if it is newer, and leaves your
settings file untouched.

---

## Uninstalling

```bash
sudo jb-download-uninstall
```

This prompts for confirmation (pass `-y` to skip), backs your settings up to
`/root/jb-download_settings.json.bak`, then removes `/opt/jb-download` and the alias file.

---

## Developer Info

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

.venv/bin/ruff check .          # lint
.venv/bin/ruff format .         # format
.venv/bin/python -m pytest      # tests
```

CI runs lint, format check, shellcheck, and the test suite before any version bump or release, so a
failing check blocks the release rather than shipping it.

Releases are available at: https://github.com/james-berkheimer/jb-download/releases

---

## Versioning

Versioning is handled automatically via GitHub Actions. The `VERSION` file is updated and tagged on every
push to `main` that passes the quality gate.

---

## License

MIT © James Berkheimer
