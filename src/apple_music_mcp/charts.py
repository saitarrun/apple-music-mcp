from __future__ import annotations

import re
from typing import Any

from apple_music_mcp.api import client
from apple_music_mcp.cache import cache
from apple_music_mcp.config import config

# Curated registry of official Apple Music & Shazam catalog chart playlists
CHART_PLAYLIST_MAP: dict[str, dict[str, str]] = {
    "shazam": {
        "all_time": "pl.8ba78a4a65cc4530bcfdfc5154385c29",  # Top 100 Songs in Shazam of All Time
        "global": "pl.409da2016b144ce0b79b3774bdba468b",    # Top Shazam Global
        "india": "pl.9126dc6a0c5c4d058c467a988d55ff67",     # Shazam India
    },
    "apple_music": {
        "global_top_100": "pl.d25f5d1181894928af76c85c967f8f31",  # Top 100: Global
        "india_top_100": "pl.c0e98d2423e54c39b3df955c24df3cc5",   # Top 100: India
        "usa_top_100": "pl.606f5090a85547cc8996156176538d4c",     # Top 100: USA
        "todays_hits": "pl.f4d106fed2bd41149aaacabb233eb5eb",     # Today's Hits
    },
    "regional": {
        "hindi_hits": "pl.d60caf02fcce4d7e9788fe01243b7c2c",      # Bollywood Hits
        "hindi_essentials": "pl.c56477b6d3864901aa0892a260470556", # 2010s Bollywood Essentials
        "telugu_hits": "pl.1be89625ddd94a80a1dff804b41efd63",     # Telugu Hits
        "telugu_essentials": "pl.bcc521d8becd472d99600db5db1b46ea", # Ultimate Telugu
        "tamil_hits": "pl.c8d5311e407f42c89d0fce075b5aaa43",      # Tamil Hits
    },
}

# YouTube All-Time Mega Hits (Billion+ Views) Pre-Mapped Catalog Registry
YOUTUBE_BILLION_CLUB_QUERIES = [
    ("Despacito", "Luis Fonsi Daddy Yankee"),
    ("Shape of You", "Ed Sheeran"),
    ("See You Again", "Wiz Khalifa Charlie Puth"),
    ("Uptown Funk", "Mark Ronson Bruno Mars"),
    ("Sugar", "Maroon 5"),
    ("Counting Stars", "OneRepublic"),
    ("Roar", "Katy Perry"),
    ("Dark Horse", "Katy Perry"),
    ("Thinking Out Loud", "Ed Sheeran"),
    ("Blank Space", "Taylor Swift"),
    ("Shake It Off", "Taylor Swift"),
    ("Lean On", "Major Lazer DJ Snake"),
    ("Faded", "Alan Walker"),
    ("Let Her Go", "Passenger"),
    ("Girls Like You", "Maroon 5 Cardi B"),
    ("Closer", "The Chainsmokers Halsey"),
    ("Hello", "Adele"),
    ("Waka Waka", "Shakira"),
    ("Perfect", "Ed Sheeran"),
    ("Starboy", "The Weeknd Daft Punk"),
    ("The Hills", "The Weeknd"),
    ("Treat You Better", "Shawn Mendes"),
    ("Love Me Like You Do", "Ellie Goulding"),
    ("Cheap Thrills", "Sia"),
    ("Something Just Like This", "The Chainsmokers Coldplay"),
    ("Believer", "Imagine Dragons"),
    ("Thunder", "Imagine Dragons"),
    ("Radioactive", "Imagine Dragons"),
    ("Side to Side", "Ariana Grande Nicki Minaj"),
    ("7 rings", "Ariana Grande"),
    ("Havana", "Camila Cabello"),
    ("Senorita", "Shawn Mendes Camila Cabello"),
    ("Sunflower", "Post Malone Swae Lee"),
    ("Smells Like Teen Spirit", "Nirvana"),
    ("Bohemian Rhapsody", "Queen"),
    ("Sweet Child O Mine", "Guns N Roses"),
    ("In the End", "Linkin Park"),
    ("Numb", "Linkin Park"),
    ("Without Me", "Eminem"),
    ("Lose Yourself", "Eminem"),
    ("Billie Jean", "Michael Jackson"),
    ("Bad Romance", "Lady Gaga"),
    ("Titanium", "David Guetta Sia"),
    ("Wake Me Up", "Avicii"),
    ("Levels", "Avicii"),
]

