import json
from pathlib import Path


def test_colab_setup_is_repeatable_and_uses_one_dependency_entrypoint() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    notebook_path = repository_root / "notebooks" / "Verification_Platform_Next.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    setup_source = "".join(notebook["cells"][1]["source"])

    assert setup_source.startswith("%cd /content\n")
    assert "[ -d Verification-Platform-Next/.git ] || git clone" in setup_source
    assert "git -C Verification-Platform-Next pull --ff-only" in setup_source
    assert "%cd /content/Verification-Platform-Next" in setup_source

    pip_commands = [
        line for line in setup_source.splitlines() if line.startswith("%pip install")
    ]
    assert pip_commands == ["%pip install -e apps/gradio"]


def test_colab_notebook_links_to_the_main_branch_launcher() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    notebook_path = repository_root / "notebooks" / "Verification_Platform_Next.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    introduction = "".join(notebook["cells"][0]["source"])

    assert "https://colab.research.google.com/assets/colab-badge.svg" in introduction
    assert (
        "https://colab.research.google.com/github/iguchi-lab/"
        "Verification-Platform-Next/blob/main/notebooks/"
        "Verification_Platform_Next.ipynb"
    ) in introduction
