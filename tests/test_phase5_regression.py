from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.phase5
def test_legacy_csv_baselines_match_current_platform(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            str(repository_root / "scripts" / "run_phase5_regression.py"),
            "--workdir",
            str(tmp_path),
        ],
        cwd=repository_root,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, (
        completed.stdout.decode(errors="replace")
        + completed.stderr.decode(errors="replace")
    )
