from pathlib import Path

from pm_bot.control_plane.db.db import OrchestratorDB
from pm_bot.shared.settings import get_storage_settings


def test_storage_settings_create_local_first_directories(tmp_path: Path) -> None:
    env = {
        "PMBOT_DATA_DIR": str(tmp_path / "data"),
        "PMBOT_SQLITE_PATH": str(tmp_path / "data" / "control_plane" / "pm_bot.sqlite"),
        "PMBOT_ARTIFACT_DIR": str(tmp_path / "data" / "artifacts"),
        "PMBOT_CHECKPOINT_DIR": str(tmp_path / "data" / "checkpoints"),
        "PMBOT_REPOS_DIR": str(tmp_path / "data" / "repos"),
    }

    settings = get_storage_settings(env)

    assert settings.data_dir.exists()
    assert settings.sqlite_path.parent.exists()
    assert settings.artifact_dir.exists()
    assert settings.checkpoint_dir.exists()
    assert settings.repos_dir.exists()


def test_sqlite_connection_uses_wal_and_busy_timeout(tmp_path: Path) -> None:
    db = OrchestratorDB(tmp_path / "control_plane" / "pm_bot.sqlite")

    journal_mode = db.conn.execute("PRAGMA journal_mode").fetchone()[0]
    busy_timeout = db.conn.execute("PRAGMA busy_timeout").fetchone()[0]

    assert str(journal_mode).lower() == "wal"
    assert int(busy_timeout) == 5000
