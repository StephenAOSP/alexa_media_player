"""Offline custom-command payload comparison. No Alexa API or network access."""

from __future__ import annotations


def build_preview(command: str, suppress_response: bool = True) -> dict:
    """Return a proposed payload delta, not a verified Amazon request.

    AlexaPy 1.34.0's actual serialization is not yet confirmed.
    The proposed field is intentionally not passed to any network transport.
    """
    if not isinstance(command, str) or not command.strip():
        raise ValueError("command must be nonempty")
    command = command.strip()
    baseline = {"type": "Alexa.TextCommand", "operationPayload": {"text": command}}
    candidate = {
        "type": "Alexa.TextCommand",
        "operationPayload": {
            "text": command,
            **({"suppressResponse": True} if suppress_response else {}),
        },
    }
    return {
        "mode": "offline_only",
        "amazon_request_sent": False,
        "alexa_py_target": "1.34.0",
        "schema_verified": False,
        "baseline": baseline,
        "candidate": candidate,
        "warning": (
            "Experimental hypothesis only. No evidence that Amazon accepts "
            "suppressResponse or that it silences confirmations."
        ),
    }