# Spotify Billions Club & Flagship Chart Hits
SPOTIFY_BILLIONS_QUERIES = [
    ("Blinding Lights", "The Weeknd"),
    ("Shape of You", "Ed Sheeran"),
    ("Someone You Loved", "Lewis Capaldi"),
    ("Sunflower", "Post Malone Swae Lee"),
    ("As It Was", "Harry Styles"),
    ("Starboy", "The Weeknd Daft Punk"),
    ("One Dance", "Drake Wizkid Kyla"),
    ("Stay", "The Kid LAROI Justin Bieber"),
    ("Believer", "Imagine Dragons"),
    ("Heat Waves", "Glass Animals"),
    ("Perfect", "Ed Sheeran"),
    ("Lucid Dreams", "Juice WRLD"),
    ("Watermelon Sugar", "Harry Styles"),
    ("Levitating", "Dua Lipa"),
    ("Don't Start Now", "Dua Lipa"),
    ("Sweater Weather", "The Neighbourhood"),
    ("Circles", "Post Malone"),
    ("lovely", "Billie Eilish Khalid"),
    ("bad guy", "Billie Eilish"),
    ("Say You Won't Let Go", "James Arthur"),
    ("Shallow", "Lady Gaga Bradley Cooper"),
    ("Take Me to Church", "Hozier"),
    ("Drivers License", "Olivia Rodrigo"),
    ("Good 4 U", "Olivia Rodrigo"),
    ("Industry Baby", "Lil Nas X Jack Harlow"),
    ("Montero", "Lil Nas X"),
]


async def fetch_cross_platform_chart_tracks(
    source: str = "shazam",
    chart_type: str = "top_hits",
    language_or_genre: str = "english",
    limit: int = 30,
    storefront: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch top songs from Shazam, Spotify, YouTube, or Apple Music chart ecosystems."""
    sf = storefront or ("in" if language_or_genre.lower() in ("hindi", "telugu", "tamil") else "us")
    src = source.lower().strip()
    lang = language_or_genre.lower().strip()

    # 1. SHAZAM CHARTS
    if src == "shazam":
        if lang in ("hindi", "bollywood"):
            query = "Shazam Hindi"
        elif lang in ("telugu", "tamil"):
            query = f"Shazam {lang.capitalize()}"
        elif chart_type == "all_time":
            return await client.get_catalog_playlist_tracks(CHART_PLAYLIST_MAP["shazam"]["all_time"], storefront=sf)
        else:
            return await client.get_catalog_playlist_tracks(CHART_PLAYLIST_MAP["shazam"]["all_time"], storefront=sf)

        res = await client.search_catalog(query, types="playlists", limit=1, storefront=sf)
        if res:
            return await client.get_catalog_playlist_tracks(res[0]["id"], storefront=sf)
        return await client.get_catalog_playlist_tracks(CHART_PLAYLIST_MAP["shazam"]["all_time"], storefront=sf)

    # 2. SPOTIFY EQUIVALENT CHARTS & BILLIONS CLUB
    elif src == "spotify":
        if lang == "hindi":
            return await client.get_catalog_playlist_tracks(CHART_PLAYLIST_MAP["regional"]["hindi_hits"], storefront="in")
        elif lang == "telugu":
            return await client.get_catalog_playlist_tracks(CHART_PLAYLIST_MAP["regional"]["telugu_hits"], storefront="in")
        elif lang == "tamil":
            return await client.get_catalog_playlist_tracks(CHART_PLAYLIST_MAP["regional"]["tamil_hits"], storefront="in")
        elif chart_type in ("all_time", "billions"):
            # Resolve Spotify Billions
            resolved = []
            for title, artist in SPOTIFY_BILLIONS_QUERIES[:limit]:
                q = f"{title} {artist}"
                s_res = await client.search_catalog(q, types="songs", limit=1, storefront=sf)
                if s_res:
                    resolved.append(s_res[0])
            return resolved
        else:
            return await client.get_catalog_playlist_tracks(CHART_PLAYLIST_MAP["apple_music"]["todays_hits"], storefront=sf)

    # 3. YOUTUBE BILLION VIEWS & VIRAL
    elif src in ("youtube", "yt"):
        resolved = []
        for title, artist in YOUTUBE_BILLION_CLUB_QUERIES[:limit]:
            q = f"{title} {artist}"
            s_res = await client.search_catalog(q, types="songs", limit=1, storefront=sf)
            if s_res:
                resolved.append(s_res[0])
        return resolved

    # 4. APPLE MUSIC CHARTS & REGIONAL ESSENTIALS
    else:
        if lang == "hindi":
            return await client.get_catalog_playlist_tracks(CHART_PLAYLIST_MAP["regional"]["hindi_hits"], storefront="in")
        elif lang == "telugu":
            return await client.get_catalog_playlist_tracks(CHART_PLAYLIST_MAP["regional"]["telugu_hits"], storefront="in")
        elif lang == "tamil":
            return await client.get_catalog_playlist_tracks(CHART_PLAYLIST_MAP["regional"]["tamil_hits"], storefront="in")
        elif lang == "india":
            return await client.get_catalog_playlist_tracks(CHART_PLAYLIST_MAP["apple_music"]["india_top_100"], storefront="in")
        else:
            return await client.get_catalog_playlist_tracks(CHART_PLAYLIST_MAP["apple_music"]["global_top_100"], storefront=sf)
