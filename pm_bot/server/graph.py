"""Graph/tree views derived from work-item relationships."""

from __future__ import annotations

from typing import Any

from pm_bot.server.db import OrchestratorDB


class GraphService:
    def __init__(self, db: OrchestratorDB) -> None:
        self.db = db

    def tree(self, root_ref: str) -> dict[str, Any]:
        root = self.db.get_work_item(root_ref)
        if root is None:
            raise ValueError(f"Unknown root: {root_ref}")

        visited: set[str] = set()

        def build(ref: str) -> dict[str, Any]:
            if ref in visited:
                return {"issue_ref": ref, "cycle": True, "children": []}
            visited.add(ref)
            item = self.db.get_work_item(ref) or {"title": "", "type": "unknown"}
            rel = self.db.get_related(ref)
            children = [build(child) for child in rel["children"]]
            return {
                "issue_ref": ref,
                "title": item.get("title", ""),
                "type": item.get("type", ""),
                "provenance": "relationship",
                "children": children,
            }

        return build(root_ref)

    def dependencies(self, area: str = "") -> dict[str, list[dict[str, Any]]]:
        nodes = []
        edges = []
        for item in self.db.list_work_items():
            if area and str(item.get("area", "")) != area:
                continue
            issue_ref = item.get("fields", {}).get("issue_ref") or item.get("title", "")
            nodes.append(
                {
                    "id": issue_ref,
                    "title": item.get("title", ""),
                    "type": item.get("type", ""),
                    "area": item.get("area", ""),
                }
            )
            blocked_by = item.get("blocked_by", "")
            if blocked_by:
                edges.append(
                    {
                        "from": issue_ref,
                        "to": str(blocked_by),
                        "edge_type": "blocked_by",
                        "provenance": "heading",
                    }
                )
        return {"nodes": nodes, "edges": edges}
