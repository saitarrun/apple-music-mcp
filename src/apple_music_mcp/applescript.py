from __future__ import annotations

import json
import platform
import subprocess
from typing import Any


def is_macos() -> bool:
    return platform.system() == "Darwin"


def run_applescript(script: str, timeout: float = 15.0) -> tuple[bool, str]:
    """Execute an AppleScript string via osascript with timeout protection."""
    if not is_macos():
        return False, "AppleScript is only supported on macOS"

    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        err = proc.stderr.strip() or proc.stdout.strip()
        return False, err
    except subprocess.TimeoutExpired:
        return False, f"AppleScript timed out after {timeout} seconds"
    except Exception as e:
        return False, str(e)


def run_jxa(script: str, timeout: float = 15.0) -> tuple[bool, str]:
    """Execute a JavaScript for Automation (JXA) script via osascript -l JavaScript."""
    if not is_macos():
        return False, "JXA is only supported on macOS"

    try:
        proc = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        return False, proc.stderr.strip() or proc.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, f"JXA timed out after {timeout} seconds"
    except Exception as e:
        return False, str(e)


# ==================== PLAYBACK CONTROLS & RATINGS ====================


def get_playback_state() -> dict[str, Any]:
    """Get rich real-time playback state, active track, and rating."""
    if not is_macos():
        return {"running": False, "state": "unsupported_os"}

    script = """
    tell application "System Events"
        set isRunning to (count of (every process whose name is "Music")) > 0
    end tell
    if not isRunning then
        return "NOT_RUNNING"
    end if

    tell application "Music"
        set pState to player state as string
        if pState is "stopped" then
            return "STOPPED"
        end if
        
        try
            set curTrack to current track
            set tName to name of curTrack
            set tArtist to artist of curTrack
            set tAlbum to album of curTrack
            set tDuration to duration of curTrack
            set tPosition to player position
            set tVolume to sound volume
            set tShuffle to shuffle enabled
            set tRepeat to song repeat as string
            set tRating to rating of curTrack
            
            return tName & "|||" & tArtist & "|||" & tAlbum & "|||" & tDuration & "|||" & tPosition & "|||" & tVolume & "|||" & tShuffle & "|||" & tRepeat & "|||" & pState & "|||" & tRating
        on error
            return "PLAYING_UNKNOWN"
        end try
    end tell
    """
    s, out = run_applescript(script)
    if not s or out == "NOT_RUNNING":
        return {"running": False, "state": "not_running"}
    if out == "STOPPED":
        return {"running": True, "state": "stopped"}

    parts = out.split("|||")
    if len(parts) >= 9:
        try:
            dur = float(parts[3])
            pos = float(parts[4])
            vol = int(parts[5])
            rating = int(parts[9]) if len(parts) > 9 and parts[9].isdigit() else 0
        except ValueError:
            dur, pos, vol, rating = 0.0, 0.0, 50, 0

        return {
            "running": True,
            "state": parts[8],
            "track": {
                "name": parts[0],
                "artist": parts[1],
                "album": parts[2],
                "duration_seconds": dur,
                "position_seconds": pos,
                "position_formatted": f"{int(pos)//60}:{int(pos)%60:02d}",
                "duration_formatted": f"{int(dur)//60}:{int(dur)%60:02d}",
                "rating_stars": rating // 20,
            },
            "volume": vol,
            "shuffle": parts[6].lower() == "true",
            "repeat": parts[7],
        }

    return {"running": True, "state": "active"}


def play_track(track_name: str | None = None) -> tuple[bool, str]:
    if track_name:
        safe = json.dumps(track_name)
        script = f"""
        tell application "Music"
            set matchTracks to (every track of library playlist 1 whose name contains {safe})
            if (count of matchTracks) > 0 then
                play (item 1 of matchTracks)
                return "Playing track: " & name of (item 1 of matchTracks)
            else
                return "Track not found in local library"
            end if
        end tell
        """
    else:
        script = 'tell application "Music" to play'
    return run_applescript(script)


def pause_playback() -> tuple[bool, str]:
    return run_applescript('tell application "Music" to pause')


def play_pause_toggle() -> tuple[bool, str]:
    return run_applescript('tell application "Music" to playpause')


def next_track() -> tuple[bool, str]:
    return run_applescript('tell application "Music" to next track')


def previous_track() -> tuple[bool, str]:
    return run_applescript('tell application "Music" to previous track')


def set_volume(level: int) -> tuple[bool, str]:
    clamped = max(0, min(100, level))
    return run_applescript(f'tell application "Music" to set sound volume to {clamped}')


def set_shuffle(enabled: bool) -> tuple[bool, str]:
    val = "true" if enabled else "false"
    return run_applescript(f'tell application "Music" to set shuffle enabled to {val}')


def set_repeat(mode: str) -> tuple[bool, str]:
    val = "all"
    if mode.lower() in ("off", "none"):
        val = "off"
    elif mode.lower() in ("one", "track"):
        val = "one"
    return run_applescript(f'tell application "Music" to set song repeat to {val}')


