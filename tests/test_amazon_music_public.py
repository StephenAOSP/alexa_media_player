"""Public Amazon Music catalogue link inspection tests (offline)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.alexa_media.amazon_music_public import (
    parse_public_music_url,
    read_public_music_page,
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
