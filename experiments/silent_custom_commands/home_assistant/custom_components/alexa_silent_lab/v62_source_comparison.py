"""V6.2: offline comparison of publicly documented Alexa command implementations."""
from __future__ import annotations
import ast
import inspect
import textwrap

def inspect_v62():
    from alexapy.alexaapi import AlexaAPI
    names = ("run_custom", "send_sequence", "run_behavior", "run_routine")
    observed = {}
    for name in names:
        method = getattr(AlexaAPI, name, None)
        if method is None:
            observed[name] = {"available": False}
            continue
        try:
            tree = ast.parse(textwrap.dedent(inspect.getsource(method)))
            constants = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            observed[name] = {
                "available": True,
                "operation_identifiers": sorted(set(s for s in constants if s.startswith("Alexa.") and len(s) < 100)),
                "mentions_llm_custom_text_command": any("Alexa.LLM.CustomTextCommand" in s for s in constants),
                "mentions_customtextcommand_skill": any("amzn1.ask.1p.customtextcommand" in s for s in constants),
                "mentions_suppression_flag": any(any(x in s.lower() for x in ("suppressresponse", "suppress_response", "suppressconfirmation", "suppress_confirmation")) for s in constants),
                "uses_behavior_preview": any("/api/behaviors/preview" in s for s in constants),
            }
        except (OSError, ValueError, TypeError, SyntaxError) as exc:
            observed[name] = {"available": True, "inspection_error": type(exc).__name__}
    return {
        "mode": "v6_2_offline_source_comparison",
        "amazon_request_sent": False,
        "installed_alexapy": observed,
        "external_source_findings": [
            {"project": "jonwilliams84/cli-anything-alexa", "language": "Python", "command_path": "AlexaPy literal text command", "speech_result": "Project documents Alexa answering aloud", "general_silent_command_proven": False, "url": "https://github.com/jonwilliams84/cli-anything-alexa"},
            {"project": "paoloantinori/ha-alexa-actions-smapi", "language": "Python", "command_path": "Custom skill via SkillConnections.Launch", "speech_result": "suppress_confirmation controls skill's post-response Okay, not built-in Alexa acknowledgements", "general_silent_command_proven": False, "url": "https://github.com/paoloantinori/ha-alexa-actions-smapi"},
            {"project": "thorsten-gehrig/alexa-remote-control", "language": "Shell", "command_path": "Amazon textcommand via unofficial API", "speech_result": "No verified universal speech-and-beep suppression", "general_silent_command_proven": False, "url": "https://github.com/thorsten-gehrig/alexa-remote-control"}
        ],
        "candidate_llm_operation": {"operation": "Alexa.LLM.CustomTextCommand", "skill_id": "amzn1.ask.1p.customtextcommand", "account": "standard Alexa", "compatible": "unknown; not tested", "silence_supported": "unknown"},
        "conclusion": "No reusable general silent natural-language Alexa command implementation verified. No routines, login, or network requests used.",
        "privacy": "No source bodies, tokens, cookies, identifiers or user command data returned."
    }
