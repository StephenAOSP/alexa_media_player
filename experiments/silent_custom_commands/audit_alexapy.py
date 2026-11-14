"""Offline structural audit of AlexaPy's custom-command call path.

No imports of alexapy, no login, no network requests. Only parses installed source.
"""
import ast
import importlib.util
from pathlib import Path


TARGETS = {"run_custom", "send_sequence", "run_behavior"}


def source_path():
    spec = importlib.util.find_spec("alexapy")
    if not spec or not spec.submodule_search_locations:
        raise RuntimeError("Install alexapy==1.35.0 in a disposable environment")
    path = Path(next(iter(spec.submodule_search_locations))) / "alexaapi.py"
    if not path.is_file():
        raise RuntimeError(f"AlexaPy source not found: {path}")
    return path


def audit(source):
    tree = ast.parse(source)
    result = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in TARGETS:
            continue
        arguments = [arg.arg for arg in node.args.args]
        if node.args.kwarg:
            arguments.append("**" + node.args.kwarg.arg)
        calls = []
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            name = func.attr if isinstance(func, ast.Attribute) else (
                func.id if isinstance(func, ast.Name) else None
            )
            if name in TARGETS or name in {"_post_request", "_request"}:
                calls.append({
                    "callee": name,
                    "keywords": [kw.arg or "**expansion" for kw in child.keywords],
                    "line": child.lineno,
                })
        result.append({
            "method": node.name,
            "line": node.lineno,
            "arguments": arguments,
            "calls": calls,
            "mentions_suppress_response": "suppress_response" in (
                ast.get_source_segment(source, node) or ""
            ),
            "mentions_suppressResponse": "suppressResponse" in (
                ast.get_source_segment(source, node) or ""
            ),
        })
    return result


def main():
    import json
    path = source_path()
    report = audit(path.read_text(encoding="utf-8"))
    print(json.dumps({"source": str(path), "methods": report}, indent=2))
    print("\nNOTE: This is a static call-site inventory, not proof of HTTP payload behaviour.")
    print("Never share credentials, cookies, customer IDs or serial numbers.")


if __name__ == "__main__":
    main()
