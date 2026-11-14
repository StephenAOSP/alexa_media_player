# Alexa Silent Lab — first isolated Home Assistant test

This is a **separate custom integration**, not a Home Assistant add-on and not
a replacement for Alexa Media Player. It registers the domain
`alexa_silent_lab` and an **offline-only** service. It has no Alexa login,
no AlexaPy dependency, and no network transport.

## Install alongside existing Alexa Media Player

1. Download the `alexa_silent_lab` folder from
   `experiments/silent_custom_commands/home_assistant/custom_components/`
   in the `feature/silent-custom-commands` branch.
2. Copy that **whole folder** to
   `/config/custom_components/alexa_silent_lab/` on Home Assistant.
   Your existing `/config/custom_components/alexa_media/` stays untouched.
3. In `/config/configuration.yaml`, add a top-level entry:

   ```yaml
   alexa_silent_lab:
   ```

   If it already exists, do not add a duplicate.
4. Restart Home Assistant.
5. Open **Developer Tools → Actions** (or **Services** in older versions).
   Select `alexa_silent_lab.preview_custom` and provide:

   ```yaml
   command: "Set an alarm for 1 a.m. and play Discover Weekly playlist on Spotify"
   suppress_response: true
   ```

6. Run the action and examine its response. The response must show
   `mode: offline_only`, `amazon_request_sent: false`, and
   `schema_verified: false`. No Echo should respond, since no request is sent.

**Do not** copy these files over `alexa_media`. Do not change your existing
Alexa Media Player integration or your alarms branch. Remove the
`alexa_silent_lab:` YAML entry and folder, then restart, to uninstall.

## Interpretation

The `suppressResponse` key is **only a hypothesis**, not a confirmed Amazon
parameter. The preview is a deliberately simplified comparison, **not** an
accurate reproduction of AlexaPy 1.34.0's wire format. This first test checks
safe integration installation, service response, and proposed payload delta.
It does **not** establish that silence is possible. The next test requires
inspection of AlexaPy 1.34.0 and transport-mocked serialization tests.

## Run offline unit tests (developer only)

```sh
python -m unittest discover -s experiments/silent_custom_commands/tests -p 'test_lab_preview.py' -v
```

## Version 0.3.0: opt-in live suppression candidate

This test targets only `media_player.living_room_echo` and reuses the already installed Alexa Media Player integration; it does **not** replace it. After copying the v0.3.0 lab files, restart Home Assistant and choose **Developer Tools → Actions → Alexa Silent Lab: Live experimental suppression candidate**:

```yaml
action: alexa_silent_lab.live_candidate
data:
  confirm_live_test: true
```

The candidate calls `media_player.play_media` with `media_content_type: custom`, the 8 a.m. ABBA Amazon Music alarm utterance, and `extra: {suppressResponse: true}`. The key is an **unverified experiment**, not an established Amazon or AlexaPy 1.34.0 feature. The service can fail, be ignored, or speak normally. A returned service response does not prove silence or successful alarm creation. Watch the Echo and verify alarms in the Alexa app. Running twice may create duplicate alarms. Remove test alarms afterwards. No DND or volume manipulation occurs.

A genuine silence result must be repeatable and checked against the baseline, and we must still inspect the exact AlexaPy 1.34.0 serialization before claiming support or proposing an upstream patch.
