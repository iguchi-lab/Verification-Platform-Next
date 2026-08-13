from pathlib import Path
import tomllib

from jjjexperiment import release


ROOT = Path(__file__).resolve().parents[1]


def _project_version(path: str) -> str:
    with (ROOT / path).open("rb") as file:
        return tomllib.load(file)["tool"]["poetry"]["version"]


def test_release_version_is_consistent_across_projects():
    assert release.VERSION == "1.2.0"
    assert release.DISPLAY_VERSION == "ver.1.2.0"
    assert release.ARTIFACT_VERSION == "_v1.2.0"
    assert {
        _project_version("pyproject.toml"),
        _project_version("packages/verification-core/pyproject.toml"),
        _project_version("packages/pyhees-jjj/pyproject.toml"),
        _project_version("apps/gradio/pyproject.toml"),
    } == {release.VERSION}
