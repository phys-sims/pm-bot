"""Meta report generation for v2 quality and safety metrics."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pm_bot.control_plane.db.db import OrchestratorDB


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
            "auth_context_denials": counts.get("auth_context_denied", 0),
            "org_sensitive_operations": (
                counts.get("changeset_proposed", 0)
                + counts.get("changeset_applied", 0)
                + counts.get("auth_context_denied", 0)
            ),
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

    def _llm_feature_metrics(self) -> dict[str, object]:
        events = self.db.list_audit_events()
        run_capabilities: dict[str, set[str]] = {}
        capability_metrics: dict[str, dict[str, float | int]] = {}
        capability_seen_changesets: dict[str, dict[str, set[str]]] = {}

        def _ensure_capability(capability_id: str) -> dict[str, float | int]:
            if capability_id not in capability_metrics:
                capability_metrics[capability_id] = {
                    "proposal_count": 0,
                    "accepted_count": 0,
                    "rejected_count": 0,
                    "override_or_edit_count": 0,
                    "lead_time_total_hours": 0.0,
                    "lead_time_sample": 0,
                    "reopened_count": 0,
                    "blocker_resolution_count": 0,
                }
                capability_seen_changesets[capability_id] = {
                    "proposed": set(),
                    "accepted": set(),
                    "rejected": set(),
                }
            return capability_metrics[capability_id]

        for event in events:
            payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
            run_id = str(payload.get("run_id", "")).strip()
            llm_metadata = payload.get("llm_metadata", {}) if isinstance(payload, dict) else {}
            capability_id = ""
            if isinstance(llm_metadata, dict):
                capability_id = str(llm_metadata.get("capability_id", "")).strip()
            if not capability_id:
                capability_id = str(payload.get("capability_id", "")).strip()
            if run_id and capability_id:
                run_capabilities.setdefault(run_id, set()).add(capability_id)
                _ensure_capability(capability_id)

        for event in events:
            payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
            run_id = str(payload.get("run_id", "")).strip()
            capabilities = run_capabilities.get(run_id, set())
            if not capabilities:
                continue

            event_type = str(event.get("event_type", "")).strip()
            for capability_id in capabilities:
                metrics = _ensure_capability(capability_id)
                changeset_id = str(payload.get("changeset_id", "")).strip()
                seen = capability_seen_changesets.get(capability_id, {})
                if event_type == "changeset_proposed":
                    if changeset_id and changeset_id in seen.get("proposed", set()):
                        pass
                    else:
                        metrics["proposal_count"] += 1
                        if changeset_id:
                            seen["proposed"].add(changeset_id)
                elif event_type == "changeset_applied":
                    if changeset_id and changeset_id in seen.get("accepted", set()):
                        pass
                    else:
                        metrics["accepted_count"] += 1
                        if changeset_id:
                            seen["accepted"].add(changeset_id)
                elif event_type in {"changeset_denied", "changeset_dead_lettered"}:
                    if changeset_id and changeset_id in seen.get("rejected", set()):
                        pass
                    else:
                        metrics["rejected_count"] += 1
                        if changeset_id:
                            seen["rejected"].add(changeset_id)

                if event_type in {
                    "changeset_override_requested",
                    "changeset_override_applied",
                    "changeset_payload_edited",
                    "changeset_edited_before_approval",
                }:
                    metrics["override_or_edit_count"] += 1
                elif bool(payload.get("override_before_approval")) or bool(
                    payload.get("edited_before_approval")
                ):
                    metrics["override_or_edit_count"] += 1

                lead_time_hours = payload.get("lead_time_hours")
                if isinstance(lead_time_hours, (int, float)):
                    metrics["lead_time_total_hours"] += float(lead_time_hours)
                    metrics["lead_time_sample"] += 1

                if event_type in {"task_reopened", "work_item_reopened"} or bool(
                    payload.get("reopened")
                ):
                    metrics["reopened_count"] += 1

                blocker_resolution_count = payload.get("blocker_resolution_count")
                if isinstance(blocker_resolution_count, int):
                    metrics["blocker_resolution_count"] += blocker_resolution_count
                elif event_type in {"blocker_resolved", "blocked_by_cleared"}:
                    metrics["blocker_resolution_count"] += 1

        summaries: list[dict[str, float | int | str]] = []
        totals = {
            "proposal_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
            "override_or_edit_count": 0,
            "lead_time_total_hours": 0.0,
            "lead_time_sample": 0,
            "reopened_count": 0,
            "blocker_resolution_count": 0,
        }

        for capability_id in sorted(capability_metrics):
            metrics = capability_metrics[capability_id]
            proposal_count = int(metrics["proposal_count"])
            accepted_count = int(metrics["accepted_count"])
            rejected_count = int(metrics["rejected_count"])
            override_count = int(metrics["override_or_edit_count"])
            lead_time_sample = int(metrics["lead_time_sample"])
            lead_time_total_hours = float(metrics["lead_time_total_hours"])
            reopened_count = int(metrics["reopened_count"])
            blocker_resolution_count = int(metrics["blocker_resolution_count"])

            totals["proposal_count"] += proposal_count
            totals["accepted_count"] += accepted_count
            totals["rejected_count"] += rejected_count
            totals["override_or_edit_count"] += override_count
            totals["lead_time_total_hours"] += lead_time_total_hours
            totals["lead_time_sample"] += lead_time_sample
            totals["reopened_count"] += reopened_count
            totals["blocker_resolution_count"] += blocker_resolution_count

            summaries.append(
                {
                    "capability_id": capability_id,
                    "proposal_count": proposal_count,
                    "accepted_count": accepted_count,
                    "rejected_count": rejected_count,
                    "override_or_edit_count": override_count,
                    "recommendation_acceptance_rate": (
                        accepted_count / proposal_count if proposal_count else 0.0
                    ),
                    "override_or_edit_rate": (
                        override_count / proposal_count if proposal_count else 0.0
                    ),
                    "false_positive_rate": (
                        rejected_count / proposal_count if proposal_count else 0.0
                    ),
                    "avg_lead_time_hours": (
                        lead_time_total_hours / lead_time_sample if lead_time_sample else 0.0
                    ),
                    "lead_time_sample": lead_time_sample,
                    "reopened_count": reopened_count,
                    "blocker_resolution_count": blocker_resolution_count,
                }
            )

        proposal_total = int(totals["proposal_count"])
        lead_time_sample_total = int(totals["lead_time_sample"])
        return {
            "proposal_count": proposal_total,
            "accepted_count": int(totals["accepted_count"]),
            "rejected_count": int(totals["rejected_count"]),
            "override_or_edit_count": int(totals["override_or_edit_count"]),
            "recommendation_acceptance_rate": (
                int(totals["accepted_count"]) / proposal_total if proposal_total else 0.0
            ),
            "override_or_edit_rate": (
                int(totals["override_or_edit_count"]) / proposal_total if proposal_total else 0.0
            ),
            "false_positive_rate": (
                int(totals["rejected_count"]) / proposal_total if proposal_total else 0.0
            ),
            "avg_lead_time_hours": (
                float(totals["lead_time_total_hours"]) / lead_time_sample_total
                if lead_time_sample_total
                else 0.0
            ),
            "lead_time_sample": lead_time_sample_total,
            "reopened_count": int(totals["reopened_count"]),
            "blocker_resolution_count": int(totals["blocker_resolution_count"]),
            "capability_breakdown": summaries,
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
        llm = self._llm_feature_metrics()
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
            "## LLM feature performance",
            (
                "- Recommendation acceptance rate: "
                f"{llm['recommendation_acceptance_rate']:.2%} "
                f"(accepted={llm['accepted_count']}, sample={llm['proposal_count']})."
            ),
            (
                "- Override/edit rate before approval: "
                f"{llm['override_or_edit_rate']:.2%} "
                f"(count={llm['override_or_edit_count']}, sample={llm['proposal_count']})."
            ),
            (
                "- False-positive rate (rejected proposals): "
                f"{llm['false_positive_rate']:.2%} "
                f"(rejected={llm['rejected_count']}, sample={llm['proposal_count']})."
            ),
            (
                "- Downstream outcomes: "
                f"avg lead time={llm['avg_lead_time_hours']:.2f}h (sample={llm['lead_time_sample']}), "
                f"reopened tasks={llm['reopened_count']}, "
                f"blocker resolutions={llm['blocker_resolution_count']}."
            ),
            "- Per-capability metrics:",
        ]

        if llm["capability_breakdown"]:
            for capability in llm["capability_breakdown"]:
                lines.append(
                    "  - "
                    f"{capability['capability_id']}: "
                    f"acceptance={capability['recommendation_acceptance_rate']:.2%} "
                    f"(accepted={capability['accepted_count']}, sample={capability['proposal_count']}), "
                    f"override/edit={capability['override_or_edit_rate']:.2%} "
                    f"(count={capability['override_or_edit_count']}, sample={capability['proposal_count']}), "
                    f"false-positive={capability['false_positive_rate']:.2%} "
                    f"(rejected={capability['rejected_count']}, sample={capability['proposal_count']}), "
                    f"avg lead time={capability['avg_lead_time_hours']:.2f}h "
                    f"(sample={capability['lead_time_sample']}), "
                    f"reopened={capability['reopened_count']}, "
                    f"blocker resolutions={capability['blocker_resolution_count']}"
                )
        else:
            lines.append("  - none")

        lines.extend(
            [
                "",
                "## Estimation",
                (
                    f"- P80 coverage: {estimation['p80_coverage']:.2%} "
                    f"(covered={estimation['covered_count']}, sample={estimation['coverage_sample']})."
                ),
                f"- Snapshot bucket count: {estimation['bucket_count']}.",
                "- Sparse buckets:",
            ]
        )

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
                f"- Auth context denials: {safety['auth_context_denials']} (sample={safety['sample_size']}).",
                f"- Org-sensitive operation events: {safety['org_sensitive_operations']} (sample={safety['sample_size']}).",
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
