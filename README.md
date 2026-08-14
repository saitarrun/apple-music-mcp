# 🎵 Apple Music High-Efficiency MCP Server

A high-performance **Model Context Protocol (MCP)** server for Apple Music, featuring a **dual-engine architecture** (macOS Native AppleScript/JXA + Async Cloud REST API), intelligent caching, cross-platform chart discovery (Shazam, Spotify, YouTube, Apple Music), smart music recommendations, and zero-timeout playlist operations.

---

## 🌟 Key Features

1. **Dual-Engine Architecture**:
   - **Native Engine (macOS)**: Compiled JXA (JavaScript for Automation) & AppleScript for instant, non-blocking bulk playlist queries, zero-timeout player controls, volume, shuffle/repeat, star rating/love/dislike, AirPlay output switching, and track management.
   - **Cloud API Engine**: Asynchronous HTTP client (`httpx`) with connection pooling, exponential jitter backoff, token segmentation (eliminating 429 errors on catalog searches), and multi-page pagination.
2. **Cross-Platform Chart & Popularity Engine**:
   - Query and auto-populate trending tracks directly from **Shazam** (All-Time Top 100, Global, India), **Spotify** (Billions Club, Hot Hits), **YouTube** (Billion+ Views Club, Viral Tracks), and **Apple Music Global Top 100**.
3. **Smart Music Recommendations**:
   - Dynamic recommendation pipeline powered by your real-time cloud listening history, heavy rotation, and artist discography similarity.
4. **High-Throughput Parallel Batching**:
   - Add or remove hundreds of songs in parallel chunks with 100% deduplication and automatic retry fallback.
5. **Pure-Audio Enforcement**:
   - Automatically filters out `music-videos` and `lyric-videos` to keep music playlists pure and clean.
6. **Smart LRU & Disk Caching**:
   - In-memory and persistent disk caching with TTL (`~/.cache/apple-music-mcp`) to eliminate redundant catalog lookups and reduce API calls by >80%.
7. **Zero-Configuration Authentication**:
   - Automatically extracts authenticated user and developer tokens directly from an open Safari or Chrome session on `music.apple.com`.

---

## 🛠️ MCP Tools Reference (22 Tools)

| Tool Name | Category | Description |
| :--- | :--- | :--- |
| `apple_music_get_cross_platform_charts` | Discovery | Fetch top tracks from **Shazam**, **Spotify**, **YouTube**, or **Apple Music** charts. |
| `apple_music_populate_from_charts` | Discovery | Populate a playlist directly from Shazam/Spotify/YouTube charts with deduplication. |
| `apple_music_get_music_recommendations` | Discovery | Smart recommendations based on artists or recent listening patterns. |
| `apple_music_get_recently_played` | Discovery | Fetch user's recent listening history from Apple Music cloud. |
| `apple_music_get_heavy_rotation` | Discovery | Fetch user's most frequently played albums and playlists. |
| `apple_music_get_artist_top_songs` | Catalog | Get top-rated and most popular tracks for any artist. |
| `apple_music_status` | System | Health check: macOS native bridge, API auth, and storefront status. |
| `apple_music_playback_control` | Playback | Control playback (`play`, `pause`, `skip`, `set_volume`, `set_shuffle`, `set_repeat`, `rate`, `love`, `dislike`). |
| `apple_music_airplay_devices` | Playback | List available AirPlay output devices (HomePods, Apple TVs, Bluetooth). |
| `apple_music_list_playlists` | Library | List user playlists with exact track counts, descriptions, and IDs. |
| `apple_music_get_playlist_tracks` | Playlists | Fast bulk retrieval of songs in a playlist with metadata and media types. |
| `apple_music_add_tracks_to_playlist` | Playlists | High-speed parallel async batch add with deduplication. |
| `apple_music_remove_tracks_from_playlist` | Playlists | Bulk remove specific track relationship IDs. |
| `apple_music_create_playlist` | Playlists | Create new playlists with custom descriptions. |
| `apple_music_delete_playlist` | Playlists | Safely delete a playlist without removing library songs. |
| `apple_music_set_playlist_description` | Playlists | Update playlist description text. |
| `apple_music_search_catalog` | Catalog | Fast global catalog search for songs, albums, artists, or curated playlists. |
| `apple_music_resolve_song` | Catalog | Pin exact studio audio catalog ID for title/artist. |
| `apple_music_get_catalog_playlist_tracks` | Catalog | Fetch tracks from official Apple Music curated playlists (e.g. `pl.xxx`). |
| `apple_music_curation_clean_videos` | Curation | Strip all video entities from a playlist and replace with audio song releases. |
| `apple_music_curation_deduplicate` | Curation | Deduplicate playlist editions, keeping canonical studio tracks. |
| `apple_music_curation_merge_playlists` | Curation | Safely merge source playlist into destination with 100% deduplication. |

---

## 🚀 Quick Start & Installation

### Run with `uvx`

```bash
uvx --from /Users/xploit404/Projects/apple-music-mcp apple-music-mcp serve
```

### Install via `pip` / `uv`

```bash
cd /Users/xploit404/Projects/apple-music-mcp
pip install -e .
```

---

## ⚙️ MCP Client Configuration

### 1. Antigravity / AGY CLI

```bash
agy mcp add apple-music -- python3 -m apple_music_mcp.server
```

### 2. Codex MCP

```bash
codex mcp add apple-music -- uvx --from /Users/xploit404/Projects/apple-music-mcp apple-music-mcp serve
```

### 3. Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "apple-music": {
      "command": "uvx",
      "args": [
        "--from",
        "/Users/xploit404/Projects/apple-music-mcp",
        "apple-music-mcp",
        "serve"
      ]
    }
  }
}
```

### 4. Cursor (`~/.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "apple-music": {
      "command": "python3",
      "args": [
        "-m",
        "apple_music_mcp.server"
      ],
      "cwd": "/Users/xploit404/Projects/apple-music-mcp"
    }
  }
}
```