def rate_current_track(rating_stars_or_score: int) -> tuple[bool, str]:
    """Rate active track (1-5 stars or 0-100 rating score)."""
    score = rating_stars_or_score * 20 if rating_stars_or_score <= 5 else rating_stars_or_score
    clamped = max(0, min(100, score))
    script = f"""
    tell application "Music"
        try
            set rating of current track to {clamped}
            return "Rated track " & (name of current track) & " as " & {clamped // 20} & " stars"
        on error err
            return "Error: " & err
        end try
    end tell
    """
    return run_applescript(script)


def get_airplay_devices() -> tuple[bool, list[dict[str, Any]]]:
    """List available AirPlay audio outputs."""
    script = """
    tell application "Music"
        set devList to AirPlay devices
        set res to ""
        repeat with d in devList
            set dName to name of d
            set dActive to selected of d
            set dKind to kind of d as string
            set res to res & dName & "|||" & dActive & "|||" & dKind & linefeed
        end repeat
        return res
    end tell
    """
    s, out = run_applescript(script)
    if not s:
        return False, []

    devices = []
    for line in out.splitlines():
        if "|||" in line:
            parts = line.split("|||")
            devices.append({
                "name": parts[0],
                "active": parts[1].lower() == "true",
                "kind": parts[2] if len(parts) > 2 else "speaker",
            })
    return True, devices


# ==================== HIGH-SPEED BULK PLAYLIST QUERIES ====================


def list_user_playlists() -> tuple[bool, list[dict[str, Any]]]:
    """Fast bulk retrieval of all user playlists with track counts and descriptions."""
    if not is_macos():
        return False, []

    script = """
    tell application "Music"
        set pList to user playlists
        set res to ""
        repeat with p in pList
            set pName to name of p
            set pId to persistent ID of p
            set pCount to count of tracks of p
            set pSmart to smart of p
            set pDesc to ""
            try
                set pDesc to description of p
            end try
            if pDesc is missing value then set pDesc to ""
            set res to res & pName & "|||" & pId & "|||" & pCount & "|||" & pSmart & "|||" & pDesc & linefeed
        end repeat
        return res
    end tell
    """
    s, out = run_applescript(script, timeout=10.0)
    if not s:
        return False, []

    playlists = []
    for line in out.splitlines():
        if "|||" in line:
            parts = line.split("|||")
            if len(parts) >= 5:
                playlists.append({
                    "name": parts[0],
                    "id": parts[1],
                    "track_count": int(parts[2]) if parts[2].isdigit() else 0,
                    "is_smart": parts[3].lower() == "true",
                    "description": parts[4],
                })
    return True, playlists


def get_playlist_tracks_fast(playlist_name: str, limit: int = 1000) -> tuple[bool, list[dict[str, Any]]]:
    """Ultra-fast JXA bulk extraction avoiding O(N) AppleScript timeouts."""
    if not is_macos():
        return False, []

    safe = json.dumps(playlist_name)
    jxa = f"""
    (() => {{
        const app = Application('Music');
        const pls = app.userPlaylists.whose({{ name: {safe} }});
        if (pls.length === 0) return JSON.stringify({{ error: 'Playlist not found' }});
        
        const pl = pls[0];
        const tracks = pl.tracks();
        const max = Math.min(tracks.length, {limit});
        const res = [];
        
        for (let i = 0; i < max; i++) {{
            const t = tracks[i];
            res.push({{
                name: t.name(),
                artist: t.artist() || '',
                album: t.album() || '',
                duration: t.time() || '',
                id: t.persistentID() || '',
                year: t.year() || 0,
                genre: t.genre() || '',
                media_kind: t.class() || 'track'
            }});
        }}
        return JSON.stringify({{ count: tracks.length, tracks: res }});
    }})()
    """
    s, out = run_jxa(jxa, timeout=20.0)
    if not s:
        return False, []

    try:
        data = json.loads(out)
        if "error" in data:
            return False, []
        return True, data.get("tracks", [])
    except Exception:
        return False, []


def set_playlist_description(playlist_name: str, description: str) -> tuple[bool, str]:
    safe_name = json.dumps(playlist_name)
    safe_desc = json.dumps(description)
    script = f"""
    tell application "Music"
        set matching to (every user playlist whose name is {safe_name})
        if (count of matching) > 0 then
            set description of (item 1 of matching) to {safe_desc}
            return "Updated description"
        else
            return "Playlist not found"
        end if
    end tell
    """
    return run_applescript(script)


def delete_playlist_native(playlist_name: str) -> tuple[bool, str]:
    safe_name = json.dumps(playlist_name)
    script = f"""
    tell application "Music"
        set matching to (every user playlist whose name is {safe_name})
        if (count of matching) > 0 then
            delete (item 1 of matching)
            return "Deleted playlist: " & {safe_name}
        else
            return "Playlist not found"
        end if
    end tell
    """
    return run_applescript(script)


def update_cloud_library() -> tuple[bool, str]:
    script = 'tell application "Music" to update cloud library'
    return run_applescript(script, timeout=10.0)
