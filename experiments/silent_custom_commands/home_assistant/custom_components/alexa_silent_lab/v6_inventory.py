"""V6: read-only inventory of installed AlexaPy command/behaviour pathways."""
from __future__ import annotations
import ast
import inspect
import importlib.metadata
import textwrap

KEYWORDS = ("command", "routine", "behavior", "sequence", "skill", "speech", "speak", "sound", "response", "silent", "brief", "ack", "volume")
TERMS = ("suppress", "silent", "brief", "acknowledg", "response", "Alexa.TextCommand", "Alexa.LLM.CustomTextCommand")

def inventory():
    from alexapy.alexaapi import AlexaAPI
    methods = {}
    for name in sorted(dir(AlexaAPI)):
        if name.startswith("_") or not any(k in name.lower() for k in KEYWORDS):
            continue
        fn = getattr(AlexaAPI, name, None)
        if not callable(fn):
            continue
        try:
            signature = inspect.signature(fn)
            params = list(signature.parameters)
            source = textwrap.dedent(inspect.getsource(fn))
            tree = ast.parse(source)
            string_literals = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            # Only report known, non-sensitive operation identifiers.
            operations = sorted({s for s in string_literals if s.startswith(("Alexa.", "AlexaRoutines.")) and len(s) < 100})[:35]
            references = sorted({term for term in TERMS if term.lower() in source.lower()})
            calls = sorted({n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("send_sequence", "run_behavior", "run_custom", "_post_request", "run_routine", "run_skill")})
            methods[name] = {"parameters":params, "operation_types":operations, "terms_present":references, "calls":calls}
        except (OSError, ValueError, TypeError, SyntaxError) as exc:
            methods[name] = {"inspection_error":type(exc).__name__}
    try:
        version = importlib.metadata.version("alexapy")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    return {
        "mode":"v6_read_only_method_inventory",
        "amazon_request_sent":False,
        "alexa_py_version":version,
        "methods":methods,
        "conclusion":"Inventory only. A matching term does not establish working command-level acknowledgement suppression.",
        "privacy":"No credentials, device identifiers, arbitrary string literals or method bodies returned.",
    }
