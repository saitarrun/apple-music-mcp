import pytest
from apple_music_mcp import config
from apple_music_mcp.cache import cache
from apple_music_mcp.tools import playback, library, playlists, catalog, curation, recommendations, discovery


def test_config_load():
    cfg = config.Config.load()
    assert cfg.preferences.storefront in ("in", "us")
    assert cfg.preferences.pure_audio_only is True


def test_cache_operations():
    cache.set("test_namespace", "test_key", {"status": "ok"}, ttl=10)
    res = cache.get("test_namespace", "test_key")
    assert res == {"status": "ok"}


def test_system_status():
    st = library.tool_system_status()
    assert "native_macos" in st
    assert "storefront" in st


def test_clean_title_helper():
    from apple_music_mcp.tools.playlists import _clean_title
    assert _clean_title("Song Name (From \"Movie\") [Remastered]") == "song name"


def test_airplay_devices_structure():
    res = playback.tool_airplay_devices()
    assert "devices" in res
