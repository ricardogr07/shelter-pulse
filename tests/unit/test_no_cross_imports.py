"""Module boundary guardrail: shelterpulse.core must not import from api/ or cli/."""

import ast
import pathlib


def _get_imports(filepath: pathlib.Path) -> list[str]:
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


FORBIDDEN_IN_CORE = ("shelterpulse.api", "shelterpulse.cli")
CORE_DIR = pathlib.Path(__file__).parent.parent.parent / "shelterpulse" / "core"


def test_core_does_not_import_adapters():
    violations: list[str] = []
    for py_file in sorted(CORE_DIR.rglob("*.py")):
        for module in _get_imports(py_file):
            if any(module.startswith(forbidden) for forbidden in FORBIDDEN_IN_CORE):
                violations.append(f"{py_file.name}: imports {module}")
    assert not violations, (
        "Core module boundary violated — core must not import from adapters:\n"
        + "\n".join(violations)
    )
