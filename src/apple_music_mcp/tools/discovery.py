from __future__ import annotations

from typing import Any

from apple_music_mcp.api import client
from apple_music_mcp.charts import fetch_cross_platform_chart_tracks
from apple_music_mcp.tools.playlists import tool_playlist_add_tracks


async def tool_get_cross_platform_charts(
    source: str = "shazam",
    chart_type: str = "top_hits",
    language_or_genre: str = "english",
    limit: int = 30,
    storefront: str | None = None,
) -> dict[str, Any]:
    """Fetch popular, top viewed, and most streamed songs from Shazam, YouTube, Spotify, or Apple Music charts.

    Args:
        source: 'shazam', 'spotify', 'youtube', 'apple_music'
        chart_type: 'top_hits', 'all_time', 'billions', 'viral'
        language_or_genre: 'english', 'hindi', 'telugu', 'tamil', 'pop', 'rock', 'hip_hop'
        limit: Max tracks to fetch (default 30)
        storefront: Two-letter country code ('in', 'us', etc.)
    """
    try:
        tracks = await fetch_cross_platform_chart_tracks(
            source=source,
            chart_type=chart_type,
            language_or_genre=language_or_genre,
            limit=limit,
            storefront=storefront,
        )
        return {
            "source": source,
            "chart_type": chart_type,
            "language_or_genre": language_or_genre,
            "count": len(tracks),
            "tracks": tracks[:limit],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_populate_from_charts(
    playlist_id: str,
    source: str = "shazam",
    chart_type: str = "top_hits",
    language_or_genre: str = "english",
    limit: int = 30,
    allow_duplicates: bool = False,
) -> dict[str, Any]:
    """Fetch and populate songs directly from Shazam, Spotify, YouTube, or Apple Music charts into a playlist with deduplication."""
    chart_res = await tool_get_cross_platform_charts(
        source=source,
        chart_type=chart_type,
        language_or_genre=language_or_genre,
        limit=limit,
    )
    if "error" in chart_res:
        return chart_res

    tracks = chart_res.get("tracks", [])
    cids = [t["id"] for t in tracks if t.get("id")]

    if not cids:
        return {"success": False, "error": "No chart catalog IDs resolved to populate."}

    add_res = await tool_playlist_add_tracks(
        playlist_id=playlist_id,
        catalog_ids=cids,
        allow_duplicates=allow_duplicates,
    )
    return {
        "success": add_res.get("success", False),
        "source": source,
        "language_or_genre": language_or_genre,
        "tracks_resolved": len(cids),
        "tracks_added": add_res.get("added_count", 0),
        "skipped_duplicates": add_res.get("skipped_duplicates", 0),
    }


async def tool_get_music_recommendations(
    based_on_artists: list[str] | None = None,
    genre: str = "pop",
    limit: int = 20,
    storefront: str | None = None,
) -> dict[str, Any]:
    """Generate smart music recommendations based on selected artists or recent listening patterns."""
    rec_songs = []
    seen_ids = set()

    artists = based_on_artists or []
    if not artists:
        # Pull from recent history
        try:
            recent = await client.get_recently_played_tracks(limit=5)
            artists = list(set(t["artist"] for t in recent if t.get("artist")))
        except Exception:
            artists = []

    if not artists:
        artists = ["The Weeknd", "Dua Lipa", "Ed Sheeran"] if genre == "pop" else ["Arijit Singh", "Pritam"]

    for art in artists[:4]:
        try:
            res = await client.search_catalog(query=art, types="artists", limit=1, storefront=storefront)
            if res:
                art_id = res[0]["id"]
                top_songs = await client.get_artist_top_songs(artist_id=art_id, limit=5, storefront=storefront)
                for s in top_songs:
                    if s["id"] not in seen_ids:
                        seen_ids.add(s["id"])
                        rec_songs.append(s)
        except Exception:
            pass

    return {
        "recommendation_basis": artists,
        "count": len(rec_songs),
        "recommended_tracks": rec_songs[:limit],
    }
