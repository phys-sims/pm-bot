from pm_bot.server.db import OrchestratorDB
from pm_bot.server.estimator import EstimatorService


def _upsert(db: OrchestratorDB, issue_ref: str, **payload: object) -> None:
    db.upsert_work_item(
        issue_ref,
        {
            "title": str(payload.get("title") or issue_ref),
            "type": payload.get("type", "task"),
            "area": payload.get("area", "platform"),
            "size": payload.get("size", "m"),
            "actual_hrs": payload.get("actual_hrs"),
            "fields": {},
            "relationships": {"children_refs": []},
        },
    )


def test_predict_fallback_path_when_exact_bucket_sparse() -> None:
    db = OrchestratorDB()
    estimator = EstimatorService(db=db)

    _upsert(db, "r#1", actual_hrs=4.0, size="m")
    _upsert(db, "r#2", actual_hrs=8.0, size="m")
    _upsert(db, "r#3", actual_hrs=6.0, size="s")

    estimator.build_snapshots()
    prediction = estimator.predict({"type": "task", "area": "platform", "size": "m"})

    assert prediction["bucket_used"] == "type:task|area:platform"
    assert prediction["bucket_rationale"]
    assert len(prediction["fallback_path"]) == 2
    assert prediction["fallback_path"][0]["reason"] == "below_min_samples"
    assert prediction["fallback_path"][1]["reason"] == "selected"


def test_predict_uses_configurable_bucket_thresholds() -> None:
    db = OrchestratorDB()
    estimator = EstimatorService(
        db=db,
        min_samples_by_bucket={"type:task|area:platform|size:m": 2},
        default_min_samples=3,
    )

    _upsert(db, "r#1", actual_hrs=4.0, size="m")
    _upsert(db, "r#2", actual_hrs=8.0, size="m")
    _upsert(db, "r#3", actual_hrs=6.0, size="s")

    estimator.build_snapshots()
    prediction = estimator.predict({"type": "task", "area": "platform", "size": "m"})

    assert prediction["bucket_used"] == "type:task|area:platform|size:m"
    assert prediction["fallback_path"][0]["selected"] is True


def test_quantiles_are_deterministic_nearest_rank() -> None:
    db = OrchestratorDB()
    estimator = EstimatorService(db=db, default_min_samples=1)

    for idx, hrs in enumerate([1.0, 2.0, 3.0, 4.0, 5.0], start=1):
        _upsert(db, f"r#{idx}", actual_hrs=hrs, size="m")

    estimator.build_snapshots()
    prediction = estimator.predict({"type": "task", "area": "platform", "size": "m"})

    assert prediction["p50"] == 3.0
    assert prediction["p80"] == 4.0
    assert prediction["method"] == "nearest-rank"


def test_historical_exclusion_reasons_are_recorded() -> None:
    db = OrchestratorDB()
    estimator = EstimatorService(db=db)

    _upsert(db, "r#1", actual_hrs=2.0)
    _upsert(db, "r#2", actual_hrs=None)
    _upsert(db, "r#3", actual_hrs="oops")
    _upsert(db, "r#4", actual_hrs=0)

    estimator.build_snapshots()

    assert estimator.exclusion_reasons() == {
        "missing_actual_hrs": 1,
        "non_numeric_actual_hrs": 1,
        "non_positive_actual_hrs": 1,
    }

    event = db.list_audit_events("estimator_samples_excluded")[-1]["payload"]
    assert event["excluded_total"] == 3
    assert event["reasons"] == estimator.exclusion_reasons()
