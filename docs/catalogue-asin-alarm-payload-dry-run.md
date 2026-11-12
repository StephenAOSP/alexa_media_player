# Catalogue ASIN alarm-creation alternative — dry run (v10.7)

Date: 2026-11-12. **Research only**; do not merge into PR #3687.

## Confirmed

- Anonymous Amazon Music search via `POST /api/showSearch` returns ranked, typed catalogue hits. Enya's first ranked exact artist match is ASIN `B001ED54MQ`.
- The AMP native music alarm service currently passes `MUSIC-<existing native UUID>` as AlexaPy `create_alarm`'s `sound_id` argument.
- Enya's ASIN is not a native Alexa `musicAlarmId` UUID. The v10.6 selected-Echo cache contained no reusable Enya UUID.
- The Alexa alarm and notifications API is unofficial; no verified catalogue-ID-specific alarm creation payload has been identified.

## Alternative proposed

Instead of converting ASIN to UUID, investigate whether Alexa's alarm create endpoint can accept a catalogue-based representation. The two unverified candidate *AlexaPy arguments* are:

1. `sound_id="B001ED54MQ"` (unprefixed)
2. `sound_id="MUSIC-B001ED54MQ"` (music prefix)

The proven existing path uses `sound_id="MUSIC-<native UUID>"`. These are **hypotheses only**, not captured Amazon wire payloads, and should never be sent automatically. An additional structured `musicEntity/provider/catalogueId` payload might exist, but we have no evidence of its shape.

## v10.7 package

A local Home Assistant read-only service `alexa_music_id_compare.preview_music_alarm_payload_v107` uses the working anonymous search and returns both candidate `sound_id` strings with `verified_by_amazon: false`, `would_be_submitted: false`. The service **never calls AlexaPy or the Alexa alarm endpoint**, and creates no alarms, playback or speech. The integration maintains a single generic `music_probe.py` and retains earlier read-only services.

This is a **dry-run argument comparison**, *not proof that Amazon accepts either candidate*. The next meaningful evidence would be a safely sanitized capture of the Alexa app's music-alarm picker/create request, documenting its field names and types, or a verified validation capability. Do not upload raw HARs/cookies/tokens or experiment with real alarm writes without explicitly agreed conditions.
