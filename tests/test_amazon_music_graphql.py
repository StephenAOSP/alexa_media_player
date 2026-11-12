"""Offline tests of observed Amazon Music GraphQL response parsing."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media.amazon_music_graphql import (
    parse_graphql_catalogue,
    probe_anonymous_graphql,
)


@pytest.fixture
def sample_search_response():
    """Minimal fabricated response following the captured SpecSearchPage shape."""
    return {
        "data": {
            "specificationSearch": {
                "result": [
                    {
                        "label": "dmusic_find_artist_results_label",
                        "edges": [
                            {"node": {"id": "B001NMX024", "name": "Florence + The Machine"}}
                        ],
                    },
                    {
                        "label": "dmusic_find_album_results_label",
                        "edges": [
                            {"node": {"id": "B00K39U8QO", "title": "Lungs"}}
                        ],
                    },
                    {
                        "label": "dmusic_find_song_results_label",
                        "edges": [
                            {"node": {"id": "B0HPS2W8ST", "title": "Which Witch (Live)"}}
                        ],
                    },
                ]
            }
        }
    }


def test_graphql_parser_identifies_artist_album_track(sample_search_response):
    results = parse_graphql_catalogue(sample_search_response, "Florence + The Machine")
    assert [(x["type"], x["catalog_id"]) for x in results] == [
        ("artist", "B001NMX024"),
        ("album", "B00K39U8QO"),
        ("track", "B0HPS2W8ST"),
    ]
    assert results[0]["exact_name_match"] is True


def test_graphql_parser_drops_invalid_and_duplicate_ids(sample_search_response):
    edges = sample_search_response["data"]["specificationSearch"]["result"][0]["edges"]
    edges.append({"node": {"name": "Duplicate", "id": "B001NMX024"}})
    edges.append({"node": {"name": "Malicious", "id": "https://evil.test/"}})
    assert len(parse_graphql_catalogue(sample_search_response, "Florence")) == 3


@pytest.mark.asyncio
async def test_graphql_probe_sends_no_browser_credentials(sample_search_response):
    import json

    response = MagicMock()
    response.status = 200
    response.headers = {"Content-Type": "application/json"}
    response.content.read = AsyncMock(
        return_value=json.dumps(sample_search_response).encode()
    )
    context = AsyncMock()
    context.__aenter__.return_value = response
    session = MagicMock()
    session.post.return_value = context
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    with patch(
        "custom_components.alexa_media.amazon_music_graphql.ClientSession",
        return_value=session,
    ) as session_class:
        result = await probe_anonymous_graphql(
            marketplace="amazon.co.uk", query="Florence + The Machine"
        )
    assert result["outcome"] == "catalogue_results"
    assert len(result["candidates"]) == 3
    assert session_class.call_args.kwargs["trust_env"] is False
    assert session_class.call_args.kwargs["cookie_jar"].__class__.__name__ == "DummyCookieJar"
    args, kwargs = session.post.call_args
    assert args[0] == "https://gql.music.amazon.co.uk/"
    assert kwargs["allow_redirects"] is False
    assert set(kwargs["headers"]) == {"Accept", "Content-Type"}
    assert kwargs["json"]["variables"]["isAuthenticated"] is False
    assert kwargs["json"]["operationName"] == "SpecSearchPage"


@pytest.mark.asyncio
async def test_graphql_probe_reports_http_denial():
    response = MagicMock()
    response.status = 403
    response.headers = {"Content-Type": "text/html"}
    context = AsyncMock()
    context.__aenter__.return_value = response
    session = MagicMock()
    session.post.return_value = context
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    with patch(
        "custom_components.alexa_media.amazon_music_graphql.ClientSession",
        return_value=session,
    ):
        result = await probe_anonymous_graphql(
            marketplace="amazon.co.uk", query="Enya"
        )
    assert result["outcome"] == "http_error_or_non_json"
    assert result["http_status"] == 403
    assert result["candidates"] == []
