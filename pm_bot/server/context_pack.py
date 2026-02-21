"""Context pack assembly with deterministic truncation and hashing."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pm_bot.server.db import OrchestratorDB


def build_context_pack(
    db: OrchestratorDB,
    issue_ref: str,
    profile: str = "pm-drafting",
    char_budget: int = 4000,
) -> dict[str, Any]:
    item = db.get_work_item(issue_ref)
    if item is None:
        raise ValueError(f"Unknown work item: {issue_ref}")

    canonical = {
        "profile": profile,
        "issue_ref": issue_ref,
        "title": item.get("title", ""),
        "type": item.get("type", ""),
        "fields": item.get("fields", {}),
        "relationships": item.get("relationships", {}),
    }

    serialized = json.dumps(canonical, sort_keys=True)
    if len(serialized) > char_budget:
        serialized = serialized[:char_budget]

    content_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return {
        "hash": content_hash,
        "content": json.loads(serialized),
        "char_budget": char_budget,
    }
