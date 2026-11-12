"""Public Amazon Music catalogue link inspection tests (offline)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.alexa_media.amazon_music_public import (
    parse_public_music_url,
    read_public_music_page,
    extract_public_music_search_candidates,
    probe_public_music_search,
)


def test_public_artist_link_extracts_enya_asin():
    result = parse_public_music_url(
        "https://music.amazon.co.uk/artists/B001ED54MQ/enya",
        expected_marketplace="amazon.co.uk",
    )
    assert (result.kind, result.catalog_id) == ("artist", "B001ED54MQ")


@pytest.mark.parametrize(
    ("url", "kind", "catalog_id"),
    [
        ("https://music.amazon.de/albums/B012345678", "album", "B012345678"),
        (
            "https://music.amazon.com/albums/B012345678?trackAsin=B098765432",
            "track",
            "B098765432",
        ),
    ],
)
def test_public_catalogue_album_and_track_links(url, kind, catalog_id):
    result = parse_public_music_url(url)
    assert (result.kind, result.catalog_id) == (kind, catalog_id)


@pytest.mark.parametrize(
    "url",
    [
        "http://music.amazon.co.uk/artists/B001ED54MQ",
        "https://music.amazon.co.uk.evil.test/artists/B001ED54MQ",
        "https://user:password@music.amazon.co.uk/artists/B001ED54MQ",
        "https://music.amazon.co.uk:4433/artists/B001ED54MQ",
        "https://music.amazon.co.uk/artists/not-an-id",
        "https://music.amazon.co.uk/search/Enya",
        "https://example.com/artists/B001ED54MQ",
    ],
)
def test_public_catalogue_rejects_untrusted_urls(url):
    with pytest.raises(ValueError):
        parse_public_music_url(url)


def test_public_catalogue_rejects_wrong_marketplace():
    with pytest.raises(ValueError, match="marketplace"):
        parse_public_music_url(
            "https://music.amazon.de/artists/B001ED54MQ",
            expected_marketplace="amazon.co.uk",
        )


@pytest.mark.asyncio
async def test_public_catalogue_read_uses_no_auth_and_does_not_follow_redirect():
    response = MagicMock()
    response.status = 200
    response.headers = {"Content-Type": "text/html"}
    response.content_length = 60
    response.content.read = AsyncMock(
        return_value=b"<html><head><title>Enya on Amazon Music</title></head></html>"
    )
    ctx = AsyncMock()
    ctx.__aenter__.return_value = response
    session = MagicMock()
    session.get.return_value = ctx
    result = await read_public_music_page(
        session,
        "https://music.amazon.co.uk/artists/B001ED54MQ/enya",
        expected_marketplace="amazon.co.uk",
    )
    assert result.catalog_id == "B001ED54MQ"
    assert result.title == "Enya on Amazon Music"
    _, kwargs = session.get.call_args
    assert kwargs["allow_redirects"] is False
    assert "Authorization" not in kwargs["headers"]


def test_public_search_extracts_only_valid_matching_marketplace_links():
    html = """
    <a href="/artists/B001ED54MQ/enya">Enya</a>
    <a href="https://music.amazon.co.uk/albums/B012345678">Watermark</a>
    <a href="https://music.amazon.de/artists/B001ED54MQ">Wrong region</a>
    <a href="https://evil.example/artists/B001ED54MQ">Untrusted</a>
    <a href="/artists/INVALID">Invalid</a>
    """
    results = extract_public_music_search_candidates(
        html, marketplace="amazon.co.uk", query="Enya"
    )
    assert [(item.name, item.catalog_id) for item in results] == [
        ("Enya", "B001ED54MQ"),
        ("Watermark", "B012345678"),
    ]
    assert results[0].exact_name_match is True
    assert results[1].exact_name_match is False


@pytest.mark.asyncio
async def test_public_search_probe_no_auth_and_no_redirect():
    response = MagicMock()
    response.status = 200
    response.headers = {"Content-Type": "text/html; charset=utf-8"}
    response.content_length = None
    response.content.read = AsyncMock(
        return_value=b'<a href="/artists/B001ED54MQ/enya">Enya</a>'
    )
    ctx = AsyncMock()
    ctx.__aenter__.return_value = response
    session = MagicMock()
    session.get.return_value = ctx
    results = await probe_public_music_search(
        session, marketplace="amazon.co.uk", query="Enya"
    )
    assert results[0].catalog_id == "B001ED54MQ"
    args, kwargs = session.get.call_args
    assert args[0] == "https://music.amazon.co.uk/search/Enya"
    assert kwargs["allow_redirects"] is False
    assert "Authorization" not in kwargs["headers"]


@pytest.mark.asyncio
async def test_public_search_unavailable_does_not_invent_results():
    response = MagicMock()
    response.status = 302
    response.headers = {"Location": "https://example.com"}
    ctx = AsyncMock()
    ctx.__aenter__.return_value = response
    session = MagicMock()
    session.get.return_value = ctx
    results = await probe_public_music_search(
        session, marketplace="amazon.co.uk", query="Enya"
    )
    assert results == []


@pytest.mark.asyncio
async def test_public_search_empty_js_shell_has_no_matches():
    response = MagicMock()
    response.status = 200
    response.headers = {"Content-Type": "text/html"}
    response.content_length = 15
    response.content.read = AsyncMock(return_value=b"<html></html>")
    ctx = AsyncMock()
    ctx.__aenter__.return_value = response
    session = MagicMock()
    session.get.return_value = ctx
    assert await probe_public_music_search(
        session, marketplace="amazon.co.uk", query="Enya"
    ) == []
