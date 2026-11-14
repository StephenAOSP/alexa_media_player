"""Offline-only AlexaPy source inspector. No Alexa API calls are made."""
import importlib.util
import ast
from pathlib import Path


def locate_source():
    spec = importlib.util.find_spec("alexapy")
    if not spec or not spec.submodule_search_locations:
        raise RuntimeError("AlexaPy not installed; install alexapy==1.35.0 in a disposable venv")
    base = Path(next(iter(spec.submodule_search_locations)))
    path = base / "alexaapi.py"
    if not path.is_file():
        raise RuntimeError(f"Cannot locate {path}")
    return path


def extract_functions(source):
    tree = ast.parse(source)
    names = ("run_custom", "send_sequence", "run_behavior")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            yield node.name, node.lineno, ast.get_source_segment(source, node)


def main():
    path = locate_source()
    print(f"Inspecting: {path}\n")
    source = path.read_text(encoding="utf-8")
    for name, line, snippet in extract_functions(source):
        print(f"\n### {name} (line {line})\n{snippet}\n")


if __name__ == "__main__":
    main()
