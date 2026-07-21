#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import sys

if not ((3, 12, 11) <= sys.version_info[:3] < (3, 13)):
    raise SystemExit(
        "Verification Platform Next requires Python >=3.12.11,<3.13; "
        f"found {sys.version.split()[0]}"
    )
PY

python -m pip install --upgrade pip
python -m pip install --no-cache-dir pytest ruff -e apps/gradio
