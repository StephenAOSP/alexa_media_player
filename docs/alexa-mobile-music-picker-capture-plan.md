# Read-only investigation: Alexa app music-alarm picker (UK)

Date: 2026-11-12. Independent research only; do not merge into PR #3687.

## Goal

Identify the **Alexa client-facing music-selection/search operation** that can
resolve an artist name such as Enya for a native alarm **without** executing a
playback/text/voice action, speech, muting, or changing an alarm.

## Findings from source checking

- Amazon's legacy Alexa browser management portal stopped functioning on
  **13 October 2023**. The separate Alexa+ web interface is not confirmed to
  expose the old alarm editor.
  https://www.amazonforum.com/s/question/0D56Q0000CPKn7RSQT/alexa-web-site
- Amazon directs users to the phone Alexa app's **More > Alarms & Timers**
  interface. The music option appears in existing music alarms.
  https://www.amazonforum.com/s/question/0D56Q0000DDZYEjSQP/alarm-song-wont-change
- The AlexaPy authenticated `GET /api/notifications` response from a real Enya
  alarm exposes `musicAlarmId`, `musicEntity`, `provider`, `sound`; no
  separate catalogue identifier in the tested fields.
- AlexaPy `AlexaAPI.play_music` executes `Alexa.Music.PlaySearchPhrase`
  via `POST /api/behaviors/preview`; calling it triggers playback, and is
  unsuitable for strict silent requirements.
- The search resolver `Alexa.Media.Search.GetPlayableContent` documented
  for music skills is **provider-facing**, not a verified Alexa-account HTTP
  operation. Do not mistake provider `contentId` for `musicAlarmId`.

## Test with no account-network capture

1. Open the Alexa **mobile app**.
2. Go to **More > Alarms & Timers** and select the existing Enya alarm.
3. Tap **Music** (wording may vary) and observe the artist/music selector.
4. **Do not save** the alarm or initiate playback.
5. Record only screenshots of the non-sensitive picker screen, and report:
   - iPhone or Android;
   - whether there is a search box;
   - whether Amazon Music is listed as a provider;
   - whether the artist result shows Enya before selection;
   - whether choosing Enya changes the visible selected item immediately
     or only after a Save action.
6. Avoid sharing screen captures with account emails, profiles, device serials,
   phone notifications, or private playlists.

This test identifies the interface, **not the HTTP endpoint**. It is
low friction and does not require a proxy or TLS interception.

## Optional advanced network capture (not required)

Only if the user already has a safe, consented debugging environment capable
of observing the Alexa mobile app's HTTPS requests, collect a **local**
request/response summary. Native app traffic is not captured by Chrome DevTools
for an ordinary website; TLS pinning may prevent observation entirely.

Whitelist *only*:
- request method;
- host;
- endpoint path **with identifier segments replaced by `<id>`**;
- HTTP status;
- GraphQL `operationName` if present;
- request **JSON field names**, not their values;
- response **JSON field names/types**, not their values.

Never export or upload raw HAR, request headers, bodies, cookies, bearer tokens,
CSRF, device serials, account IDs, query string values, or authenticated URLs.
Do not modify app binaries, bypass TLS pinning, or replay write requests for
this investigation.

## Decision criteria

A useful candidate must be an independently callable operation that:
- accepts text/provider or resolves a selected artist;
- returns **non-playing** selection metadata;
- can be authorized by the already-connected AlexaPy session;
- does not itself play, speak, or modify alarms;
- produces enough data to create a music alarm silently via existing alarm
  creation API.

Until all are demonstrated, preserve stock v5.20.0 and PR #3687 unchanged.
