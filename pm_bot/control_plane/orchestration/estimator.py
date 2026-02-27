"""Deterministic estimator baseline with v2 fallback rules."""

from __future__ import annotations

from math import ceil
from typing import Any

from pm_bot.control_plane.db.db import OrchestratorDB


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

    DEFAULT_MIN_SAMPLES = 3

    def __init__(
        self,
        db: OrchestratorDB,
        min_samples_by_bucket: dict[str | tuple[str, ...], int] | None = None,
        default_min_samples: int = DEFAULT_MIN_SAMPLES,
    ) -> None:
        self.db = db
        self.default_min_samples = max(1, int(default_min_samples))
        self._min_samples_by_bucket_key: dict[str, int] = {}
        self._min_samples_by_level: dict[tuple[str, ...], int] = {}
        self._last_exclusion_reasons: dict[str, int] = {}

        for bucket, threshold in (min_samples_by_bucket or {}).items():
            normalized = max(1, int(threshold))
            if isinstance(bucket, tuple):
                self._min_samples_by_level[bucket] = normalized
            else:
                self._min_samples_by_bucket_key[bucket] = normalized

    def _bucket_key(self, item: dict[str, Any], keys: tuple[str, ...]) -> str:
        if not keys:
            return "global"
        parts = []
        for key in keys:
            value = str(item.get(key, "")).strip().lower() or "_"
            parts.append(f"{key}:{value}")
        return "|".join(parts)

    def _threshold_for_bucket(self, keys: tuple[str, ...], bucket_key: str) -> int:
        return self._min_samples_by_bucket_key.get(
            bucket_key,
            self._min_samples_by_level.get(keys, self.default_min_samples),
        )

    def _historical_items(self) -> tuple[list[dict[str, Any]], dict[str, int]]:
        rows = self.db.list_work_items()
        out: list[dict[str, Any]] = []
        exclusions: dict[str, int] = {}
        for row in rows:
            actual = row.get("actual_hrs")
            if actual is None:
                exclusions["missing_actual_hrs"] = exclusions.get("missing_actual_hrs", 0) + 1
                continue
            if not isinstance(actual, (int, float)):
                exclusions["non_numeric_actual_hrs"] = (
                    exclusions.get("non_numeric_actual_hrs", 0) + 1
                )
                continue
            if actual <= 0:
                exclusions["non_positive_actual_hrs"] = (
                    exclusions.get("non_positive_actual_hrs", 0) + 1
                )
                continue
            out.append(
                {
                    "type": str(row.get("type", "")).strip().lower(),
                    "area": str(row.get("area", "")).strip().lower(),
                    "size": str(row.get("size", "")).strip().lower(),
                    "actual_hrs": float(actual),
                }
            )
        return out, exclusions

    def exclusion_reasons(self) -> dict[str, int]:
        return dict(self._last_exclusion_reasons)

    def build_snapshots(self) -> list[dict[str, Any]]:
        history, exclusions = self._historical_items()
        self._last_exclusion_reasons = exclusions
        self.db.append_audit_event(
            "estimator_samples_excluded",
            {"reasons": exclusions, "excluded_total": sum(exclusions.values())},
        )
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

        fallback_path: list[dict[str, Any]] = []

        for keys in self.FALLBACKS:
            bucket_key = self._bucket_key(normalized, keys)
            row = snapshots.get(bucket_key)
            sample_count = int(row["sample_count"]) if row else 0
            min_samples = self._threshold_for_bucket(keys, bucket_key)
            selected = bool(row and sample_count >= min_samples)
            fallback_path.append(
                {
                    "bucket_key": bucket_key,
                    "bucket_keys": list(keys),
                    "sample_count": sample_count,
                    "min_samples_required": min_samples,
                    "selected": selected,
                    "reason": (
                        "selected"
                        if selected
                        else ("missing_snapshot" if row is None else "below_min_samples")
                    ),
                }
            )

            if selected and row is not None:
                return {
                    "p50": row["p50"],
                    "p80": row["p80"],
                    "sample_count": row["sample_count"],
                    "bucket_used": bucket_key,
                    "bucket_key": bucket_key,
                    "fallback_level": len(keys),
                    "fallback_path": fallback_path,
                    "bucket_rationale": (
                        f"Selected '{bucket_key}' with sample_count={sample_count} "
                        f">= min_samples_required={min_samples}."
                    ),
                    "method": row["method"],
                }

        raise ValueError(f"No estimator snapshots satisfy configured thresholds: {fallback_path}")
