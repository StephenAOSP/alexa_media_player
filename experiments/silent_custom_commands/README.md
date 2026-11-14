# Silent custom Alexa commands — independent research branch

**Status: inspection-only scaffold.** No response-suppression capability has been verified, and nothing in this branch executes Alexa commands or changes Home Assistant runtime behaviour.

This branch was created from `StephenAOSP/alexa_media_player:dev`, independently of PR #3687 (`feature/native-music-alarms`). Do not merge the music-alarm branch into this experiment.

## Inspect AlexaPy locally

From the repository root, use a disposable Python environment with AlexaPy 1.35.0 installed:

```bash
python -m venv .venv-silent
source .venv-silent/bin/activate
python -m pip install alexapy==1.35.0
python experiments/silent_custom_commands/inspect_alexapy.py
python experiments/silent_custom_commands/audit_alexapy.py
python -m unittest discover -s experiments/silent_custom_commands/tests -v
```

On Windows, activate with `.venv-silent\\Scripts\\activate`. The inspector reads locally installed AlexaPy source and prints the methods `run_custom`, `send_sequence`, and `run_behavior`. It does not send any requests or execute commands.

## Next steps (not yet implemented)

1. **Ready for local verification:** run `audit_alexapy.py` to inventory call sites and forwarding keywords in the installed AlexaPy 1.35.0 source. This is static analysis only; it does not prove how Amazon interprets any field. Share only the sanitized audit output (review it before posting).
2. **Pending:** after inspecting the exact 1.35.0 source, add version-specific transport-mocked tests to determine whether a candidate flag reaches the behaviour request, without contacting Amazon.
3. Only after a candidate is justified, manually test it on an idle test Echo, one variation at a time.
4. Verify that the action succeeds, no voice or tone is produced, no unwanted playback occurs, volume is unchanged, and any temporary alarm is removed.

**Do not treat HTTP 200 as evidence of silence.** Do not collect or share cookies, authentication headers, customer IDs, or device serial numbers. Do not test during sleep or against a production alarm.

The suggested Home Assistant `extra.suppress_response: true` interface is only a hypothesis, **not a supported feature**. No mute, DND, or volume-zero workaround will be considered acceptable.
