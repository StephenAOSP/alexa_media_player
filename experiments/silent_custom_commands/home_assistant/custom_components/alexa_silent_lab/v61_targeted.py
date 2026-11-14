"""V6.1 targeted static diagnostic. Never invokes Alexa APIs."""
from __future__ import annotations
import ast
import inspect
import importlib.metadata
import textwrap

NAMES = ("run_custom", "send_sequence", "run_routine", "run_behavior")
TERMS = ("brief", "response", "suppress", "silent", "ack", "speak", "sound", "utterance")
CALLS = ("send_sequence", "run_behavior", "run_custom", "_post_request", "run_routine")

def _analyse(name, method):
    tree = ast.parse(textwrap.dedent(inspect.getsource(method)))
    literals = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    mentions = {}
    for term in TERMS:
        matching = [s for s in literals if term in s.lower()]
        if matching:
            mentions[term] = {
                "literal_count": len(matching),
                "exact_term_only": all(s.lower() == term for s in matching),
                "contains_longer_string": any(s.lower() != term for s in matching),
                "likely_false_positive": term == "brief" and all(s.lower() != "brief" for s in matching),
            }
    calls = sorted({n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in CALLS})
    return {
        "parameters": list(inspect.signature(method).parameters),
        "literal_term_matches": mentions,
        "call_targets": calls,
        "known_operation_types": sorted({s for s in literals if s.startswith("Alexa.") and len(s) < 100})[:20],
        "uses_extra_parameter": any(isinstance(n, ast.Name) and n.id == "extra" for n in ast.walk(tree)),
        "forwards_extra_to_call": any(
            isinstance(n, ast.keyword) and (
                (n.arg == "extra" and isinstance(n.value, ast.Name) and n.value.id == "extra") or
                (n.arg is None and isinstance(n.value, ast.Name) and n.value.id == "extra")
            ) for n in ast.walk(tree)
        ),
        "calls_behavior_preview": "/api/behaviors/preview" in literals,
        "returns_request_result": any(isinstance(n, ast.Return) and n.value is not None for n in ast.walk(tree)),
    }

def inspect_v61():
    from alexapy.alexaapi import AlexaAPI
    methods = {}
    for name in NAMES:
        method = getattr(AlexaAPI, name, None)
        if method is None:
            methods[name] = {"found": False}
            continue
        try:
            methods[name] = {"found": True, **_analyse(name, method)}
        except (OSError, TypeError, ValueError, SyntaxError) as exc:
            methods[name] = {"found": True, "inspection_error": type(exc).__name__}
    try:
        version = importlib.metadata.version("alexapy")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    return {
        "mode": "v6_1_read_only_targeted_inspection",
        "amazon_request_sent": False,
        "alexa_py_version": version,
        "methods": methods,
        "interpretation_limit": "Static Python analysis only; cannot prove Amazon supports silent command execution or beep suppression.",
        "privacy": "No method bodies, arbitrary literals, account identifiers or credentials returned.",
    }
