"""Read-only AST inspection of installed AlexaPy command serialization."""
from __future__ import annotations
import ast
import inspect
import textwrap
import importlib.metadata

METHODS = ("run_custom", "send_sequence", "run_behavior")
SAFE_LITERALS = {
    "Alexa.TextCommand", "/api/behaviors/preview", "operationPayload",
    "customerId", "type", "text", "suppressResponse", "suppress_response",
    "sequence", "nodesToExecute", "behaviorId", "sequenceJson",
}

class RedactLiterals(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value not in SAFE_LITERALS:
            return ast.copy_location(ast.Constant(value="<redacted string>"), node)
        return node

def inspect_request_builders():
    """Never calls Amazon, reads only installed method source code."""
    from alexapy.alexaapi import AlexaAPI
    result = {}
    for name in METHODS:
        method = getattr(AlexaAPI, name, None)
        if method is None:
            result[name] = {"found": False}
            continue
        try:
            source = textwrap.dedent(inspect.getsource(method))
            tree = ast.parse(source)
            fn = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
            # Remove docstring; do not include comments, local paths or runtime values.
            fn.decorator_list = []
            if fn.body and isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant) and isinstance(fn.body[0].value.value, str):
                fn.body.pop(0)
            safe = RedactLiterals().visit(fn)
            ast.fix_missing_locations(safe)
            snippet = ast.unparse(safe)
            # Bound response size; never expose complete arbitrary code.
            result[name] = {
                "found": True,
                "sanitized_method_ast": snippet[:11000],
                "truncated": len(snippet) > 11000,
                "extra_references": sum(isinstance(n, ast.Name) and n.id == "extra" for n in ast.walk(fn)),
                "suppression_literal_present": any(isinstance(n, ast.Constant) and n.value in ("suppressResponse", "suppress_response") for n in ast.walk(fn)),
            }
        except (OSError, TypeError, ValueError, SyntaxError) as exc:
            result[name] = {"found": True, "error_type": type(exc).__name__}
    try:
        version = importlib.metadata.version("alexapy")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    return {
        "mode": "read_only_no_amazon_request",
        "alexa_py_version": version,
        "methods": result,
        "note": "AST reconstruction of installed methods. Arbitrary string literals redacted. No requests sent. Do not infer Amazon suppression support.",
    }
