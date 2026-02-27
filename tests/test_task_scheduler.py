from pm_bot.control_plane.orchestration.task_scheduler import SchedulerQuotas, TaskScheduler
from pm_bot.server.app import ServerApp


def _expand_three_tasks(service: ServerApp, plan_id: str = "plan-scheduler") -> None:
    service.expand_plan(
        plan_id=plan_id,
        repo_id=1,
        source="test",
        payload={
            "tasks": [
                {
                    "id": "a",
                    "title": "A",
                    "inputs": {
                        "repo": "org/repo-1",
                        "tool": "github_read",
                        "provider": "langgraph",
                    },
                },
                {
                    "id": "b",
                    "title": "B",
                    "inputs": {
                        "repo": "org/repo-1",
                        "tool": "github_read",
                        "provider": "langgraph",
                    },
                },
                {
                    "id": "c",
                    "title": "C",
                    "inputs": {
                        "repo": "org/repo-1",
                        "tool": "github_read",
                        "provider": "langgraph",
                    },
                },
            ]
        },
    )


def test_scheduler_respects_parallel_quota() -> None:
    service = ServerApp()
    _expand_three_tasks(service)

    scheduler = TaskScheduler(
        db=service.db,
        runner=service.runner,
        worker_id="scheduler-1",
        quotas=SchedulerQuotas(
            max_parallel_per_repo=2, max_parallel_per_tool=5, max_parallel_per_provider=5
        ),
        lease_seconds=30,
    )

    first = scheduler.run_once()
    assert first["claimed"] == 2

    all_runs = service.db.list_task_runs("plan-scheduler")
    active = [run for run in all_runs if run["status"] in {"succeeded", "running"}]
    pending = [run for run in all_runs if run["status"] == "pending"]
    assert len(active) == 2
    assert len(pending) == 1


def test_scheduler_lease_recovery_allows_reclaim_after_expiry() -> None:
    service = ServerApp()
    _expand_three_tasks(service, plan_id="plan-lease")
    task_run = service.db.list_task_runs("plan-lease")[0]

    claimed = service.db.claim_task_run(
        task_run["task_run_id"], worker_id="dead-worker", lease_seconds=1
    )
    assert claimed is True
    service.db.conn.execute(
        "UPDATE task_runs SET claim_expires_at = datetime(CURRENT_TIMESTAMP, '-1 seconds') WHERE task_run_id = ?",
        (task_run["task_run_id"],),
    )
    service.db.conn.commit()

    scheduler = TaskScheduler(
        db=service.db,
        runner=service.runner,
        worker_id="scheduler-2",
        quotas=SchedulerQuotas(
            max_parallel_per_repo=1, max_parallel_per_tool=1, max_parallel_per_provider=1
        ),
    )
    scheduler.run_once()
    refreshed = service.db.get_task_run(task_run["task_run_id"])
    assert refreshed is not None
    assert refreshed["status"] in {"succeeded", "running", "pending"}
    assert refreshed["claimed_by"] in {"", "scheduler-2"}


def test_scheduler_audit_events_include_task_run_correlation() -> None:
    service = ServerApp()
    _expand_three_tasks(service, plan_id="plan-audit")
    task_run = service.db.list_task_runs("plan-audit")[0]

    scheduler = TaskScheduler(
        db=service.db,
        runner=service.runner,
        worker_id="scheduler-audit",
        quotas=SchedulerQuotas(
            max_parallel_per_repo=1, max_parallel_per_tool=1, max_parallel_per_provider=1
        ),
    )
    scheduler.run_once()

    events = service.db.list_audit_events()
    correlated = [
        event for event in events if event["payload"].get("task_run_id") == task_run["task_run_id"]
    ]
    assert correlated
    assert any(event["payload"].get("run_id") for event in correlated)
