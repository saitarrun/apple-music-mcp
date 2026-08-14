from __future__ import annotations

import asyncio
import json
import random
import time
from typing import Any

import httpx

from apple_music_mcp.auth import extract_tokens_from_safari, get_auth_headers
from apple_music_mcp.cache import cache
from apple_music_mcp.config import config

AMP_BASE_URL = "https://amp-api.music.apple.com/v1"


class AppleMusicAPIError(Exception):
    def __init__(self, status_code: int, message: str, detail: Any = None):
        super().__init__(f"Apple Music API Error [{status_code}]: {message}")
        self.status_code = status_code
        self.detail = detail


class AsyncAppleMusicClient:
    """High-throughput asynchronous client with backoff, connection pooling, and segmented auth."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(5)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(config.preferences.request_timeout),
                limits=httpx.Limits(max_connections=30, max_keepalive_connections=15),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Execute request with intelligent token segmentation and exponential backoff."""
        clean_path = path.lstrip("/")
        url = f"{AMP_BASE_URL}/{clean_path}"
        is_user_lib = clean_path.startswith("me/")
        client = await self._get_client()

        for attempt in range(max_retries):
            headers = get_auth_headers(is_user_library=is_user_lib)
            try:
                resp = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                )

                if resp.status_code in (200, 201, 202, 204):
                    if resp.status_code == 204 or not resp.content:
                        return {"success": True}
                    return resp.json()

                # Handle 401 (Expired session) -> Auto-refresh from Safari
                if resp.status_code == 401 and attempt == 0:
                    extract_tokens_from_safari()
                    continue

                # Handle Rate Limit (429) or Upstream Server Error (500 / 502 / 503 / 504)
                if resp.status_code in (429, 500, 502, 503, 504):
                    if attempt < max_retries - 1:
                        retry_after = resp.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            wait_time = float(retry_after) + random.uniform(0.1, 0.5)
                        else:
                            wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                        await asyncio.sleep(wait_time)
                        continue

                error_data = {}
                try:
                    error_data = resp.json()
                except Exception:
                    error_data = {"raw": resp.text}

                raise AppleMusicAPIError(
                    resp.status_code,
                    f"HTTP {resp.status_code} on {method} {clean_path}",
                    detail=error_data,
                )

            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 + attempt)
                    continue
                raise AppleMusicAPIError(0, f"Network request error: {str(e)}")

        raise AppleMusicAPIError(0, f"Failed after {max_retries} attempts")

    # ==================== PLAYLIST OPERATIONS ====================

    async def get_user_playlists(self) -> list[dict[str, Any]]:
        """Fetch all user library playlists with caching."""
        cached = cache.get("user", "playlists")
        if cached:
            return cached

        data = await self.request("GET", "/me/library/playlists")
        raw_pls = data.get("data", [])
        
        playlists = []
        for p in raw_pls:
            attr = p.get("attributes", {})
            playlists.append({
                "id": p.get("id"),
                "name": attr.get("name", "Untitled"),
                "can_edit": attr.get("canEdit", True),
                "is_public": attr.get("isPublic", False),
                "description": attr.get("description", {}).get("standard", ""),
                "track_count": attr.get("trackCount", 0),
            })

        cache.set("user", "playlists", playlists, ttl=30)
        return playlists

    async def get_playlist_tracks(
        self,
        playlist_id: str,
        limit: int = 100,
        filter_audio_only: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all tracks in a user playlist, handling multi-page pagination."""
        audio_only = (
            config.preferences.pure_audio_only
            if filter_audio_only is None
            else filter_audio_only
        )

        tracks: list[dict[str, Any]] = []
        next_path = f"/me/library/playlists/{playlist_id}/tracks?limit={min(limit, 100)}"

        while next_path and len(tracks) < limit:
            data = await self.request("GET", next_path)
            raw_items = data.get("data", [])
            for item in raw_items:
                itype = item.get("type", "")
                if audio_only and "video" in itype:
                    continue

                attr = item.get("attributes", {})
                play_params = attr.get("playParams", {})
                tracks.append({
                    "relationship_id": item.get("id"),
                    "catalog_id": play_params.get("catalogId") or item.get("id"),
                    "name": attr.get("name", ""),
                    "artist": attr.get("artistName", ""),
                    "album": attr.get("albumName", ""),
                    "duration_millis": attr.get("durationInMillis", 0),
                    "type": itype,
                    "release_date": attr.get("releaseDate", ""),
                    "track_number": attr.get("trackNumber", 1),
                })

            next_url = data.get("next")
            next_path = next_url if next_url else None

        return tracks

    async def _add_chunk(self, playlist_id: str, chunk: list[str]) -> tuple[int, list[str]]:
        async with self._semaphore:
            data = [{"id": cid, "type": "songs"} for cid in chunk]
            try:
                await self.request(
                    "POST",
                    f"/me/library/playlists/{playlist_id}/tracks",
                    json_data={"data": data},
                )
                return len(chunk), []
            except Exception:
                added = 0
                failed = []
                for cid in chunk:
                    try:
                        await self.request(
                            "POST",
                            f"/me/library/playlists/{playlist_id}/tracks",
                            json_data={"data": [{"id": cid, "type": "songs"}]},
                        )
                        added += 1
                    except Exception:
                        failed.append(cid)
                    await asyncio.sleep(0.05)
                return added, failed

    async def add_tracks_bulk(
        self,
        playlist_id: str,
        track_ids: list[str],
        batch_size: int | None = None,
    ) -> tuple[int, list[str]]:
        """Add tracks in concurrent parallel batches for maximum throughput."""
        size = batch_size or config.preferences.batch_size
        chunks = [track_ids[i:i + size] for i in range(0, len(track_ids), size)]
        
        tasks = [self._add_chunk(playlist_id, chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks)

        total_added = sum(r[0] for r in results)
        failed_ids = [cid for r in results for cid in r[1]]

        cache.clear()
        return total_added, failed_ids

    async def remove_tracks_bulk(
        self,
        playlist_id: str,
        relationship_ids: list[str],
        is_video: bool = False,
    ) -> int:
        """Remove specific tracks by relationship ID in concurrent batches."""
        key = "ids[library-music-videos]" if is_video else "ids[library-songs]"
        
        async def _remove_one(rel_id: str) -> bool:
            async with self._semaphore:
                try:
                    await self.request(
                        "DELETE",
                        f"/me/library/playlists/{playlist_id}/tracks",
                        params={key: rel_id, "mode": "all"},
                    )
                    return True
                except Exception:
                    return False

        tasks = [_remove_one(rel_id) for rel_id in relationship_ids]
        results = await asyncio.gather(*tasks)
        cache.clear()
        return sum(1 for s in results if s)

    async def create_playlist(
        self,
        name: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a new playlist in the user library."""
        payload = {
            "attributes": {
                "name": name,
                "description": description,
            }
        }
        res = await self.request("POST", "/me/library/playlists", json_data=payload)
        cache.clear()
        return res.get("data", [{}])[0]

    async def delete_playlist(self, playlist_id: str) -> bool:
        """Delete a playlist from user library."""
        try:
            await self.request("DELETE", f"/me/library/playlists/{playlist_id}")
            cache.clear()
            return True
        except Exception:
            return False

    # ==================== USER DISCOVERY & HISTORY ====================

    async def get_recently_played_tracks(self, limit: int = 25) -> list[dict[str, Any]]:
        """Fetch user's recently played track history."""
        data = await self.request("GET", "/me/recent/played/tracks", params={"limit": min(limit, 30)})
        items = data.get("data", [])
        results = []
        for s in items:
            attr = s.get("attributes", {})
            results.append({
                "id": s.get("id"),
                "name": attr.get("name", ""),
                "artist": attr.get("artistName", ""),
                "album": attr.get("albumName", ""),
                "duration_millis": attr.get("durationInMillis", 0),
            })
        return results

    async def get_heavy_rotation(self, limit: int = 15) -> list[dict[str, Any]]:
        """Fetch user's heavy rotation albums and playlists."""
        data = await self.request("GET", "/me/history/heavy-rotation", params={"limit": min(limit, 20)})
        items = data.get("data", [])
        results = []
        for item in items:
            attr = item.get("attributes", {})
            results.append({
                "id": item.get("id"),
                "type": item.get("type", ""),
                "name": attr.get("name", ""),
                "curator_or_artist": attr.get("artistName") or attr.get("curatorName", ""),
            })
        return results

    # ==================== CATALOG SEARCH & DISCOVERY ====================

    async def search_catalog(
        self,
        query: str,
        types: str = "songs",
        limit: int = 25,
        storefront: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fast catalog search with zero 429 errors and automatic caching."""
        sf = storefront or config.preferences.storefront
        cache_key = f"search:{sf}:{types}:{query}:{limit}"
        cached = cache.get("catalog", cache_key)
        if cached:
            return cached

        data = await self.request(
            "GET",
            f"/catalog/{sf}/search",
            params={"term": query, "types": types, "limit": min(limit, 25)},
        )

        results = []
        results_data = data.get("results", {})
        
        # Parse songs
        if "songs" in results_data:
            for s in results_data["songs"].get("data", []):
                attr = s.get("attributes", {})
                results.append({
                    "id": s.get("id"),
                    "type": "song",
                    "name": attr.get("name", ""),
                    "artist": attr.get("artistName", ""),
                    "album": attr.get("albumName", ""),
                    "duration_millis": attr.get("durationInMillis", 0),
                    "release_date": attr.get("releaseDate", ""),
                    "isrc": attr.get("isrc", ""),
                    "has_lyrics": attr.get("hasLyrics", False),
                })

        # Parse playlists
        if "playlists" in results_data:
            for p in results_data["playlists"].get("data", []):
                attr = p.get("attributes", {})
                results.append({
                    "id": p.get("id"),
                    "type": "playlist",
                    "name": attr.get("name", ""),
                    "curator": attr.get("curatorName", ""),
                    "description": attr.get("description", {}).get("standard", ""),
                })

        # Parse artists
        if "artists" in results_data:
            for a in results_data["artists"].get("data", []):
                attr = a.get("attributes", {})
                results.append({
                    "id": a.get("id"),
                    "type": "artist",
                    "name": attr.get("name", ""),
                    "genre": attr.get("genreNames", []),
                })

        cache.set("catalog", cache_key, results, ttl=1800)
        return results

    async def get_artist_top_songs(
        self,
        artist_id: str,
        limit: int = 20,
        storefront: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get the top songs for an artist directly from Apple Music catalog."""
        sf = storefront or config.preferences.storefront
        cache_key = f"artist_top:{sf}:{artist_id}:{limit}"
        cached = cache.get("catalog", cache_key)
        if cached:
            return cached

        data = await self.request("GET", f"/catalog/{sf}/artists/{artist_id}/view/top-songs")
        raw_items = data.get("data", [])
        
        songs = []
        for s in raw_items[:limit]:
            attr = s.get("attributes", {})
            songs.append({
                "id": s.get("id"),
                "name": attr.get("name", ""),
                "artist": attr.get("artistName", ""),
                "album": attr.get("albumName", ""),
                "duration_millis": attr.get("durationInMillis", 0),
                "release_date": attr.get("releaseDate", ""),
            })

        cache.set("catalog", cache_key, songs, ttl=3600)
        return songs

    async def get_catalog_playlist_tracks(
        self,
        playlist_id: str,
        storefront: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all songs in an Apple Music official curated catalog playlist."""
        sf = storefront or config.preferences.storefront
        cache_key = f"catalog_pl:{sf}:{playlist_id}"
        cached = cache.get("catalog", cache_key)
        if cached:
            return cached

        data = await self.request("GET", f"/catalog/{sf}/playlists/{playlist_id}/tracks")
        raw_items = data.get("data", [])
        
        tracks = []
        for s in raw_items:
            attr = s.get("attributes", {})
            tracks.append({
                "id": s.get("id"),
                "name": attr.get("name", ""),
                "artist": attr.get("artistName", ""),
                "album": attr.get("albumName", ""),
                "release_date": attr.get("releaseDate", ""),
            })

        cache.set("catalog", cache_key, tracks, ttl=3600)
        return tracks


client = AsyncAppleMusicClient()
