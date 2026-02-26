from __future__ import annotations

import subprocess


def test_docs_hygiene_script_passes() -> None:
    result = subprocess.run(
        [
            "python",
            "scripts/docs_hygiene.py",
            "--check-links",
            "--check-contradictions",
            "--check-status-gates",
            "--check-depth-metadata",
            "--check-l0-bloat",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
