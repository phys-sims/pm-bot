from __future__ import annotations

from pathlib import Path

from datetime import datetime, timezone

from pm_bot.server.db import OrchestratorDB
from pm_bot.server.reporting import ReportingService


class _FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 2, 23, 12, 0, 0, tzinfo=timezone.utc)


def _seed_reporting_dataset(db: OrchestratorDB) -> None:
    db.upsert_work_item(
        "repo#1",
        {
            "title": "Feature covered",
            "type": "feature",
            "area": "platform",
            "size": "M",
            "status": "closed",
            "actual_hrs": 4,
            "estimate_hrs": 5,
        },
    )
    db.upsert_work_item(
        "repo#2",
        {
            "title": "Feature exceeded",
            "type": "feature",
            "area": "platform",
            "size": "M",
            "status": "closed",
            "actual_hrs": 12,
            "estimate_hrs": 8,
        },
    )
    db.upsert_work_item(
        "repo#3",
        {
            "title": "Task missing fields",
            "type": "task",
            "area": "",
            "size": "",
            "status": "closed",
        },
    )

    db.store_estimate_snapshot("feature|platform|M", p50=5, p80=10, sample_count=5, method="bucket")
    db.store_estimate_snapshot("task|platform|S", p50=2, p80=3, sample_count=2, method="bucket")

    db.append_audit_event(
        "report_ir_draft_generated",
        {
            "run_id": "run-1",
            "capability_id": "report_ir_draft",
            "llm_metadata": {"capability_id": "report_ir_draft", "prompt_version": "v1"},
        },
    )
    db.append_audit_event(
        "issue_replanner_triggered",
        {
            "run_id": "run-2",
            "capability_id": "issue_replanner",
            "llm_metadata": {"capability_id": "issue_replanner", "prompt_version": "v1"},
        },
    )
    db.append_audit_event("changeset_proposed", {"run_id": "run-1", "changeset_id": 1})
    db.append_audit_event(
        "changeset_applied", {"run_id": "run-1", "changeset_id": 1, "lead_time_hours": 24.0}
    )
    db.append_audit_event("changeset_proposed", {"run_id": "run-2", "changeset_id": 2})
    db.append_audit_event("changeset_override_requested", {"run_id": "run-2", "changeset_id": 2})
    db.append_audit_event("changeset_denied", {"run_id": "run-2", "changeset_id": 2})
    db.append_audit_event("changeset_dead_lettered", {"run_id": "run-2", "changeset_id": 2})
    db.append_audit_event("task_reopened", {"run_id": "run-2", "issue_ref": "repo#2"})
    db.append_audit_event("blocker_resolved", {"run_id": "run-1", "issue_ref": "repo#1"})


def test_weekly_report_metrics_from_seeded_data(tmp_path, monkeypatch):
    monkeypatch.setattr("pm_bot.server.reporting.datetime", _FixedDatetime)

    db = OrchestratorDB()
    _seed_reporting_dataset(db)
    reporting = ReportingService(db=db, reports_dir=tmp_path)

    report_path = reporting.generate_weekly_report("seeded.md")
    content = report_path.read_text()

    assert "- Acceptance rate: 50.00% (sample=2)." in content
    assert "- Validator failures: 100.00% (count=2, sample=2)." in content
    assert "- P80 coverage: 50.00% (covered=1, sample=2)." in content
    assert "- Sparse buckets:" in content
    assert "  - task|platform|S (sample_count=2)" in content
    assert "- Excluded historical samples: total=0 reasons={}." in content
    assert "- Recommendation acceptance rate: 50.00% (accepted=1, sample=2)." in content
    assert "- Override/edit rate before approval: 50.00% (count=1, sample=2)." in content
    assert "- False-positive rate (rejected proposals): 50.00% (rejected=1, sample=2)." in content
    assert (
        "  - issue_replanner: acceptance=0.00% (accepted=0, sample=1), override/edit=100.00% (count=1, sample=1), false-positive=100.00% (rejected=1, sample=1), avg lead time=0.00h (sample=0), reopened=1, blocker resolutions=0"
        in content
    )
    assert (
        "  - report_ir_draft: acceptance=100.00% (accepted=1, sample=1), override/edit=0.00% (count=0, sample=1), false-positive=0.00% (rejected=0, sample=1), avg lead time=24.00h (sample=1), reopened=0, blocker resolutions=1"
        in content
    )
    assert "- Denied changesets: 1 (blocked write attempts=1, sample=10)." in content
    assert "- Missing `Area`: 33.33% (count=1, sample=3)." in content
    assert "- Missing `Size`: 33.33% (count=1, sample=3)." in content
    assert "- Missing `Actual (hrs)` for closed items: 33.33% (count=1, sample=3)." in content
    assert "- Snapshot IDs: estimator=[1, 2], audit=[1, 10]" in content
    assert "- Run IDs: ['run-1', 'run-2']" in content
    assert "- Context packs built: count=0 hashes=[]" in content


def test_weekly_report_matches_golden_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr("pm_bot.server.reporting.datetime", _FixedDatetime)

    db = OrchestratorDB()
    _seed_reporting_dataset(db)
    reporting = ReportingService(db=db, reports_dir=tmp_path)

    report_path = reporting.generate_weekly_report("golden.md")
    actual = report_path.read_text()
    expected = (Path(__file__).parent / "fixtures" / "golden_weekly_report.md").read_text()

    assert actual == expected
