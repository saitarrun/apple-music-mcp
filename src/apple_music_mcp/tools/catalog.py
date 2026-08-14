from __future__ import annotations

from typing import Any

from apple_music_mcp.api import client
from apple_music_mcp.config import config


async def tool_catalog_search(
    query: str,
    types: str = "songs",
    limit: int = 25,
    storefront: str | None = None,
) -> dict[str, Any]:
    """Search Apple Music global catalog for songs, albums, artists, or curated playlists."""
    try:
        results = await client.search_catalog(
            query=query,
            types=types,
            limit=limit,
            storefront=storefront,
        )
        return {
            "query": query,
            "storefront": storefront or config.preferences.storefront,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_catalog_artist_top_songs(
    artist_name_or_id: str,
    limit: int = 20,
    storefront: str | None = None,
) -> dict[str, Any]:
    """Fetch top rated and most popular tracks for an artist."""
    sf = storefront or config.preferences.storefront
    art_id = artist_name_or_id

    # If artist name given instead of numeric ID, search first
    if not artist_name_or_id.isdigit():
        try:
            res = await client.search_catalog(query=artist_name_or_id, types="artists", limit=1, storefront=sf)
            if not res:
                return {"success": False, "error": f"Artist '{artist_name_or_id}' not found in catalog."}
            art_id = res[0]["id"]
        except Exception as e:
            return {"success": False, "error": str(e)}

    try:
        songs = await client.get_artist_top_songs(artist_id=art_id, limit=limit, storefront=sf)
        return {
            "artist_id": art_id,
            "count": len(songs),
            "top_songs": songs,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_catalog_playlist_tracks(
    playlist_id: str,
    storefront: str | None = None,
) -> dict[str, Any]:
    """Get all track items inside an official Apple Music curated playlist (e.g. pl.xxx)."""
    try:
        tracks = await client.get_catalog_playlist_tracks(
            playlist_id=playlist_id,
            storefront=storefront,
        )
        return {
            "playlist_id": playlist_id,
            "count": len(tracks),
            "tracks": tracks,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_catalog_resolve_song(
    title: str,
    artist: str = "",
    storefront: str | None = None,
) -> dict[str, Any]:
    """Pin the exact official studio audio song catalog ID for a title and artist."""
    q = f"{title} {artist}".strip()
    try:
        res = await client.search_catalog(
            query=q,
            types="songs",
            limit=5,
            storefront=storefront,
        )
        if not res:
            return {"found": False, "message": "Song not found in catalog"}

        top = res[0]
        return {
            "found": True,
            "catalog_id": top["id"],
            "name": top["name"],
            "artist": top["artist"],
            "album": top.get("album", ""),
        }
    except Exception as e:
        return {"found": False, "error": str(e)}
