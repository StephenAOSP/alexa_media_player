"""Experimental anonymous Amazon Music GraphQL search probe.

The SpecSearchPage persisted-query hash and response shape were observed in a
consensually supplied browser HAR. A successful authenticated browser request
does NOT establish that this operation supports unauthenticated access.

This probe sends no Alexa cookies, OAuth tokens, browser API keys, CSRF tokens,
device IDs, or account identifiers. It never initiates media playback.
"""

from __future__ import annotations

from typing import Any

from aiohttp import ClientSession, ClientTimeout, DummyCookieJar

# This is a public GraphQL *query hash*, not an authentication credential.
# It is subject to change when Amazon changes its website.
_SPEC_SEARCH_HASH = (
    "19e7571fa4ccb97a7e70bacbf8877ad9f63ba23359131807300ac6eb8616b083"
)

# Minimal search groups observed in SpecSearchPage's request variables.
_SEARCH_GROUPS = (
    ("dmusic_find_artist_results_label", "artist"),
    ("dmusic_find_album_results_label", "album"),
    ("dmusic_find_song_results_label", "track"),
)


def parse_graphql_catalogue(body: Any, query: str) -> list[dict[str, Any]]:
    """Extract and deduplicate catalog results from observed search group edges."""
    if not isinstance(body, dict):
        return []
    data = body.get("data")
    search = data.get("specificationSearch") if isinstance(data, dict) else None
    groups = search.get("result") if isinstance(search, dict) else None
    if not isinstance(groups, list):
        return []
    group_types = {label: kind for label, kind in _SEARCH_GROUPS}
    found = []
    seen = set()
    for group in groups:
        if not isinstance(group, dict):
            continue
        kind = group_types.get(group.get("label"))
        edges = group.get("edges")
        if kind is None or not isinstance(edges, list):
            continue
        for edge in edges:
            node = edge.get("node") if isinstance(edge, dict) else None
            if not isinstance(node, dict):
                continue
            catalog_id = node.get("id")
            name = node.get("name") if kind == "artist" else node.get("title")
            if not (
                isinstance(catalog_id, str)
                and isinstance(name, str)
                and catalog_id.isascii()
                and catalog_id.isalnum()
                and len(catalog_id) == 10
                and name.strip()
            ):
                continue
            key = (kind, catalog_id)
            if key in seen:
                continue
            seen.add(key)
            # Do not include Amazon's opaque URI, MRN, playback parameters,
            # metric IDs, trace IDs, or raw request/response content.
            found.append(
                {
                    "type": kind,
                    "name": name.strip(),
                    "catalog_id": catalog_id,
                    "exact_name_match": name.strip().casefold() == query.casefold(),
                }
            )
    return found


async def probe_anonymous_graphql(
    *, marketplace: str, query: str
) -> dict[str, Any]:
    """Try a single anonymous, read-only GraphQL search; return safe diagnostics."""
    from .amazon_music_public import _ALLOWED_MARKETPLACES

    if marketplace not in _ALLOWED_MARKETPLACES:
        raise ValueError("Unsupported Amazon Music marketplace")
    if not isinstance(query, str) or not query.strip() or len(query) > 200:
        raise ValueError("Search text must contain 1 to 200 characters")

    query = query.strip()
    endpoint = f"https://gql.music.{marketplace}/"
    payload = {
        "operationName": "SpecSearchPage",
        "variables": {
            "searchText": query,
            "specifications": [
                {"label": label, "types": [kind], "limit": 10}
                for label, kind in _SEARCH_GROUPS
            ],
            "isAuthenticated": False,
            "audiobooksEnabled": False,
            "merchEnabled": False,
            "categoryInEntityUnionEnabled": False,
        },
        "extensions": {
            "clientLibrary": {"name": "@apollo/client", "version": "4.1.6"},
            "persistedQuery": {"version": 1, "sha256Hash": _SPEC_SEARCH_HASH},
        },
    }
    # Use an isolated session with a disabled cookie jar. Never pass Amazon
    # authentication material obtained from Home Assistant / AlexaPy.
    async with ClientSession(
        cookie_jar=DummyCookieJar(),
        timeout=ClientTimeout(total=12),
        trust_env=False,
    ) as session:
        async with session.post(
            endpoint,
            json=payload,
            allow_redirects=False,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ) as response:
            status = response.status
            mime = response.headers.get("Content-Type", "").split(";")[0]
            if status != 200 or mime != "application/json":
                return {
                    "outcome": "http_error_or_non_json",
                    "http_status": status,
                    "content_type": mime,
                    "candidates": [],
                }
            # Limit response memory, avoiding logging or returning raw data.
            content = await response.content.read(2_000_001)
            if len(content) > 2_000_000:
                return {
                    "outcome": "response_too_large",
                    "http_status": status,
                    "content_type": mime,
                    "candidates": [],
                }
            import json

            try:
                body = json.loads(content)
            except (ValueError, UnicodeDecodeError):
                return {
                    "outcome": "invalid_json",
                    "http_status": status,
                    "content_type": mime,
                    "candidates": [],
                }
    if not isinstance(body, dict):
        return {
            "outcome": "invalid_response_shape",
            "http_status": status,
            "content_type": mime,
            "candidates": [],
        }
    errors = body.get("errors")
    if isinstance(errors, list) and errors:
        # Only surface standardized codes, never arbitrary error messages.
        codes = sorted(
            {
                code
                for item in errors
                if isinstance(item, dict)
                for details in [item.get("extensions")]
                if isinstance(details, dict)
                for code in [details.get("code")]
                if isinstance(code, str) and code.isidentifier() and len(code) <= 50
            }
        )
        return {
            "outcome": "graphql_errors",
            "http_status": status,
            "content_type": mime,
            "error_count": len(errors),
            "error_codes": codes,
            "candidates": [],
        }
    candidates = parse_graphql_catalogue(body, query)
    return {
        "outcome": "catalogue_results" if candidates else "no_parsed_results",
        "http_status": status,
        "content_type": mime,
        "candidates": candidates,
    }
