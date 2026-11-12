"""Tests for authorized Amazon Music catalogue discovery (no real network)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.alexa_media.amazon_music_catalog import (
    normalize_music_search_items,
    search_amazon_music_catalog,
)


@pytest.mark.parametrize(
    ("kind", "search_key", "title_field", "expected"),
    [
        ("artist", "searchArtists", "name", "Enya"),
        ("album", "searchAlbums", "title", "Watermark"),
        ("track", "searchTracks", "title", "Orinoco Flow"),
    ],
)
def test_normalize_catalogue_result(kind, search_key, title_field, expected):
    response = {
        "data": {
            search_key: {
                "edges": [
                    {
                        "node": {
                            "id": "B001ED54MQ",
                            title_field: expected,
                            "url": "https://music.amazon.co.uk/artists/B001ED54MQ",
                        }
                    },
                    {"node": {"id": "", title_field: "Invalid"}},
                ]
            }
        }
    }
    results = normalize_music_search_items(response, kind)
    assert len(results) == 1
    assert results[0].name == expected
    assert results[0].kind == kind
    assert results[0].catalog_id == "B001ED54MQ"


@pytest.mark.asyncio
async def test_catalogue_search_posts_read_only_artist_query():
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = AsyncMock(
        return_value={
            "data": {
                "searchArtists": {
                    "edges": [
                        {"node": {"name": "Enya", "id": "B001ED54MQ"}}
                    ]
                }
            }
        }
    )
    context = AsyncMock()
    context.__aenter__.return_value = response
    session = MagicMock()
    session.post.return_value = context

    results = await search_amazon_music_catalog(
        session,
        base_url="https://music-api.example.org",
        api_key="test-key",
        bearer_token="test-token",
        query="Enya",
        kind="artist",
    )

    assert results[0].name == "Enya"
    assert results[0].catalog_id == "B001ED54MQ"
    session.post.assert_called_once()
    args, kwargs = session.post.call_args
    assert args[0] == "https://music-api.example.org/v1/search/artists"
    assert kwargs["json"]["searchFilters"] == [{"field": "name", "query": "Enya"}]
    assert kwargs["headers"]["Authorization"] == "Bearer test-token"


@pytest.mark.asyncio
async def test_catalogue_search_requires_explicit_access():
    session = MagicMock()
    with pytest.raises(ValueError, match="credentials"):
        await search_amazon_music_catalog(
            session,
            base_url="https://music-api.example.org",
            api_key="",
            bearer_token="",
            query="Enya",
            kind="artist",
        )
    session.post.assert_not_called()


def test_catalogue_search_unknown_schema_returns_no_candidates():
    assert normalize_music_search_items({"data": {}}, "artist") == []
