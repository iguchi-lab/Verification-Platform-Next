from pathlib import Path


def test_cloud_run_keeps_one_calculation_queue_instance() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    workflow = (
        repository_root / ".github" / "workflows" / "deploy-cloud-run.yml"
    ).read_text(encoding="utf-8")

    assert "--concurrency 20" in workflow
    assert "--max-instances 1" in workflow
    assert "GRADIO_QUEUE_MAX_SIZE=5" in workflow
    assert "VERIFICATION_RESULT_TTL_SECONDS=86400" in workflow


def test_container_has_safe_queue_and_result_retention_defaults() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    dockerfile = (repository_root / "Dockerfile").read_text(encoding="utf-8")

    assert "GRADIO_QUEUE_MAX_SIZE=5" in dockerfile
    assert "VERIFICATION_RESULT_TTL_SECONDS=86400" in dockerfile
