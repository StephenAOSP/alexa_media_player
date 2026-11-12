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

## Current blocker

Amazon's Music Web API remains closed beta / partner access at the time of research. An ordinary Alexa login session does **not** imply eligibility to call the Music Web API. Never use Alexa account OAuth tokens or cookies as substitute Music API credentials or publish those secrets.

Even an authorized catalogue search returning Enya's UK artist ASIN `B001ED54MQ` will not by itself provide the `musicAlarmId` UUID required for native Alexa alarms. Do not form `MUSIC-B001ED54MQ`, guess an ID, or start playback to discover one.

## Recommended next investigation

Find and verify a silent, authorized method that maps Amazon Music catalogue selections to an Alexa native music-alarm identifier. Only wire automatic alarm creation once the mapping is proven. Keep the existing PR #3687 unchanged.

References:

- https://developer.amazon.com/docs/music/API_web_search.html
- https://developer.amazon.com/docs/music/API_web_schema.html
