from __future__ import annotations

import ast
from pathlib import Path


def test_control_plane_does_not_import_langgraph_or_langchain() -> None:
    forbidden = ("langgraph", "langchain")
    for path in Path("pm_bot/control_plane").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                lowered = name.lower()
                assert not any(token in lowered for token in forbidden), (
                    f"{path} imports forbidden dependency: {name}"
                )
