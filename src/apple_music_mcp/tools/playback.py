from __future__ import annotations

from typing import Any

from apple_music_mcp import applescript as asc


def tool_playback_status() -> dict[str, Any]:
    """Get the current playback status, active track, volume, and player state."""
    return asc.get_playback_state()


def tool_playback_control(
    action: str,
    track: str | None = None,
    volume: int | None = None,
    shuffle: bool | None = None,
    repeat: str | None = None,
    rating_stars: int | None = None,
) -> dict[str, Any]:
    """Control local Apple Music playback and ratings.

    Args:
        action: 'play', 'pause', 'toggle', 'next', 'previous', 'set_volume', 'set_shuffle', 'set_repeat', 'rate', 'love', 'dislike'
        track: Track name or search query (for action='play')
        volume: Volume level 0-100 (for action='set_volume')
        shuffle: Boolean enabled (for action='set_shuffle')
        repeat: 'off', 'one', 'all' (for action='set_repeat')
        rating_stars: Star rating 1-5 (for action='rate')
    """
    act = action.lower().strip()
    if act == "play":
        s, msg = asc.play_track(track)
    elif act == "pause":
        s, msg = asc.pause_playback()
    elif act in ("toggle", "playpause"):
        s, msg = asc.play_pause_toggle()
    elif act in ("next", "skip"):
        s, msg = asc.next_track()
    elif act in ("previous", "prev", "back"):
        s, msg = asc.previous_track()
    elif act == "set_volume":
        if volume is None:
            return {"success": False, "error": "volume (0-100) is required"}
        s, msg = asc.set_volume(volume)
    elif act == "set_shuffle":
        if shuffle is None:
            return {"success": False, "error": "shuffle (true/false) is required"}
        s, msg = asc.set_shuffle(shuffle)
    elif act == "set_repeat":
        if not repeat:
            return {"success": False, "error": "repeat ('off', 'one', 'all') is required"}
        s, msg = asc.set_repeat(repeat)
    elif act == "rate":
        if rating_stars is None:
            return {"success": False, "error": "rating_stars (1-5) is required"}
        s, msg = asc.rate_current_track(rating_stars)
    elif act in ("love", "favorite"):
        s, msg = asc.rate_current_track(5)
    elif act == "dislike":
        s, msg = asc.rate_current_track(1)
    else:
        return {"success": False, "error": f"Unknown playback action: {action}"}

    return {
        "success": s,
        "message": msg or f"Executed {action}",
        "state": asc.get_playback_state(),
    }


def tool_airplay_devices() -> dict[str, Any]:
    """List available AirPlay output devices (HomePods, Apple TVs, Bluetooth speakers)."""
    s, devs = asc.get_airplay_devices()
    return {"success": s, "devices": devs}
