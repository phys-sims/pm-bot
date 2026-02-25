"""Meta report generation for v2 quality and safety metrics."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pm_bot.server.db import OrchestratorDB


class ReportingService:
    def __init__(self, db: OrchestratorDB, reports_dir: str | Path = "reports") -> None:
        self.db = db
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _metric_counts(self) -> dict[str, int]:
        events = self.db.list_audit_events()
        counts: dict[str, int] = {}
        for event in events:
            counts[event["event_type"]] = counts.get(event["event_type"], 0) + 1
        return counts

    def _draft_quality_metrics(self, counts: dict[str, int]) -> dict[str, float | int]:
        proposed = counts.get("changeset_proposed", 0)
        applied = counts.get("changeset_applied", 0)
        denied = counts.get("changeset_denied", 0)
        dead_lettered = counts.get("changeset_dead_lettered", 0)
        acceptance_rate = (applied / proposed) if proposed else 0.0
        validator_failure_rate = ((denied + dead_lettered) / proposed) if proposed else 0.0
        return {
            "proposed": proposed,
            "applied": applied,
            "acceptance_rate": acceptance_rate,
            "validator_failures": denied + dead_lettered,
            "validator_failure_rate": validator_failure_rate,
            "avg_human_edits": 0.0,
            "published_sample": applied,
        }

    def _estimation_metrics(self) -> dict[str, object]:
        work_items = self.db.list_work_items()
        snapshots = self.db.latest_estimate_snapshots()
        snapshot_ids = [int(snapshot["id"]) for snapshot in snapshots]
        snapshot_bucket_map = {
            str(snapshot["bucket_key"]): {
                "p80": float(snapshot["p80"]),
                "sample_count": int(snapshot["sample_count"]),
            }
            for snapshot in snapshots
        }

        comparable_items = [
            item
            for item in work_items
            if isinstance(item.get("actual_hrs"), (int, float))
            and isinstance(item.get("type"), str)
            and isinstance(item.get("area"), str)
            and isinstance(item.get("size"), str)
        ]
        covered_count = 0
        for item in comparable_items:
            bucket_key = f"{item['type']}|{item['area']}|{item['size']}"
            snapshot = snapshot_bucket_map.get(bucket_key)
            if not snapshot:
                continue
            if float(item["actual_hrs"]) <= snapshot["p80"]:
                covered_count += 1

        p80_coverage = (covered_count / len(comparable_items)) if comparable_items else 0.0
        sparse_buckets = [
            {
                "bucket_key": bucket_key,
                "sample_count": data["sample_count"],
            }
            for bucket_key, data in snapshot_bucket_map.items()
            if data["sample_count"] < 3
        ]
        sparse_buckets.sort(key=lambda bucket: (bucket["sample_count"], bucket["bucket_key"]))

        exclusion_reasons: dict[str, int] = {}
        excluded_total = 0
        exclusion_events = self.db.list_audit_events("estimator_samples_excluded")
        if exclusion_events:
            latest = exclusion_events[-1]["payload"]
            raw_reasons = latest.get("reasons")
            if isinstance(raw_reasons, dict):
                exclusion_reasons = {str(k): int(v) for k, v in raw_reasons.items()}
            excluded_total = int(latest.get("excluded_total") or sum(exclusion_reasons.values()))

        return {
            "p80_coverage": p80_coverage,
            "coverage_sample": len(comparable_items),
            "covered_count": covered_count,
            "snapshot_ids": snapshot_ids,
            "bucket_count": len(snapshots),
            "sparse_buckets": sparse_buckets[:5],
            "excluded_total": excluded_total,
            "excluded_reasons": exclusion_reasons,
        }

    def _safety_metrics(self, counts: dict[str, int]) -> dict[str, int]:
        return {
            "blocked_write_attempts": counts.get("changeset_denied", 0),
            "denied_changesets": counts.get("changeset_denied", 0),
            "dead_lettered_changesets": counts.get("changeset_dead_lettered", 0),
            "denied_agent_runs": counts.get("agent_run_denied", 0),
            "anomaly_count": counts.get("safety_anomaly", 0),
            "sample_size": sum(counts.values()),
        }

    def _data_quality_metrics(self) -> dict[str, object]:
        work_item_records = self.db.list_work_item_records()
        total_items = len(work_item_records)
        closed_items = [
            record for record in work_item_records if record["payload"].get("status") == "closed"
        ]

        missing_area = [
            record
            for record in work_item_records
            if not str(record["payload"].get("area") or "").strip()
        ]
        missing_size = [
            record
            for record in work_item_records
            if not str(record["payload"].get("size") or "").strip()
        ]
        missing_actual_closed = [
            record
            for record in closed_items
            if not isinstance(record["payload"].get("actual_hrs"), (int, float))
        ]

        total_by_type: dict[str, int] = {}
        missing_by_type: dict[str, int] = {}
        for record in work_item_records:
            item_type = str(record["payload"].get("type") or "unknown")
            total_by_type[item_type] = total_by_type.get(item_type, 0) + 1
            payload = record["payload"]
            if (
                not str(payload.get("area") or "").strip()
                or not str(payload.get("size") or "").strip()
                or (
                    payload.get("status") == "closed"
                    and not isinstance(payload.get("actual_hrs"), (int, float))
                )
            ):
                missing_by_type[item_type] = missing_by_type.get(item_type, 0) + 1

        offenders = [
            {
                "template_type": item_type,
                "missing_count": missing_count,
                "total_count": total_by_type[item_type],
            }
            for item_type, missing_count in missing_by_type.items()
        ]
        offenders.sort(
            key=lambda offender: (
                -offender["missing_count"],
                offender["template_type"],
            )
        )

        return {
            "total_items": total_items,
            "closed_sample": len(closed_items),
            "missing_area_count": len(missing_area),
            "missing_area_pct": (len(missing_area) / total_items) if total_items else 0.0,
            "missing_size_count": len(missing_size),
            "missing_size_pct": (len(missing_size) / total_items) if total_items else 0.0,
            "missing_actual_closed_count": len(missing_actual_closed),
            "missing_actual_closed_pct": (
                (len(missing_actual_closed) / len(closed_items)) if closed_items else 0.0
            ),
            "top_offenders": offenders[:3],
        }

    def _traceability_metadata(self) -> dict[str, object]:
        audit_events = self.db.list_audit_events()
        context_events = [
            event for event in audit_events if event["event_type"] == "context_pack_built"
        ]
        recent_context_hashes = [
            str(event["payload"].get("hash") or "")
            for event in context_events
            if str(event["payload"].get("hash") or "")
        ]
        recent_context_hashes = sorted(dict.fromkeys(recent_context_hashes))[:5]
        run_ids = sorted(
            {
                str(event["payload"].get("run_id"))
                for event in audit_events
                if str(event["payload"].get("run_id") or "").strip()
            }
        )
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "audit_snapshot": {
                "event_count": len(audit_events),
                "first_event_id": int(audit_events[0]["id"]) if audit_events else None,
                "last_event_id": int(audit_events[-1]["id"]) if audit_events else None,
            },
            "context_packs": {
                "count": len(context_events),
                "recent_hashes": recent_context_hashes,
            },
            "run_ids": run_ids,
        }

    def generate_weekly_report(self, report_name: str = "weekly.md") -> Path:
        counts = self._metric_counts()
        draft = self._draft_quality_metrics(counts)
        estimation = self._estimation_metrics()
        safety = self._safety_metrics(counts)
        data_quality = self._data_quality_metrics()
        traceability = self._traceability_metadata()

        lines = [
            f"# Weekly pm-bot report — {traceability['generated_at'][0:10]}",
            "",
            "## Summary",
            "- Wins:",
            f"  - Draft acceptance held at {draft['acceptance_rate']:.2%} across {draft['proposed']} proposed changesets.",
            f"  - P80 coverage is {estimation['p80_coverage']:.2%} over {estimation['coverage_sample']} comparable closed items.",
            "- Pain points:",
            f"  - Missing `Area` on {data_quality['missing_area_count']} of {data_quality['total_items']} items.",
            f"  - Missing `Actual (hrs)` on {data_quality['missing_actual_closed_count']} of {data_quality['closed_sample']} closed items.",
            "- Recommended actions (top 3):",
            "  1. Add explicit `Actual (hrs)` prompts in templates for close-out workflows.",
            "  2. Require `Area` and `Size` before publish in validator checks.",
            "  3. Increase estimator bucket samples for sparse buckets listed below.",
            "",
            "## Drafting quality",
            f"- Acceptance rate: {draft['acceptance_rate']:.2%} (sample={draft['proposed']}).",
            (
                f"- Validator failures: {draft['validator_failure_rate']:.2%} "
                f"(count={draft['validator_failures']}, sample={draft['proposed']})."
            ),
            (
                "- Average # of human edits per published draft: "
                f"{draft['avg_human_edits']:.2f} (sample={draft['published_sample']})."
            ),
            "",
            "## Estimation",
            (
                f"- P80 coverage: {estimation['p80_coverage']:.2%} "
                f"(covered={estimation['covered_count']}, sample={estimation['coverage_sample']})."
            ),
            f"- Snapshot bucket count: {estimation['bucket_count']}.",
            "- Sparse buckets:",
        ]

        if estimation["sparse_buckets"]:
            for bucket in estimation["sparse_buckets"]:
                lines.append(f"  - {bucket['bucket_key']} (sample_count={bucket['sample_count']})")
        else:
            lines.append("  - none")

        lines.append(
            "- Excluded historical samples: "
            f"total={estimation['excluded_total']} reasons={estimation['excluded_reasons']}."
        )

        lines.extend(
            [
                "",
                "## Safety incidents",
                (
                    "- Denied changesets: "
                    f"{safety['denied_changesets']} (blocked write attempts={safety['blocked_write_attempts']}, sample={safety['sample_size']})."
                ),
                f"- Denied agent runs: {safety['denied_agent_runs']} (sample={safety['sample_size']}).",
                f"- Dead-lettered changesets: {safety['dead_lettered_changesets']} (sample={safety['sample_size']}).",
                f"- Anomaly counts: {safety['anomaly_count']} (sample={safety['sample_size']}).",
                "",
                "## Data quality",
                (
                    f"- Missing `Area`: {data_quality['missing_area_pct']:.2%} "
                    f"(count={data_quality['missing_area_count']}, sample={data_quality['total_items']})."
                ),
                (
                    f"- Missing `Size`: {data_quality['missing_size_pct']:.2%} "
                    f"(count={data_quality['missing_size_count']}, sample={data_quality['total_items']})."
                ),
                (
                    "- Missing `Actual (hrs)` for closed items: "
                    f"{data_quality['missing_actual_closed_pct']:.2%} "
                    f"(count={data_quality['missing_actual_closed_count']}, sample={data_quality['closed_sample']})."
                ),
                "- Top offenders by template type:",
            ]
        )

        if data_quality["top_offenders"]:
            for offender in data_quality["top_offenders"]:
                lines.append(
                    "  - "
                    f"{offender['template_type']} "
                    f"(missing={offender['missing_count']}, sample={offender['total_count']})"
                )
        else:
            lines.append("  - none")

        lines.extend(
            [
                "",
                "## Appendix",
                (
                    "- Snapshot IDs: "
                    f"estimator={estimation['snapshot_ids']}, "
                    f"audit=[{traceability['audit_snapshot']['first_event_id']}, {traceability['audit_snapshot']['last_event_id']}]"
                ),
                f"- Report generation timestamp: {traceability['generated_at']}",
                f"- Run IDs: {traceability['run_ids']}",
                (
                    "- Context packs built: "
                    f"count={traceability['context_packs']['count']} "
                    f"hashes={traceability['context_packs']['recent_hashes']}"
                ),
                (
                    "- Snapshot sample sizes: "
                    f"audit_events={traceability['audit_snapshot']['event_count']}, "
                    f"work_items={data_quality['total_items']}, "
                    f"estimator_buckets={estimation['bucket_count']}"
                ),
            ]
        )

        report_path = self.reports_dir / report_name
        report_path.write_text("\n".join(lines) + "\n")
        self.db.record_report("weekly", str(report_path))
        return report_path
