from __future__ import annotations

import re
from typing import Any

from apple_music_mcp import applescript as asc
from apple_music_mcp.api import client


def _clean_title(name: str) -> str:
    if not name:
        return ""
    s = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    s = re.sub(r"[^a-zA-Z0-9\s]", "", s)
    return " ".join(s.lower().split())


async def tool_playlist_get_tracks(
    playlist_id_or_name: str,
    limit: int = 500,
    filter_audio_only: bool = True,
) -> dict[str, Any]:
    """Retrieve all songs in a playlist with duration, artist, catalog ID, and media type."""
    # If it starts with 'p.', query via API
    if playlist_id_or_name.startswith("p."):
        try:
            tracks = await client.get_playlist_tracks(
                playlist_id_or_name,
                limit=limit,
                filter_audio_only=filter_audio_only,
            )
            return {
                "playlist_id": playlist_id_or_name,
                "total_tracks": len(tracks),
                "tracks": tracks,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Otherwise if macOS native, query via fast JXA engine
    if asc.is_macos():
        s, tracks = asc.get_playlist_tracks_fast(playlist_id_or_name, limit=limit)
        if s:
            return {
                "playlist_name": playlist_id_or_name,
                "total_tracks": len(tracks),
                "tracks": tracks,
            }

    # Resolve by name via API
    try:
        pls = await client.get_user_playlists()
        target = next((p for p in pls if p["name"].lower() == playlist_id_or_name.lower()), None)
        if target:
            tracks = await client.get_playlist_tracks(
                target["id"],
                limit=limit,
                filter_audio_only=filter_audio_only,
            )
            return {
                "playlist_id": target["id"],
                "playlist_name": target["name"],
                "total_tracks": len(tracks),
                "tracks": tracks,
            }
        return {"success": False, "error": f"Playlist '{playlist_id_or_name}' not found."}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_playlist_add_tracks(
    playlist_id: str,
    catalog_ids: list[str],
    allow_duplicates: bool = False,
) -> dict[str, Any]:
    """Add multiple songs to a playlist in parallel async batches with deduplication."""
    if not catalog_ids:
        return {"success": False, "error": "catalog_ids list cannot be empty"}

    # If deduplication requested, fetch existing tracks first
    to_add = catalog_ids
    if not allow_duplicates:
        try:
            existing = await client.get_playlist_tracks(playlist_id, limit=2000)
            existing_cids = set(t.get("catalog_id") for t in existing if t.get("catalog_id"))
            existing_names = set(_clean_title(t.get("name", "")) for t in existing if t.get("name"))

            filtered = []
            for cid in catalog_ids:
                if cid not in existing_cids:
                    filtered.append(cid)
            to_add = filtered
        except Exception:
            pass

    if not to_add:
        return {
            "success": True,
            "added_count": 0,
            "message": "All requested tracks are already present in playlist (no duplicates added).",
        }

    added, failed = await client.add_tracks_bulk(playlist_id, to_add)
    return {
        "success": added > 0,
        "added_count": added,
        "requested_count": len(catalog_ids),
        "skipped_duplicates": len(catalog_ids) - len(to_add),
        "failed_ids": failed,
    }


async def tool_playlist_remove_tracks(
    playlist_id: str,
    relationship_ids: list[str],
    is_video: bool = False,
) -> dict[str, Any]:
    """Remove specific track relationship IDs from a playlist."""
    if not relationship_ids:
        return {"success": False, "error": "relationship_ids list cannot be empty"}

    removed = await client.remove_tracks_bulk(playlist_id, relationship_ids, is_video=is_video)
    return {
        "success": removed > 0,
        "removed_count": removed,
        "requested_count": len(relationship_ids),
    }


async def tool_playlist_create(
    name: str,
    description: str = "",
) -> dict[str, Any]:
    """Create a new user playlist with custom metadata and description."""
    try:
        res = await client.create_playlist(name, description)
        if asc.is_macos() and description:
            asc.set_playlist_description(name, description)
        return {
            "success": True,
            "playlist_id": res.get("id"),
            "name": name,
            "description": description,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_playlist_delete(
    playlist_id_or_name: str,
) -> dict[str, Any]:
    """Delete a user playlist safely from cloud library and native macOS."""
    success = False
    msg = ""

    if playlist_id_or_name.startswith("p."):
        success = await client.delete_playlist(playlist_id_or_name)
        msg = f"Deleted API playlist {playlist_id_or_name}"
    elif asc.is_macos():
        s, m = asc.delete_playlist_native(playlist_id_or_name)
        success = s
        msg = m
    else:
        # Resolve by name
        pls = await client.get_user_playlists()
        target = next((p for p in pls if p["name"].lower() == playlist_id_or_name.lower()), None)
        if target:
            success = await client.delete_playlist(target["id"])
            msg = f"Deleted playlist {target['name']}"

    return {"success": success, "message": msg}


def tool_playlist_set_description(
    playlist_name: str,
    description: str,
) -> dict[str, Any]:
    """Update playlist description in macOS Music.app."""
    s, msg = asc.set_playlist_description(playlist_name, description)
    return {"success": s, "message": msg}
