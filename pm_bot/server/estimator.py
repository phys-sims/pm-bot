"""Deterministic estimator baseline with v2 fallback rules."""

from __future__ import annotations

from math import ceil
from typing import Any

from pm_bot.server.db import OrchestratorDB


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot compute quantile for empty values")
    idx = ceil(q * len(sorted_values)) - 1
    idx = max(0, min(idx, len(sorted_values) - 1))
    return float(sorted_values[idx])


class EstimatorService:
    """Compute and serve deterministic P50/P80 estimates."""

    FALLBACKS: tuple[tuple[str, ...], ...] = (
        ("type", "area", "size"),
        ("type", "area"),
        ("type",),
        tuple(),
    )

    def __init__(self, db: OrchestratorDB) -> None:
        self.db = db

    def _bucket_key(self, item: dict[str, Any], keys: tuple[str, ...]) -> str:
        if not keys:
            return "global"
        parts = []
        for key in keys:
            value = str(item.get(key, "")).strip().lower() or "_"
            parts.append(f"{key}:{value}")
        return "|".join(parts)

    def _historical_items(self) -> list[dict[str, Any]]:
        rows = self.db.list_work_items()
        out: list[dict[str, Any]] = []
        for row in rows:
            actual = row.get("actual_hrs")
            if isinstance(actual, (int, float)) and actual > 0:
                out.append(
                    {
                        "type": str(row.get("type", "")).strip().lower(),
                        "area": str(row.get("area", "")).strip().lower(),
                        "size": str(row.get("size", "")).strip().lower(),
                        "actual_hrs": float(actual),
                    }
                )
        return out

    def build_snapshots(self) -> list[dict[str, Any]]:
        history = self._historical_items()
        snapshots: list[dict[str, Any]] = []
        for keys in self.FALLBACKS:
            groups: dict[str, list[float]] = {}
            for item in history:
                bucket = self._bucket_key(item, keys)
                groups.setdefault(bucket, []).append(item["actual_hrs"])
            for bucket_key, values in groups.items():
                values_sorted = sorted(values)
                p50 = _quantile(values_sorted, 0.5)
                p80 = _quantile(values_sorted, 0.8)
                method = "nearest-rank"
                self.db.store_estimate_snapshot(
                    bucket_key=bucket_key,
                    p50=p50,
                    p80=p80,
                    sample_count=len(values_sorted),
                    method=method,
                )
                snapshots.append(
                    {
                        "bucket_key": bucket_key,
                        "p50": p50,
                        "p80": p80,
                        "sample_count": len(values_sorted),
                        "method": method,
                    }
                )
        return snapshots

    def predict(self, item: dict[str, Any]) -> dict[str, Any]:
        snapshots = {row["bucket_key"]: row for row in self.db.latest_estimate_snapshots()}
        normalized = {
            "type": str(item.get("type", "")).strip().lower(),
            "area": str(item.get("area", "")).strip().lower(),
            "size": str(item.get("size", "")).strip().lower(),
        }

        for keys in self.FALLBACKS:
            bucket_key = self._bucket_key(normalized, keys)
            if bucket_key in snapshots:
                row = snapshots[bucket_key]
                return {
                    "p50": row["p50"],
                    "p80": row["p80"],
                    "sample_count": row["sample_count"],
                    "bucket_key": bucket_key,
                    "fallback_level": len(keys),
                    "method": row["method"],
                }

        raise ValueError("No estimator snapshots available")
