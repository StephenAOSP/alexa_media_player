"""Experimental read-only Amazon Music catalogue search.

Amazon's Music Web API is restricted to approved partners. This client requires
an explicitly authorized catalogue endpoint, API key and OAuth token. Alexa
login cookies / tokens are NOT interchangeable with Music API credentials.
Search results are catalogue IDs, never native Alexa musicAlarmId values.
"""

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from aiohttp import ClientSession


@dataclass(frozen=True)
class MusicCatalogueItem:
    """An Amazon Music artist, album or track search candidate."""

    kind: str
    name: str
    catalog_id: str
    artist_name: str | None = None
    url: str | None = None


def normalize_music_search_items(
    response: dict[str, Any], kind: str
) -> list[MusicCatalogueItem]:
    """Extract catalogue candidates from a Music Web API v1 search response.

    Responses outside the documented entity-group shape are not guessed at.
    No selection is made automatically when multiple candidates are returned.
    """
    if kind not in ("artist", "album", "track"):
        raise ValueError("Unsupported catalogue item type")
    search_key = {"artist": "searchArtists", "album": "searchAlbums", "track": "searchTracks"}[kind]
    data = response.get("data")
    if not isinstance(data, dict):
        return []
    group = data.get(search_key)
    if not isinstance(group, dict):
        return []
    # In the V1 API, search results are returned as a collection of edges.
    edges = group.get("edges")
    if not isinstance(edges, list):
        return []
    items = []
    for edge in edges:
        node = edge.get("node") if isinstance(edge, dict) else None
        if not isinstance(node, dict):
            continue
        name = node.get("name") if kind == "artist" else node.get("title")
        catalog_id = node.get("id")
        if not all(isinstance(v, str) and v.strip() for v in (name, catalog_id)):
            continue
        artist = node.get("artist")
        artist_name = artist.get("name") if isinstance(artist, dict) else None
        raw_url = node.get("url")
        items.append(
            MusicCatalogueItem(
                kind=kind,
                name=name.strip(),
                catalog_id=catalog_id.strip(),
                artist_name=artist_name if isinstance(artist_name, str) else None,
                url=raw_url if isinstance(raw_url, str) else None,
            )
        )
    return items


async def search_amazon_music_catalog(
    session: ClientSession,
    *,
    base_url: str,
    api_key: str,
    bearer_token: str,
    query: str,
    kind: str,
    limit: int = 10,
) -> list[MusicCatalogueItem]:
    """Search Amazon Music's partner catalogue API without any playback.

    The API endpoint and credentials must be supplied by an authorized partner;
    this is NOT an anonymously accessible or Alexa-cookie-based lookup.
    """
    if kind not in ("artist", "album", "track"):
        raise ValueError("kind must be artist, album or track")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search text must not be blank")
    if not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("An authorized HTTPS Music API base URL is required")
    if not api_key or not bearer_token:
        raise ValueError("Amazon Music partner API credentials are required")

    endpoint = f"{base_url.rstrip('/')}/v1/search/{kind}s"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "searchFilters": [{"field": "name", "query": query.strip()}],
        "limit": limit,
        "sortBy": "relevance",
    }
    async with session.post(endpoint, headers=headers, json=payload) as response:
        response.raise_for_status()
        body = await response.json()
    if not isinstance(body, dict):
        raise ValueError("Amazon Music search returned an invalid response")
    return normalize_music_search_items(body, kind)
