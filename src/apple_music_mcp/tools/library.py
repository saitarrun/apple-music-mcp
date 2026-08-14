from __future__ import annotations

from typing import Any

from apple_music_mcp import applescript as asc
from apple_music_mcp.api import client
from apple_music_mcp.auth import get_auth_status


async def tool_library_playlists(use_api: bool = False) -> dict[str, Any]:
    """List all user playlists with accurate track counts, descriptions, and IDs."""
    if not use_api and asc.is_macos():
        s, pls = asc.list_user_playlists()
        if s:
            return {
                "source": "native_macos",
                "count": len(pls),
                "playlists": pls,
            }

    # Fallback / API query
    try:
        pls = await client.get_user_playlists()
        return {
            "source": "apple_music_api",
            "count": len(pls),
            "playlists": pls,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_library_sync() -> dict[str, Any]:
    """Force Apple Music macOS cloud library update and refresh synchronization."""
    if asc.is_macos():
        s, msg = asc.update_cloud_library()
        return {"success": s, "message": msg or "Cloud library sync initiated"}
    return {"success": True, "message": "API cloud updates sync automatically on non-macOS"}


def tool_system_status() -> dict[str, Any]:
    """Check Apple Music MCP configuration, native AppleScript bridge, and API auth status."""
    return get_auth_status()
