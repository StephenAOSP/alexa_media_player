"""Safe unauthenticated reading of known public Amazon Music catalogue links.

This does not discover links by an artist name, does not create alarms, and
does not turn ASINs into Alexa's native musicAlarmId UUID.
"""

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import quote, urljoin
import re
from urllib.parse import urlparse

from aiohttp import ClientSession

_ID_RE = re.compile(r"^[A-Z0-9]{10}$")
_ALLOWED_MARKETPLACES = frozenset({
    "amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
    "amazon.it", "amazon.es", "amazon.co.jp", "amazon.ca",
    "amazon.com.au", "amazon.com.br", "amazon.com.mx", "amazon.in",
    "amazon.nl", "amazon.se", "amazon.pl", "amazon.com.tr",
    "amazon.com.be", "amazon.ae", "amazon.sa", "amazon.sg",
})


@dataclass(frozen=True)
class PublicMusicCataloguePage:
    """Public-page metadata for a caller-supplied Amazon Music link."""

    marketplace: str
    kind: str
    catalog_id: str
    title: str | None


class _PageTitle(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_title = False
        self._pieces = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self._pieces.append(data)

    @property
    def text(self):
        return "".join(self._pieces).strip() or None


def parse_public_music_url(
    url: str, *, expected_marketplace: str | None = None
) -> PublicMusicCataloguePage:
    """Allow only known regional Amazon Music links with explicit content IDs."""
    if not isinstance(url, str) or len(url) > 2048:
        raise ValueError("Invalid Amazon Music URL")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or not host.startswith("music.")
    ):
        raise ValueError("Expected an HTTPS Amazon Music catalogue URL")
    marketplace = host.removeprefix("music.")
    if marketplace not in _ALLOWED_MARKETPLACES:
        raise ValueError("Unsupported Amazon Music marketplace")
    if expected_marketplace and expected_marketplace != marketplace:
        raise ValueError("Amazon Music URL does not match account marketplace")
    segments = parsed.path.strip("/").split("/")
    if len(segments) < 2 or segments[0] not in ("artists", "albums"):
        raise ValueError("Expected an artist or album catalogue page")
    ident = segments[1].upper()
    if not _ID_RE.fullmatch(ident):
        raise ValueError("Amazon Music URL has no valid catalogue ID")
    if parsed.query and segments[0] == "albums":
        from urllib.parse import parse_qs

        track = parse_qs(parsed.query).get("trackAsin")
        if track:
            track_id = track[0].upper()
            if not _ID_RE.fullmatch(track_id):
                raise ValueError("Invalid Amazon Music track catalogue ID")
            return PublicMusicCataloguePage(marketplace, "track", track_id, None)
    return PublicMusicCataloguePage(
        marketplace, "artist" if segments[0] == "artists" else "album", ident, None
    )


async def read_public_music_page(
    session: ClientSession,
    url: str,
    *,
    expected_marketplace: str | None = None,
) -> PublicMusicCataloguePage:
    """Read a caller-supplied public music page; never send login credentials."""
    page = parse_public_music_url(url, expected_marketplace=expected_marketplace)
    # No redirects: prevents cross-origin redirects and SSRF through an allowed host.
    # No cookies or Alexa authentication headers are supplied.
    async with session.get(
        url, allow_redirects=False, headers={"Accept": "text/html"}
    ) as response:
        if response.status != 200:
            raise ValueError("Public Amazon Music page was unavailable")
        if "text/html" not in response.headers.get("Content-Type", ""):
            raise ValueError("Amazon Music returned non-HTML content")
        if response.content_length and response.content_length > 2_000_000:
            raise ValueError("Amazon Music page exceeds safe size limit")
        content = await response.content.read(2_000_001)
        if len(content) > 2_000_000:
            raise ValueError("Amazon Music page exceeds safe size limit")
    title_parser = _PageTitle()
    title_parser.feed(content.decode("utf-8", errors="replace"))
    return PublicMusicCataloguePage(
        page.marketplace, page.kind, page.catalog_id, title_parser.text
    )



@dataclass(frozen=True)
class PublicMusicSearchCandidate:
    """An observed catalogue link on a public results page."""

    name: str
    kind: str
    catalog_id: str
    url: str
    exact_name_match: bool


class _PublicSearchLinks(HTMLParser):
    """Collect anchor URLs and visible labels from public HTML only."""

    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._chunks = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._chunks = []

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join(self._chunks).strip()))
            self._href = None
            self._chunks = []

    def handle_data(self, data):
        if self._href:
            self._chunks.append(data.strip())


def extract_public_music_search_candidates(
    html: str, *, marketplace: str, query: str
) -> list[PublicMusicSearchCandidate]:
    """Accept only named same-marketplace artist/album/track catalogue links.

    Some Amazon pages may render search results only via JavaScript. In that
    case this intentionally returns [] instead of inventing a result.
    """
    if marketplace not in _ALLOWED_MARKETPLACES:
        raise ValueError("Unsupported Amazon Music marketplace")
    parser = _PublicSearchLinks()
    parser.feed(html)
    candidates = []
    seen = set()
    root = f"https://music.{marketplace}"
    for href, label in parser.links:
        if not isinstance(href, str) or not label:
            continue
        candidate_url = urljoin(root, href)
        try:
            item = parse_public_music_url(
                candidate_url, expected_marketplace=marketplace
            )
        except (ValueError, TypeError):
            continue
        key = (item.kind, item.catalog_id)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            PublicMusicSearchCandidate(
                name=label,
                kind=item.kind,
                catalog_id=item.catalog_id,
                url=candidate_url,
                exact_name_match=label.strip().casefold() == query.strip().casefold(),
            )
        )
    return sorted(candidates, key=lambda item: (not item.exact_name_match, item.kind))


async def probe_public_music_search(
    session: ClientSession,
    *,
    marketplace: str,
    query: str,
) -> list[PublicMusicSearchCandidate]:
    """Probe public search HTML with no authentication or playback.

    This is experimental: '/search/<name>' is NOT a verified, stable
    anonymous search API. Empty results mean unavailable/JS-only/unsupported
    search markup, not that the artist or track doesn't exist.
    """
    if marketplace not in _ALLOWED_MARKETPLACES:
        raise ValueError("Unsupported Amazon Music marketplace")
    if not isinstance(query, str) or not query.strip() or len(query) > 200:
        raise ValueError("Search text must be between 1 and 200 characters")
    url = f"https://music.{marketplace}/search/{quote(query.strip(), safe='')}"
    async with session.get(
        url, allow_redirects=False, headers={"Accept": "text/html"}
    ) as response:
        if response.status != 200:
            return []
        if "text/html" not in response.headers.get("Content-Type", ""):
            return []
        if response.content_length and response.content_length > 2_000_000:
            return []
        content = await response.content.read(2_000_001)
        if len(content) > 2_000_000:
            return []
    return extract_public_music_search_candidates(
        content.decode("utf-8", errors="replace"),
        marketplace=marketplace,
        query=query,
    )
