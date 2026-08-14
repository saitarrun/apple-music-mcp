from __future__ import annotations

from typing import Any

from apple_music_mcp.api import client


async def tool_get_recently_played(limit: int = 25) -> dict[str, Any]:
    """Fetch user's recently played track listening history."""
    try:
        tracks = await client.get_recently_played_tracks(limit=limit)
        return {
            "count": len(tracks),
            "tracks": tracks,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_get_heavy_rotation(limit: int = 15) -> dict[str, Any]:
    """Fetch user's most frequently played and heavy rotation albums/playlists."""
    try:
        items = await client.get_heavy_rotation(limit=limit)
        return {
            "count": len(items),
            "items": items,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
