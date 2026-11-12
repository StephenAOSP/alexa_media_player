# Silent creation of native music alarms: investigation (12 November 2026)

This is a research note only. Do **not** merge into the native music alarm PR
[#3687](https://github.com/alandtse/alexa_media_player/pull/3687).

## Hard requirement

Creating the alarm must be **silent**: no Alexa voice confirmation, no music
playback, no chime, no temporary volume change. Music should play only when the
scheduled alarm rings. The user should provide only an artist/album/track name.

## Evidence

- Stock AMP v5.20.0 calls `AlexaAPI.create_alarm` for regular alarms. The
  research PR passes a `MUSIC-<musicAlarmId>` sound selection when it already
  knows a native ID; it does not resolve arbitrary artist names to new IDs.
- Read-only HA cached notification comparison of **three manually created**
  Enya / Amazon Music alarms on the bedroom Echo: three alarms, all UUID-shaped
  `musicAlarmId`, and **three distinct IDs** (comparison groups A/B/C).
  Time slots 2026-11-12 15:00 and 2026-11-13 08:00 / 09:00.
  This disproves the proposed assumption of one reusable UUID for every Enya
  selection in those records. It does NOT conclusively establish the lifecycle
  or semantic meaning of `musicAlarmId`, or whether the same ID is reused on
  editing an individual alarm.
- AlexaPy's behaviours API supports `run_custom(text)`, which dispatches an
  `Alexa.TextCommand` behaviour, and `play_music(provider, phrase)`, which
  dispatches `Alexa.Music.PlaySearchPhrase`. The latter initiates music.
  Alexa text commands may generate speech; their silence is **not guaranteed**.
  Therefore neither path satisfies the strict silent requirement as currently
  demonstrated.
- The alarm-creation REST pathway is inherently different from Alexa's
  conversational intent processing: an ordinary create-alarm request accepts
  an alarm sound selection, not a free-form artist to resolve.
- A voice request apparently resolves a music intent and creates the alarm;
  no independently callable silent intent-resolution endpoint has been
  verified.

## Working hypothesis, NOT established fact

The per-alarm UUIDs suggest that `musicAlarmId` may represent a generated
alarm-specific music selection instance rather than an artist catalogue ID.
The creation path may involve Amazon server-side music-alarm intent resolution
or an application-specific music-picker API. That operation has not yet been
identified, and it should not be guessed from artist ASINs.

## Next research approach

1. Retain stock AMP locally. Keep the three existing Enya alarms available
   for read-only metadata analysis and do not send `Alexa.TextCommand` in a
   production integration.
2. Research the **music picker / alarm save** transactions in Alexa's first
   party app; use a redacted capture of an interactive *manual music alarm
   selection*, rather than browser Amazon Music catalogue search or voice
   request, if technically feasible and consented. Never upload raw HARs,
   cookies, tokens, full account identifiers or private request headers.
3. Compare a single alarm's ID before and after an **edit of time only**, using
   an irreversible fingerprint stable across both runs; avoid writing or
   persisting any raw music IDs. This helps distinguish per-alarm from per-save
   IDs, but does not itself yield a resolver.
4. Only implement a new route after identifying and verifying a silent,
   authenticated, read-only music-selector operation followed by the existing
   silent alarm-save method. Confirm no playback, speech or volume changes in
   a real device test.

## Conclusion

**No verified silent artist-name -> new native musicAlarmId mechanism exists in
the examined AlexaPy APIs.** Voice-equivalent text commands are known, but
cannot be assumed silent. Do not merge speculative or audible behaviour into
PR #3687.


## Further source tracing: Alexa behaviours vs provider music search (12 November 2026)

Verified from AlexaPy `alexapy/alexaapi.py`:

- `play_music(provider_id, search_phrase)` delegates to
  `send_sequence("Alexa.Music.PlaySearchPhrase", searchPhrase=...,
  sanitizedSearchPhrase=..., musicProviderId=...)`.
- `send_sequence` wraps this in an Alexa behaviours operation and
  `run_behavior` POSTs to `/api/behaviors/preview` on the regional Alexa web
  host (UK: `alexa.amazon.co.uk`).
- That is an **execution** endpoint. Neither `play_music` nor
  `run_behavior` returns a resolved music content ID to the caller.
  Trying `PlaySearchPhrase` even once would initiate playback, violating
  the strict no-audio requirement. We did **not** send such a command.
- Inspecting Python alone cannot disclose Alexa's private downstream provider
  calls or the source of its internal music search results.

**New documented architecture:** Amazon's Alexa Music, Radio, and Podcast Skill
API exposes `Alexa.Media.Search.GetPlayableContent`, which Alexa sends
**to a music provider's skill**, with resolved selection criteria; the
provider returns a `contentId`. Amazon documents saving that `contentId`
for a music alarm and subsequently sending `Alexa.Media.Playback.Initiate`
when the alarm fires. Sources:

- https://developer.amazon.com/en-US/docs/alexa/device-apis/alexa-media-search.html
- https://developer.amazon.com/en-US/docs/alexa/music-skills/understand-content-id.html
- https://developer.amazon.com/en-US/docs/alexa/device-apis/alexa-media-playback.html

**Important caveats:** This is a provider-facing service contract, NOT an
account-facing method in AlexaPy, and there is no verified authenticated
request that HA can send to invoke `GetPlayableContent` for Amazon Music.
The provider `contentId` is NOT proven identical to Alexa notification
`musicAlarmId`. In fact, Amazon requires content IDs to be persistent for
the same content, whereas the three manually created Enya alarms had three
distinct `musicAlarmId` UUIDs: the two identifiers may represent different
layers.

**Concrete next evidence to seek without audio:** Capture only endpoint
paths, operation names, safe JSON field *names*, and redacted response schema
when opening the Alexa app's music-alarm picker or selecting an artist.
The likely bridge is the Alexa **client-facing** music-selection endpoint
that requests a provider resolution and produces an alarm-specific music
selection, not `Alexa.Media.Search` (which is provider-facing).
Never upload raw HARs/auth headers/cookies/account IDs. No production-code
changes or live playback tests justified yet.
