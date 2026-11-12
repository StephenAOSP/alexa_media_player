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
