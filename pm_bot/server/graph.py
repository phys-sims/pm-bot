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

    def ingest_repo_graph(self, repo: str, connector: Any) -> dict[str, Any]:
        calls = 0
        failures = 0
        edge_count = 0
        partial = False
        diagnostics: dict[str, Any] = {"failures": [], "repo": repo}

        for item in self.db.list_work_items():
            issue_ref = item.get("fields", {}).get("issue_ref") or item.get("issue_ref", "")
            if not issue_ref or not issue_ref.startswith("#"):
                continue
            calls += 1
            full_ref = f"{repo}{issue_ref}"
            try:
                for sub_issue in connector.list_sub_issues(repo, issue_ref):
                    child_ref = f"{repo}{sub_issue['issue_ref']}"
                    self.db.add_graph_edge(
                        from_issue_ref=full_ref,
                        to_issue_ref=child_ref,
                        edge_type="parent_child",
                        source="sub_issue",
                        observed_at=sub_issue.get("observed_at", ""),
                    )
                    edge_count += 1

                for dep in connector.list_issue_dependencies(repo, issue_ref):
                    blocked_by_ref = f"{repo}{dep['issue_ref']}"
                    self.db.add_graph_edge(
                        from_issue_ref=full_ref,
                        to_issue_ref=blocked_by_ref,
                        edge_type="blocked_by",
                        source="dependency_api",
                        observed_at=dep.get("observed_at", ""),
                    )
                    edge_count += 1
            except Exception as exc:  # pragma: no cover - defensive connector boundary
                failures += 1
                partial = True
                diagnostics["failures"].append({"issue_ref": full_ref, "error": str(exc)})

        self.db.record_graph_ingestion(
            repo=repo,
            calls=calls,
            failures=failures,
            partial=partial,
            diagnostics=diagnostics,
        )
        return {
            "repo": repo,
            "calls": calls,
            "failures": failures,
            "partial": partial,
            "edge_count": edge_count,
            "diagnostics": diagnostics,
        }

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

        for rel in self.db.list_graph_edges(edge_type="blocked_by"):
            edge_key = (rel["from_issue_ref"], rel["to_issue_ref"], rel["source"])
            if edge_key in seen:
                continue
            seen.add(edge_key)
            edges.append(
                {
                    "from": rel["from_issue_ref"],
                    "to": rel["to_issue_ref"],
                    "edge_type": "blocked_by",
                    "provenance": rel["source"],
                }
            )

        ingestion_rows = self.db.latest_graph_ingestions()
        for row in ingestion_rows:
            if row["partial"]:
                warnings.append(
                    {
                        "code": "partial_ingestion",
                        "message": f"Graph ingestion for {row['repo']} completed with partial data.",
                        "diagnostic": row,
                    }
                )

        nodes.sort(key=lambda node: (str(node.get("area", "")), str(node.get("id", ""))))
        edges.sort(
            key=lambda edge: (edge["from"], edge["to"], edge["edge_type"], edge["provenance"])
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
