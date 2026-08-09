import re

import pytest
from yt_dlp import YoutubeDL

from jb_download.settings import (
    DownloadConfig,
    _deep_merge,
    _limit_height,
    _parse_browser_spec,
)


class TestDeepMerge:
    def test_nested_dicts_are_merged_not_replaced(self):
        base = {"subtitles": {"write_subs": True, "sub_langs": ["en"]}, "proxy": ""}
        merged = _deep_merge(base, {"subtitles": {"sub_langs": ["de"]}})

        assert merged["subtitles"] == {"write_subs": True, "sub_langs": ["de"]}
        assert merged["proxy"] == ""

    def test_inputs_are_not_mutated(self):
        base = {"a": {"b": 1}}
        _deep_merge(base, {"a": {"b": 2}})

        assert base == {"a": {"b": 1}}


class TestLimitHeight:
    def test_filter_is_applied_to_each_video_term(self):
        assert (
            _limit_height("bestvideo[ext=mp4]+bestaudio[ext=m4a]", "1080")
            == "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]"
        )

    def test_audio_terms_are_left_alone(self):
        assert _limit_height("bestaudio[ext=m4a]", "720") == "bestaudio[ext=m4a]"

    def test_existing_height_filter_is_not_duplicated(self):
        assert _limit_height("best[height<=480]", "1080") == "best[height<=480]"

    def test_bare_selector_gets_a_filter(self):
        assert _limit_height("best", "360") == "best[height<=360]"


class TestFormatString:
    def test_entries_become_a_fallback_chain(self, make_config):
        config = make_config({"formats": ["a", "b"], "fallback_to_best": False})

        assert config.get_format_string() == "a/b"

    def test_permissive_fallback_is_appended_by_default(self, make_config):
        config = make_config({"formats": ["bestvideo[vcodec^=avc1]+bestaudio"]})

        assert config.get_format_string().endswith("/best")

    def test_fallback_is_not_duplicated(self, make_config):
        config = make_config({"formats": ["bestvideo+bestaudio", "best"]})

        assert config.get_format_string() == "bestvideo+bestaudio/best"

    def test_resolution_limits_every_alternative(self, make_config):
        config = make_config({"formats": ["bestvideo[ext=mp4]+bestaudio[ext=m4a]", "best[ext=mp4]"]})
        chain = config.get_format_string("1080")

        # Regression guard: a filter appended once to the end of the chain would
        # only bind to the final alternative, silently ignoring --resolution.
        for alternative in chain.split("/"):
            assert "[height<=1080]" in alternative
        assert "bestaudio[ext=m4a][height<=1080]" not in chain

    def test_empty_format_list_still_yields_a_selector(self, make_config):
        config = make_config({"formats": []})

        assert config.get_format_string() == "bestvideo+bestaudio/best"


class TestSettingsResolution:
    def test_packaged_defaults_load_without_a_user_file(self):
        config = DownloadConfig()

        assert config.settings_path is None
        assert config.get("merge_output_format") == "mp4"

    def test_user_file_overrides_only_the_keys_it_sets(self, make_config):
        config = make_config({"merge_output_format": "mkv"})

        assert config.get("merge_output_format") == "mkv"
        assert config.get("restrict_filenames") is True

    def test_env_var_is_used_when_no_path_is_given(self, tmp_path, monkeypatch):
        path = tmp_path / "env-settings.json"
        path.write_text('{"output_dir": "from-env"}', encoding="utf-8")
        monkeypatch.setenv("JBDOWNLOAD_SETTINGS", str(path))

        assert DownloadConfig().output_dir.name == "from-env"

    def test_absolute_output_dir_is_not_prefixed_with_the_media_root(self, make_config):
        config = make_config({"output_dir": "/srv/videos"})

        assert str(config.output_dir) == "/srv/videos"

    def test_malformed_settings_fall_back_to_defaults(self, tmp_path, caplog):
        path = tmp_path / "broken.json"
        path.write_text("{not json", encoding="utf-8")

        config = DownloadConfig(path)

        assert config.get("merge_output_format") == "mp4"

    def test_disabled_logger_silences_output(self, make_config):
        assert make_config({"logger": {"enabled": False}}).log_level == "CRITICAL"


