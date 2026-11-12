# Amazon Music search: existing AlexaPy session diagnostic (v4)

Research branch only. **Do not merge into PR #3687**: the tested native-alarm
implementation is separate from this experimental music-catalogue resolver.

## Goal

Resolve a plain artist/album/track name from `alexa_media.create_alarm` user
input (e.g. `music_entity: Enya`, `music_provider: Amazon Music`) without
requiring an Amazon Music URL, asking for browser credentials, starting music
playback, or creating any intermediary Alexa alarm.

The eventual native Alexa alarm needs a **UUID-shaped `musicAlarmId`**.
Amazon Music catalogue IDs such as `B001ED54MQ` are **not** musicAlarmIds.
Catalogue search is a prerequisite investigation, not a complete resolver.

## Evidence from user's UK browser and Home Assistant tests

1. Public `GET https://music.amazon.co.uk/search/Enya`: HTTP 200 with
   approximately 11,468 bytes of HTML, but 0 anchors, no parseable catalogue
   results, and no identified embedded catalogue markers. Browser displays
   results after JavaScript loads.
2. User-supplied browser HAR showed
   `POST https://gql.music.amazon.co.uk/` operation `SpecSearchPage`.
   Browser's authenticated GraphQL search returned HTTP 200 and artist,
   album, and song groups; `GetSearchSuggestions` was also observed.
   This capture is **not** stored in GitHub and neither are its sensitive
   headers or cookies.
3. Experimental v3.1 anonymous GraphQL `SpecSearchPage` probe:
   HTTP **401**, content type `application/json`; no candidates.
4. Experimental v4 reused the already authenticated `login_obj.session`
   (aiohttp/ AlexaPy) and normal cookie-domain routing. User-reported response:
   - Marketplace `amazon.co.uk`; query `Enya`
   - HTTP **401**, `application/json`
   - `applicable_cookie_count: 12`
   - `outcome: http_error_or_non_json`; no candidates
   - No reported GraphQL error codes (response body intentionally not
     surfaced on HTTP 401).

**Interpretation:** 12 applicable cookies in the AlexaPy jar do **not** establish
that Amazon Music recognises or authorises the session; the v4 request was
rejected. A 401 also does not tell us which required browser request parameters
are missing. Do not conclude the catalogue lacks Enya or that any subscription
is absent. An authenticated browser request can carry API keys, CSRF tokens
and other headers that v4 intentionally does not reproduce.

## Implementation on this branch

- `amazon_music_graphql.py` contains the anonymous probe plus
  `probe_existing_alexa_session`, which posts a read-only `SpecSearchPage`
  request through the existing aiohttp session.
- The `alexa_media.search_music_catalog` diagnostic reports the HTTP status,
  operation, response MIME type, outcome, **count only** of applicable cookies,
  and parsed catalogue candidates where authorised.
- No raw cookies, browser API keys, CSRF tokens, login secrets, HTTP response
  bodies or full HAR dumps are logged, returned, stored or committed.
- No playback, alarm creation, or permanent music-ID storage. This service
  is for diagnosis only.
- The GraphQL persisted-query hash and payload are **experimental website
  internals**, not a documented supported public API and may change.
- v4 was tested live in the user's Home Assistant and returned HTTP 401.
  Offline parsing tests are included; a full Home Assistant regression suite
  has **not** been verified for the research branch.

## Known stumbling block and recommended next investigation

The working browser search and rejected AlexaPy request must be compared
at the **request-structure and authentication-mechanism** level: operation
variables, header *names* and documented auth requirements; never copy or
publish live browser cookies, authorization values, CSRF secrets or HAR
captures. Check whether AlexaPy exposes a legitimately reusable supported
Amazon Music identity, or whether catalogue search requires a distinct
Amazon Music website session / approved partner API.

If the website GraphQL service requires separate browser/partner credentials
that AlexaPy does not support, stop rather than add credential hacks. Prefer
a documented supported catalogue API or retain the existing notification-cache
approach for already-known native alarm assets.

Even after a catalogue lookup works, **catalogue ASIN -> native musicAlarmId
UUID resolution remains completely unverified**. Keep this distinction explicit.

## Reproduce diagnostic

```yaml
action: alexa_media.search_music_catalog
data:
  entity_id: media_player.bedroom_echo
  query: Enya
```

Expected result from the UK v4 test (actual observed values, not guaranteed
for other accounts):

```yaml
marketplace: amazon.co.uk
query: Enya
diagnostics:
  transport: existing_alexapy_session
  operation: SpecSearchPage
  http_status: 401
  content_type: application/json
  outcome: http_error_or_non_json
  applicable_cookie_count: 12
  error_count: 0
  error_codes: []
candidates: []
```
