from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from apple_music_mcp.tools import catalog, curation, discovery, library, playback, playlists, recommendations

# Initialize MCP Server
app = Server("apple-music-mcp")

# Tool Definitions
TOOLS = [
    types.Tool(
        name="apple_music_status",
        description="Check Apple Music configuration, native macOS AppleScript bridge, and API authentication status.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    types.Tool(
        name="apple_music_playback_control",
        description="Control local Apple Music player on macOS (play, pause, next, previous, volume, shuffle, repeat, rate, love, dislike).",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["play", "pause", "toggle", "next", "previous", "set_volume", "set_shuffle", "set_repeat", "rate", "love", "dislike"],
                    "description": "Playback action to perform.",
                },
                "track": {"type": "string", "description": "Track name to play (for action='play')."},
                "volume": {"type": "integer", "minimum": 0, "maximum": 100, "description": "Sound volume level 0-100."},
                "shuffle": {"type": "boolean", "description": "Enable or disable shuffle."},
                "repeat": {"type": "string", "enum": ["off", "one", "all"], "description": "Repeat mode."},
                "rating_stars": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Star rating 1-5 (for action='rate')."},
            },
            "required": ["action"],
        },
    ),
    types.Tool(
        name="apple_music_airplay_devices",
        description="List available AirPlay output devices (HomePods, Apple TVs, Bluetooth speakers).",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    types.Tool(
        name="apple_music_get_recently_played",
        description="Fetch user's recently played track listening history from Apple Music cloud.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 25, "description": "Number of recent tracks to fetch (max 30)."},
            },
        },
    ),
    types.Tool(
        name="apple_music_get_heavy_rotation",
        description="Fetch user's heavy rotation albums and playlists.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 15, "description": "Number of items to fetch (max 20)."},
            },
        },
    ),
    types.Tool(
        name="apple_music_get_cross_platform_charts",
        description="Fetch popular, top viewed, and most streamed songs from Shazam, Spotify, YouTube, or Apple Music charts.",
        inputSchema={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["shazam", "spotify", "youtube", "apple_music"],
                    "default": "shazam",
                    "description": "Chart ecosystem to pull from.",
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["top_hits", "all_time", "billions", "viral"],
                    "default": "top_hits",
                    "description": "Category of chart.",
                },
                "language_or_genre": {
                    "type": "string",
                    "default": "english",
                    "description": "Language or genre (e.g. 'english', 'hindi', 'telugu', 'tamil', 'pop').",
                },
                "limit": {"type": "integer", "default": 30, "description": "Number of songs to fetch."},
                "storefront": {"type": "string", "description": "Country storefront ('in', 'us')."},
            },
        },
    ),
    types.Tool(
        name="apple_music_populate_from_charts",
        description="Populate a playlist directly with popular songs from Shazam, Spotify, YouTube, or Apple Music with deduplication.",
        inputSchema={
            "type": "object",
            "properties": {
                "playlist_id": {"type": "string", "description": "Destination playlist ID (e.g. 'p.xxx')."},
                "source": {
                    "type": "string",
                    "enum": ["shazam", "spotify", "youtube", "apple_music"],
                    "default": "shazam",
                    "description": "Chart source to pull from.",
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["top_hits", "all_time", "billions", "viral"],
                    "default": "top_hits",
                    "description": "Type of chart.",
                },
                "language_or_genre": {"type": "string", "default": "english", "description": "Language or genre."},
                "limit": {"type": "integer", "default": 30, "description": "Max songs to add."},
                "allow_duplicates": {"type": "boolean", "default": False, "description": "Whether to allow duplicate tracks."},
            },
            "required": ["playlist_id"],
        },
    ),
    types.Tool(
        name="apple_music_get_music_recommendations",
        description="Generate smart music recommendations based on selected artists or recent listening patterns.",
        inputSchema={
            "type": "object",
            "properties": {
                "based_on_artists": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of artist names to base recommendations on.",
                },
                "genre": {"type": "string", "default": "pop", "description": "Target genre if no artists specified."},
                "limit": {"type": "integer", "default": 20, "description": "Max recommendations to return."},
            },
        },
    ),
    types.Tool(
        name="apple_music_list_playlists",
        description="List all playlists in the user's Apple Music library with track counts and descriptions.",
        inputSchema={
            "type": "object",
            "properties": {
                "use_api": {"type": "boolean", "description": "Force using Cloud API instead of native macOS bridge."},
            },
        },
    ),
    types.Tool(
        name="apple_music_get_playlist_tracks",
        description="Fetch all songs from a playlist with name, artist, album, duration, catalog ID, and media type.",
        inputSchema={
            "type": "object",
            "properties": {
                "playlist_id_or_name": {"type": "string", "description": "Playlist ID (e.g. 'p.xxx') or exact playlist name."},
                "limit": {"type": "integer", "default": 500, "description": "Maximum number of tracks to fetch."},
                "filter_audio_only": {"type": "boolean", "default": True, "description": "Filter out music-videos to ensure pure audio."},
            },
            "required": ["playlist_id_or_name"],
        },
    ),
    types.Tool(
        name="apple_music_add_tracks_to_playlist",
        description="Add multiple songs to a user playlist in high-speed parallel batches with deduplication.",
        inputSchema={
            "type": "object",
            "properties": {
                "playlist_id": {"type": "string", "description": "Destination playlist ID (e.g. 'p.xxx')."},
                "catalog_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of Apple Music catalog song IDs to add.",
                },
                "allow_duplicates": {"type": "boolean", "default": False, "description": "Whether to allow duplicate tracks."},
            },
            "required": ["playlist_id", "catalog_ids"],
        },
    ),
    types.Tool(
        name="apple_music_remove_tracks_from_playlist",
        description="Remove specific tracks from a user playlist using relationship IDs.",
        inputSchema={
            "type": "object",
            "properties": {
                "playlist_id": {"type": "string", "description": "Playlist ID (e.g. 'p.xxx')."},
                "relationship_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of track relationship IDs to remove.",
                },
                "is_video": {"type": "boolean", "default": False, "description": "Whether the tracks are music-video items."},
            },
            "required": ["playlist_id", "relationship_ids"],
        },
    ),
    types.Tool(
        name="apple_music_create_playlist",
        description="Create a new playlist in Apple Music with custom metadata and description.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the new playlist."},
                "description": {"type": "string", "default": "", "description": "Description text for the playlist."},
            },
            "required": ["name"],
        },
    ),
    types.Tool(
        name="apple_music_delete_playlist",
        description="Delete a user playlist safely from Apple Music without removing underlying songs from library.",
        inputSchema={
            "type": "object",
            "properties": {
                "playlist_id_or_name": {"type": "string", "description": "Playlist ID (e.g. 'p.xxx') or playlist name."},
            },
            "required": ["playlist_id_or_name"],
        },
    ),
    types.Tool(
        name="apple_music_set_playlist_description",
        description="Set or update the description text for an existing playlist.",
        inputSchema={
            "type": "object",
            "properties": {
                "playlist_name": {"type": "string", "description": "Exact name of the playlist."},
                "description": {"type": "string", "description": "New description text."},
            },
            "required": ["playlist_name", "description"],
        },
    ),
    types.Tool(
        name="apple_music_search_catalog",
        description="Search global Apple Music catalog for songs, albums, playlists, or artists with caching.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword / phrase."},
                "types": {"type": "string", "default": "songs", "description": "Comma-separated types: 'songs', 'albums', 'playlists', 'artists'."},
                "limit": {"type": "integer", "default": 25, "description": "Maximum number of results to return."},
                "storefront": {"type": "string", "description": "Two-letter country storefront (e.g. 'in', 'us', 'gb')."},
            },
            "required": ["query"],
        },
    ),
    types.Tool(
        name="apple_music_get_artist_top_songs",
        description="Fetch top rated and most popular tracks for an artist directly from Apple Music catalog.",
        inputSchema={
            "type": "object",
            "properties": {
                "artist_name_or_id": {"type": "string", "description": "Artist name (e.g. 'A.R. Rahman', 'The Weeknd') or Apple Music artist ID."},
                "limit": {"type": "integer", "default": 20, "description": "Number of top songs to fetch."},
                "storefront": {"type": "string", "description": "Storefront code (e.g. 'in', 'us')."},
            },
            "required": ["artist_name_or_id"],
        },
    ),
    types.Tool(
        name="apple_music_resolve_song",
        description="Pin the exact official catalog ID for a specific song title and artist.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Song title."},
                "artist": {"type": "string", "default": "", "description": "Artist name."},
                "storefront": {"type": "string", "description": "Storefront code."},
            },
            "required": ["title"],
        },
    ),
    types.Tool(
        name="apple_music_get_catalog_playlist_tracks",
        description="Fetch all tracks from an official Apple Music curated catalog playlist (e.g. 'pl.xxx').",
        inputSchema={
            "type": "object",
            "properties": {
                "playlist_id": {"type": "string", "description": "Catalog playlist ID (e.g. 'pl.xxx')."},
                "storefront": {"type": "string", "description": "Storefront code."},
            },
            "required": ["playlist_id"],
        },
    ),
    types.Tool(
        name="apple_music_curation_clean_videos",
        description="Strip all music-videos from a playlist and replace them with official studio audio song releases.",
        inputSchema={
            "type": "object",
            "properties": {
                "playlist_id": {"type": "string", "description": "Playlist ID (e.g. 'p.xxx')."},
                "replace_with_audio": {"type": "boolean", "default": True, "description": "Whether to find and add audio replacements."},
            },
            "required": ["playlist_id"],
        },
    ),
    types.Tool(
        name="apple_music_curation_deduplicate",
        description="Scan and deduplicate a playlist, preserving only the canonical edition of each song.",
        inputSchema={
            "type": "object",
            "properties": {
                "playlist_id": {"type": "string", "description": "Playlist ID (e.g. 'p.xxx')."},
            },
            "required": ["playlist_id"],
        },
    ),
    types.Tool(
        name="apple_music_curation_merge_playlists",
        description="Safely merge tracks from source playlist to destination with 100% deduplication.",
        inputSchema={
            "type": "object",
            "properties": {
                "source_playlist_id": {"type": "string", "description": "Source playlist ID (e.g. 'p.xxx')."},
                "destination_playlist_id": {"type": "string", "description": "Destination playlist ID (e.g. 'p.xxx')."},
                "delete_source_after_merge": {"type": "boolean", "default": False, "description": "Delete source playlist once merged."},
            },
            "required": ["source_playlist_id", "destination_playlist_id"],
        },
    ),
]


