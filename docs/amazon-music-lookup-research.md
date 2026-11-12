# Amazon Music name lookup research (experimental)

## User interface

The desired alarm action stays unchanged:

```yaml
action: alexa_media.create_alarm
data:
  entity_id: media_player.bedroom_echo
  time: "08:15:00"
  days: tomorrow
  alarm_type: music
  music_provider: Amazon Music
  music_entity: Enya
```

The user should not need an Amazon Music URL.

## What is implemented

- `amazon_music_catalog.py` implements a read-only HTTP client for the documented Amazon Music partner Web API v1 `POST /v1/search/artists`, `/albums`, and `/tracks` endpoints.
- It parses `data.searchArtists.edges[].node.name/id`, and `searchAlbums`/`searchTracks` nodes using `title/id`.
- The client requires an explicitly supplied authorized HTTPS API base URL, partner API key, and Music API bearer token.
- Queries do not initiate playback. The module returns catalogue candidates, **not** Alexa native alarm IDs.
- `services.py` already selects Amazon domain from the Alexa account and supports reusing a verified `musicAlarmId` from existing alarms.
- The new client is **not yet wired to a Home Assistant service**; credentials and a verified catalogue-to-alarm-ID resolver are unavailable.

## Experimental public name-search probe

The research branch now exposes a read-only Home Assistant response action:

```yaml
action: alexa_media.search_music_catalog
data:
  entity_id: media_player.bedroom_echo
  query: Enya
```

The action derives `amazon.co.uk` or another regional Amazon marketplace from the logged-in Alexa account. It requests a public `https://music.<marketplace>/search/<query>` HTML page **without Alexa cookies, Amazon Music API tokens, or playback**. It accepts only visible named links to known artist/album/track catalogue pages on that same marketplace. Empty results can mean JavaScript-rendered results, a redirect, an unavailable page, a different search URL scheme, or lack of content; they are **not** evidence that an artist is absent.

**Important:** This URL shape is an experimental probe, not a verified Amazon public search API. Public named artist pages have been independently observed, but unauthenticated name-search results could not yet be verified. This action is deliberately NOT wired to `create_alarm` and does not return a native Alexa `musicAlarmId`.

The public page inspector can separately extract an ASIN from known artist or album URLs. Neither probe supplies the missing ASIN-to-native-alarm-UUID mapping.

## Current blocker

Amazon's Music Web API remains closed beta / partner access at the time of research. An ordinary Alexa login session does **not** imply eligibility to call the Music Web API. Never use Alexa account OAuth tokens or cookies as substitute Music API credentials or publish those secrets.

Even an authorized catalogue search returning Enya's UK artist ASIN `B001ED54MQ` will not by itself provide the `musicAlarmId` UUID required for native Alexa alarms. Do not form `MUSIC-B001ED54MQ`, guess an ID, or start playback to discover one.

## Recommended next investigation

Find and verify a silent, authorized method that maps Amazon Music catalogue selections to an Alexa native music-alarm identifier. Only wire automatic alarm creation once the mapping is proven. Keep the existing PR #3687 unchanged.

References:

- https://developer.amazon.com/docs/music/API_web_search.html
- https://developer.amazon.com/docs/music/API_web_schema.html
