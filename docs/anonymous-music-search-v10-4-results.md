# Amazon Music anonymous catalogue search — v10.4 success (12 November 2026)

This is experimental research only. Do not merge into native alarm PR #3687.

## Observed Home Assistant results

- `mode: anonymous_only`; no Alexa login, Alexa cookies, or browser credentials used.
- `POST https://music.amazon.co.uk/config.json?skipToken=false&clientApplication=skyfire` -> HTTP 200 JSON, anonymous CSRF object present; no access token.
- `POST https://eu.web.skill.music.a2z.com/api/showSearch` -> HTTP 200 `application/json` with a `methods` object.
- The anonymous search for **Enya** returned **13 parsed candidates** including:
  - `Enya` — `B001ED54MQ` (known artist link).
  - `The Very Best of Enya` — `B002X3XFYA`.
  - `Enya` — `B0942PN668` (another same-name result; type/rank not yet returned).
- No playback, speech, volume change, or alarm writes.
- v10.1–v10.3 successfully reached HTTP 200 but failed to decode JSON because the response reader used only one `aiohttp.content.read(n)` call. This may return fewer than `n` bytes, leaving a truncated JSON string. v10.4 reads the complete stream in chunks with a size limit before decoding. Search response then decoded successfully.

## Engineering follow-up

1. Preserve result **type** (artist, album, track) and original result **rank/order** rather than matching names alone. There are two exact-name `Enya` results, so guessing solely by name is unsafe. Consider requiring a caller to select when ambiguity remains.
2. Add isolated unit tests for chunked JSON reads, search-response parsing, and duplicate-name candidate selection. No further live request is required to implement these tests.
3. Do not mistake catalogue ASINs for Alexa native `musicAlarmId` UUIDs. The catalogue-search problem is solved experimentally; a **silent catalogue-selection -> new music-alarm UUID** route has not been demonstrated.
4. Treat the web-player API as undocumented/fragile. Never upload HAR files, session tokens, cookies, or raw responses. Preserve the user's strict no-playback/no-speech constraint.

Source: user-reported YAML output for `alexa_music_id_compare.probe_music_web_v104`.