async def handle_list_tools(
    _ctx: Any, _params: types.PaginatedRequestParams
) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOLS)


async def handle_call_tool(
    _ctx: Any, params: types.CallToolRequestParams
) -> types.CallToolResult:
    name = params.name
    args = params.arguments or {}
    res: Any = {}

    try:
        if name == "apple_music_status":
            res = library.tool_system_status()
        elif name == "apple_music_playback_control":
            res = playback.tool_playback_control(
                action=args.get("action", ""),
                track=args.get("track"),
                volume=args.get("volume"),
                shuffle=args.get("shuffle"),
                repeat=args.get("repeat"),
                rating_stars=args.get("rating_stars"),
            )
        elif name == "apple_music_airplay_devices":
            res = playback.tool_airplay_devices()
        elif name == "apple_music_get_recently_played":
            res = await recommendations.tool_get_recently_played(limit=args.get("limit", 25))
        elif name == "apple_music_get_heavy_rotation":
            res = await recommendations.tool_get_heavy_rotation(limit=args.get("limit", 15))
        elif name == "apple_music_get_cross_platform_charts":
            res = await discovery.tool_get_cross_platform_charts(
                source=args.get("source", "shazam"),
                chart_type=args.get("chart_type", "top_hits"),
                language_or_genre=args.get("language_or_genre", "english"),
                limit=args.get("limit", 30),
                storefront=args.get("storefront"),
            )
        elif name == "apple_music_populate_from_charts":
            res = await discovery.tool_populate_from_charts(
                playlist_id=args["playlist_id"],
                source=args.get("source", "shazam"),
                chart_type=args.get("chart_type", "top_hits"),
                language_or_genre=args.get("language_or_genre", "english"),
                limit=args.get("limit", 30),
                allow_duplicates=args.get("allow_duplicates", False),
            )
        elif name == "apple_music_get_music_recommendations":
            res = await discovery.tool_get_music_recommendations(
                based_on_artists=args.get("based_on_artists"),
                genre=args.get("genre", "pop"),
                limit=args.get("limit", 20),
            )
        elif name == "apple_music_list_playlists":
            res = await library.tool_library_playlists(use_api=args.get("use_api", False))
        elif name == "apple_music_get_playlist_tracks":
            res = await playlists.tool_playlist_get_tracks(
                playlist_id_or_name=args["playlist_id_or_name"],
                limit=args.get("limit", 500),
                filter_audio_only=args.get("filter_audio_only", True),
            )
        elif name == "apple_music_add_tracks_to_playlist":
            res = await playlists.tool_playlist_add_tracks(
                playlist_id=args["playlist_id"],
                catalog_ids=args.get("catalog_ids", []),
                allow_duplicates=args.get("allow_duplicates", False),
            )
        elif name == "apple_music_remove_tracks_from_playlist":
            res = await playlists.tool_playlist_remove_tracks(
                playlist_id=args["playlist_id"],
                relationship_ids=args.get("relationship_ids", []),
                is_video=args.get("is_video", False),
            )
        elif name == "apple_music_create_playlist":
            res = await playlists.tool_playlist_create(
                name=args["name"],
                description=args.get("description", ""),
            )
        elif name == "apple_music_delete_playlist":
            res = await playlists.tool_playlist_delete(playlist_id_or_name=args["playlist_id_or_name"])
        elif name == "apple_music_set_playlist_description":
            res = playlists.tool_playlist_set_description(
                playlist_name=args["playlist_name"],
                description=args.get("description", ""),
            )
        elif name == "apple_music_search_catalog":
            res = await catalog.tool_catalog_search(
                query=args["query"],
                types=args.get("types", "songs"),
                limit=args.get("limit", 25),
                storefront=args.get("storefront"),
            )
        elif name == "apple_music_get_artist_top_songs":
            res = await catalog.tool_catalog_artist_top_songs(
                artist_name_or_id=args["artist_name_or_id"],
                limit=args.get("limit", 20),
                storefront=args.get("storefront"),
            )
        elif name == "apple_music_resolve_song":
            res = await catalog.tool_catalog_resolve_song(
                title=args["title"],
                artist=args.get("artist", ""),
                storefront=args.get("storefront"),
            )
        elif name == "apple_music_get_catalog_playlist_tracks":
            res = await catalog.tool_catalog_playlist_tracks(
                playlist_id=args["playlist_id"],
                storefront=args.get("storefront"),
            )
        elif name == "apple_music_curation_clean_videos":
            res = await curation.tool_curation_clean_videos(
                playlist_id=args["playlist_id"],
                replace_with_audio=args.get("replace_with_audio", True),
            )
        elif name == "apple_music_curation_deduplicate":
            res = await curation.tool_curation_deduplicate(playlist_id=args["playlist_id"])
        elif name == "apple_music_curation_merge_playlists":
            res = await curation.tool_curation_merge_playlists(
                source_playlist_id=args["source_playlist_id"],
                destination_playlist_id=args["destination_playlist_id"],
                delete_source_after_merge=args.get("delete_source_after_merge", False),
            )
        else:
            res = {"error": f"Unknown tool: {name}"}
    except Exception as e:
        res = {"error": str(e)}

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(res, indent=2))]
    )


# Register handlers
app.add_request_handler("tools/list", types.PaginatedRequestParams, handle_list_tools)
app.add_request_handler("tools/call", types.CallToolRequestParams, handle_call_tool)


async def run_server():
    """Run MCP server over stdio streams."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


def main():
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
