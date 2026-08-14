from __future__ import annotations

import re
from typing import Any

from apple_music_mcp.api import client
from apple_music_mcp.config import config


def _clean(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    s = re.sub(r"[^a-zA-Z0-9\s]", "", s)
    return " ".join(s.lower().split())


async def tool_curation_clean_videos(
    playlist_id: str,
    replace_with_audio: bool = True,
) -> dict[str, Any]:
    """Scan playlist for any video tracks, delete video entities, and swap with official audio songs."""
    tracks = await client.get_playlist_tracks(playlist_id, limit=2000, filter_audio_only=False)
    video_tracks = [t for t in tracks if "video" in t.get("type", "")]

    if not video_tracks:
        return {"success": True, "message": "Playlist contains 0 video tracks (100% pure audio)."}

    # Remove video tracks
    rel_ids = [t["relationship_id"] for t in video_tracks]
    removed = await client.remove_tracks_bulk(playlist_id, rel_ids, is_video=True)

    added_audio = 0
    if replace_with_audio:
        audio_cids = []
        for t in video_tracks:
            q = f"{t['name']} {t['artist']}".strip()
            try:
                res = await client.search_catalog(query=q, types="songs", limit=3)
                if res:
                    audio_cids.append(res[0]["id"])
            except Exception:
                pass

        if audio_cids:
            added_audio, _ = await client.add_tracks_bulk(playlist_id, audio_cids)

    return {
        "success": True,
        "videos_detected": len(video_tracks),
        "videos_removed": removed,
        "audio_replacements_added": added_audio,
    }


async def tool_curation_deduplicate(
    playlist_id: str,
) -> dict[str, Any]:
    """Scan playlist, identify all duplicate editions/versions, and keep only the single canonical track."""
    tracks = await client.get_playlist_tracks(playlist_id, limit=2000, filter_audio_only=False)

    seen_titles: dict[str, dict[str, Any]] = {}
    duplicate_rel_ids: list[str] = []
    duplicate_names: list[str] = []

    for t in tracks:
        ctitle = _clean(t["name"])
        if ctitle in seen_titles:
            duplicate_rel_ids.append(t["relationship_id"])
            duplicate_names.append(t["name"])
        else:
            seen_titles[ctitle] = t

    if not duplicate_rel_ids:
        return {"success": True, "message": "No duplicates found. Playlist is fully deduplicated."}

    removed = await client.remove_tracks_bulk(playlist_id, duplicate_rel_ids)
    return {
        "success": True,
        "duplicates_removed": removed,
        "duplicate_tracks": duplicate_names,
    }


async def tool_curation_merge_playlists(
    source_playlist_id: str,
    destination_playlist_id: str,
    delete_source_after_merge: bool = False,
) -> dict[str, Any]:
    """Merge all tracks from source playlist into destination playlist with zero duplicates."""
    src_tracks = await client.get_playlist_tracks(source_playlist_id, limit=2000)
    dest_tracks = await client.get_playlist_tracks(destination_playlist_id, limit=2000)

    dest_cids = set(t.get("catalog_id") for t in dest_tracks if t.get("catalog_id"))
    dest_titles = set(_clean(t.get("name", "")) for t in dest_tracks if t.get("name"))

    to_add_cids = []
    skipped = 0

    for t in src_tracks:
        cid = t.get("catalog_id")
        ctitle = _clean(t.get("name", ""))
        if cid and cid in dest_cids:
            skipped += 1
        elif ctitle in dest_titles:
            skipped += 1
        else:
            if cid:
                to_add_cids.append(cid)
                dest_cids.add(cid)

    added, failed = await client.add_tracks_bulk(destination_playlist_id, to_add_cids)

    deleted_src = False
    if delete_source_after_merge and added == len(to_add_cids):
        deleted_src = await client.delete_playlist(source_playlist_id)

    return {
        "success": True,
        "source_tracks_count": len(src_tracks),
        "tracks_added": added,
        "duplicates_skipped": skipped,
        "source_deleted": deleted_src,
    }