class TestBuildYdlOpts:
    def test_settings_are_translated_to_yt_dlp_names(self, make_config):
        opts = make_config().build_ydl_opts()

        assert opts["restrictfilenames"] is True
        assert opts["writesubtitles"] is True
        assert opts["subtitleslangs"] == ["en"]
        assert opts["merge_output_format"] == "mp4"
        assert opts["overwrites"] is False
        assert opts["sleep_interval"] == 1
        assert opts["max_sleep_interval"] == 3
        assert opts["concurrent_fragment_downloads"] == 4

    def test_embed_flags_become_postprocessors(self, make_config):
        keys = [pp["key"] for pp in make_config().build_ydl_opts()["postprocessors"]]

        assert "FFmpegEmbedSubtitle" in keys
        assert "FFmpegMetadata" in keys

    def test_remux_video_becomes_a_remuxer_postprocessor(self, make_config):
        pps = make_config({"remux_video": "mp4"}).build_ydl_opts()["postprocessors"]

        assert pps[0] == {"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}

    def test_remux_runs_before_anything_is_embedded(self, make_config):
        pps = make_config({"remux_video": "mkv"}).build_ydl_opts()["postprocessors"]
        keys = [pp["key"] for pp in pps]

        assert keys.index("FFmpegVideoRemuxer") < keys.index("FFmpegEmbedSubtitle")
        assert keys.index("FFmpegVideoRemuxer") < keys.index("FFmpegMetadata")

    def test_empty_remux_video_is_omitted(self, make_config):
        keys = [pp["key"] for pp in make_config().build_ydl_opts()["postprocessors"]]

        assert "FFmpegVideoRemuxer" not in keys

    def test_js_runtimes_are_enabled_by_default(self, make_config):
        # YouTube extraction without a JS runtime is deprecated and hides formats.
        assert make_config().build_ydl_opts()["js_runtimes"] == {
            "deno": {"path": None},
            "node": {"path": None},
        }

    def test_js_runtime_accepts_an_explicit_path(self, make_config):
        opts = make_config({"js_runtimes": ["node:/usr/bin/node"]}).build_ydl_opts()

        assert opts["js_runtimes"] == {"node": {"path": "/usr/bin/node"}}

    def test_js_runtimes_can_be_disabled(self, make_config):
        assert "js_runtimes" not in make_config({"js_runtimes": []}).build_ydl_opts()

    def test_empty_proxy_is_omitted(self, make_config):
        assert "proxy" not in make_config().build_ydl_opts()

    def test_configured_proxy_is_passed_through(self, make_config):
        opts = make_config({"proxy": "socks5://127.0.0.1:1080"}).build_ydl_opts()

        assert opts["proxy"] == "socks5://127.0.0.1:1080"

    def test_output_path_overrides_the_configured_directory(self, make_config, tmp_path):
        destination = tmp_path / "out"

        opts = make_config().build_ydl_opts(output_path=str(destination))

        assert opts["outtmpl"] == f"{destination}/%(title)s.%(ext)s"

    def test_noplaylist_defaults_to_the_settings_file(self, make_config):
        config = make_config({"playlist": {"noplaylist": True}})

        assert config.build_ydl_opts()["noplaylist"] is True
        assert config.build_ydl_opts(noplaylist=False)["noplaylist"] is False

    def test_extra_options_win(self, make_config):
        opts = make_config().build_ydl_opts(extra={"merge_output_format": "mkv"})

        assert opts["merge_output_format"] == "mkv"


class TestCookieOptions:
    def test_existing_cookie_file_is_passed_as_cookiefile(self, make_config, tmp_path):
        jar = tmp_path / "cookies.txt"
        jar.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

        opts = make_config({"cookie_file": str(jar)}).build_ydl_opts()

        assert opts["cookiefile"] == str(jar)

    def test_missing_cookie_file_is_dropped_silently(self, make_config):
        opts = make_config({"cookie_file": "/nope/cookies.txt"}).build_ydl_opts()

        assert "cookiefile" not in opts

    def test_browser_cookies_use_the_four_element_tuple_yt_dlp_expects(self, make_config):
        opts = make_config({"use_browser_cookies": True, "cookie_browser": "firefox"}).build_ydl_opts()

        assert opts["cookiesfrombrowser"] == ("firefox", None, None, None)

    def test_browser_spec_accepts_a_profile_path(self):
        assert _parse_browser_spec("firefox:/srv/profiles/ab.default") == (
            "firefox",
            "/srv/profiles/ab.default",
            None,
            None,
        )

    def test_bare_browser_name_has_no_profile(self, make_config):
        opts = make_config({"use_browser_cookies": True, "cookie_browser": "Firefox"}).build_ydl_opts()

        assert opts["cookiesfrombrowser"] == ("firefox", None, None, None)

    def test_missing_cookie_file_does_not_warn(self, make_config, caplog):
        with caplog.at_level("WARNING", logger="jb-download"):
            make_config({"cookie_file": "/nope/cookies.txt"}).build_ydl_opts()

        assert caplog.text == ""

    def test_sidecar_files_are_off_by_default(self, make_config):
        opts = make_config().build_ydl_opts()

        assert opts["writedescription"] is False
        assert opts["writeinfojson"] is False
        assert opts["writethumbnail"] is False

    def test_firefox_profile_without_a_cookie_db_is_skipped(self, make_config, tmp_path):
        # Must degrade to "no cookies" rather than failing every download.
        empty = tmp_path / "ffprofile"
        empty.mkdir()

        opts = make_config(
            {"use_browser_cookies": True, "cookie_browser": f"firefox:{empty}"}
        ).build_ydl_opts()

        assert "cookiesfrombrowser" not in opts

    def test_firefox_profile_with_a_cookie_db_is_used(self, make_config, tmp_path):
        profile = tmp_path / "ffprofile"
        profile.mkdir()
        (profile / "cookies.sqlite").write_bytes(b"SQLite format 3\x00")

        opts = make_config(
            {"use_browser_cookies": True, "cookie_browser": f"firefox:{profile}"}
        ).build_ydl_opts()

        assert opts["cookiesfrombrowser"] == ("firefox", str(profile), None, None)

    def test_unpopulated_firefox_profile_falls_back_to_the_cookie_file(self, make_config, tmp_path):
        empty = tmp_path / "ffprofile"
        empty.mkdir()
        jar = tmp_path / "cookies.txt"
        jar.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

        opts = make_config(
            {
                "use_browser_cookies": True,
                "cookie_browser": f"firefox:{empty}",
                "cookie_file": str(jar),
            }
        ).build_ydl_opts()

        assert opts["cookiefile"] == str(jar)

    def test_cli_cookie_file_overrides_the_configured_one(self, make_config, tmp_path):
        jar = tmp_path / "override.txt"
        jar.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

        opts = make_config({"cookie_file": "/nope.txt"}).build_ydl_opts(cookie_file=str(jar))

        assert opts["cookiefile"] == str(jar)

    @pytest.mark.parametrize("legacy_key", ["cookies", "cookiesfrom_browser"])
    def test_legacy_misspelled_keys_are_never_emitted(self, make_config, tmp_path, legacy_key):
        # yt-dlp silently ignores unknown option names, so these spellings made
        # cookie support a no-op for every release that used them.
        jar = tmp_path / "cookies.txt"
        jar.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
        file_opts = make_config({"cookie_file": str(jar)}).build_ydl_opts()
        browser_opts = make_config({"use_browser_cookies": True}).build_ydl_opts()

        assert legacy_key not in file_opts
        assert legacy_key not in browser_opts


def test_every_emitted_option_is_a_real_yt_dlp_parameter(make_config, tmp_path):
    """Guard against option names yt-dlp would silently discard."""
    documented = set(re.findall(r"^\s{4}(\w+)[:,]", YoutubeDL.__doc__, re.M))
    jar = tmp_path / "cookies.txt"
    jar.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

    opts = make_config({"cookie_file": str(jar), "proxy": "http://p:1"}).build_ydl_opts(
        resolution="720",
        playlist_items="1-5",
        extra={"progress_hooks": [], "listformats": True},
    )

    unknown = sorted(key for key in opts if key not in documented)
    assert unknown == [], f"yt-dlp does not recognise these options: {unknown}"
