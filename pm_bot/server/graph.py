"""Graph/tree views derived from work-item relationships."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from pm_bot.server.db import OrchestratorDB


class GraphService:
    _SOURCE_PRIORITY = {
        "sub_issue": 0,
        "dependency_api": 1,
        "checklist": 2,
    }

    def __init__(self, db: OrchestratorDB) -> None:
        self.db = db

    def tree(self, root_ref: str) -> dict[str, Any]:
        root = self.db.get_work_item(root_ref)
        if root is None:
            raise ValueError(f"Unknown root: {root_ref}")

        relationships = self.db.list_relationships()
        child_sources: dict[str, set[str]] = defaultdict(set)
        for edge in relationships:
            child_sources[edge["child_ref"]].add(edge["source"])

        selected_children: dict[str, list[dict[str, str]]] = defaultdict(list)
        warnings: list[dict[str, Any]] = []
        parent_choice: dict[str, dict[str, str]] = {}

        for edge in relationships:
            parent_ref = edge["parent_ref"]
            child_ref = edge["child_ref"]
            source = edge["source"]
            existing = parent_choice.get(child_ref)
            if existing is None:
                parent_choice[child_ref] = edge
                continue

            existing_priority = self._SOURCE_PRIORITY.get(existing["source"], 99)
            source_priority = self._SOURCE_PRIORITY.get(source, 99)
            if source_priority < existing_priority:
                warnings.append(
                    {
                        "code": "conflicting_parent_edge",
                        "message": f"{child_ref} has multiple parents; chose {parent_ref} via {source}.",
                        "diagnostic": {
                            "child": child_ref,
                            "selected": {
                                "parent": parent_ref,
                                "source": source,
                            },
                            "discarded": {
                                "parent": existing["parent_ref"],
                                "source": existing["source"],
                            },
                        },
                    }
                )
                parent_choice[child_ref] = edge
            elif parent_ref != existing["parent_ref"] or source != existing["source"]:
                warnings.append(
                    {
                        "code": "conflicting_parent_edge",
                        "message": f"{child_ref} has multiple parents; kept {existing['parent_ref']} via {existing['source']}.",
                        "diagnostic": {
                            "child": child_ref,
                            "selected": {
                                "parent": existing["parent_ref"],
                                "source": existing["source"],
                            },
                            "discarded": {
                                "parent": parent_ref,
                                "source": source,
                            },
                        },
                    }
                )

        for edge in parent_choice.values():
            selected_children[edge["parent_ref"]].append(edge)

        for parent_ref in selected_children:
            selected_children[parent_ref].sort(
                key=lambda edge: (
                    self._SOURCE_PRIORITY.get(edge["source"], 99),
                    edge["child_ref"],
                )
            )

        in_path: list[str] = []

        def build(ref: str) -> dict[str, Any]:
            if ref in in_path:
                cycle_path = in_path[in_path.index(ref) :] + [ref]
                warnings.append(
                    {
                        "code": "cycle_detected",
                        "message": "Cycle detected in parent/child hierarchy.",
                        "diagnostic": {"path": cycle_path},
                    }
                )
                return {"issue_ref": ref, "cycle": True, "children": []}

            in_path.append(ref)
            item = self.db.get_work_item(ref) or {"title": "", "type": "unknown"}
            children = []
            for edge in selected_children.get(ref, []):
                child_node = build(edge["child_ref"])
                child_node.setdefault("provenance", edge["source"])
                children.append(child_node)

            in_path.pop()
            return {
                "issue_ref": ref,
                "title": item.get("title", ""),
                "type": item.get("type", ""),
                "provenance": self._preferred_source_for_node(ref, child_sources),
                "children": children,
            }

        tree = build(root_ref)
        return {"root": tree, "warnings": warnings}

    def _preferred_source_for_node(self, ref: str, child_sources: dict[str, set[str]]) -> str:
        sources = child_sources.get(ref, set())
        if not sources:
            return "sub_issue"
        return sorted(sources, key=lambda source: self._SOURCE_PRIORITY.get(source, 99))[0]

    def dependencies(self, area: str = "") -> dict[str, Any]:
        nodes = []
        edges = []
        warnings: list[dict[str, Any]] = []

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
                        "provenance": "dependency_api",
                    }
                )

        seen = set()
        for rel in self.db.list_relationships():
            if rel["source"] != "dependency_api":
                continue
            edge_key = (rel["child_ref"], rel["parent_ref"])
            if edge_key in seen:
                continue
            seen.add(edge_key)
            edges.append(
                {
                    "from": rel["child_ref"],
                    "to": rel["parent_ref"],
                    "edge_type": "blocked_by",
                    "provenance": "dependency_api",
                }
            )

        if not edges:
            warnings.append(
                {
                    "code": "no_dependencies",
                    "message": "No dependency edges available for requested filter.",
                }
            )

        return {
            "nodes": nodes,
            "edges": edges,
            "warnings": warnings,
            "summary": {
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
        }
