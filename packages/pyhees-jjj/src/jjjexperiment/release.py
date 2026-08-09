"""Release identity and calculation artifact provenance."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


VERSION = "1.0.2"
DISPLAY_VERSION = "ver.1.0.2"
RELEASE_DATE = "2026-08-09"
ARTIFACT_VERSION = "_v1.0.2"

UPSTREAM_PYHEES_VERSION = "3.10.0"
UPSTREAM_PYHEES_COMMIT = "d5224c4a01def00a8421bcd2fcc0d4b4a5b88644"
UNDERFLOOR_SPECIFICATION = "floor14"


def canonical_input_json(input_data: Mapping[str, Any]) -> str:
    """Return a stable JSON representation used only for provenance hashing."""
    return json.dumps(
        input_data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def input_sha256(input_data: Mapping[str, Any]) -> str:
    """Return the SHA-256 digest of the canonical calculation input."""
    return hashlib.sha256(canonical_input_json(input_data).encode("utf-8")).hexdigest()


def source_commit() -> str:
    """Resolve the exact source revision, preferring deployment metadata."""
    configured_commit = os.environ.get("VERIFICATION_SOURCE_COMMIT")
    if configured_commit:
        return configured_commit

    for parent in Path(__file__).resolve().parents:
        if not (parent / ".git").exists():
            continue
        try:
            completed = subprocess.run(
                ["git", "-C", str(parent), "rev-parse", "HEAD"],
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return "unknown"
        if completed.returncode == 0:
            return completed.stdout.strip()
        break
    return "unknown"


def build_artifact_manifest(input_data: Mapping[str, Any]) -> dict[str, Any]:
    """Build metadata that makes an output reproducible and auditable."""
    return {
        "schema_version": 1,
        "product": "Verification Platform Next",
        "version": VERSION,
        "display_version": DISPLAY_VERSION,
        "release_date": RELEASE_DATE,
        "artifact_version": ARTIFACT_VERSION,
        "source_commit": source_commit(),
        "upstream_pyhees_version": UPSTREAM_PYHEES_VERSION,
        "upstream_pyhees_commit": UPSTREAM_PYHEES_COMMIT,
        "underfloor_specification": UNDERFLOOR_SPECIFICATION,
        "input_sha256": input_sha256(input_data),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def write_artifact_manifest(
    path: str | Path,
    input_data: Mapping[str, Any],
) -> None:
    """Write provenance metadata after a calculation has completed."""
    Path(path).write_text(
        json.dumps(build_artifact_manifest(input_data), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
