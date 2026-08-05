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
    assert "ランタイム > すべてのセルを実行" in introduction
    assert "Running on public URL" in introduction
    assert "gradio.live" in introduction


def test_colab_default_flow_contains_only_setup_and_launch() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    notebook_path = repository_root / "notebooks" / "Verification_Platform_Next.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_sources = [
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]

    assert len(code_sources) == 2
    assert "%pip install -e apps/gradio" in code_sources[0]
    assert code_sources[1].rstrip().endswith("!verification-platform")
    assert all("run_phase5_regression.py" not in source for source in code_sources)


def test_colab_launcher_exposes_the_server_and_enables_diagnostics() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    notebook_path = repository_root / "notebooks" / "Verification_Platform_Next.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    launch_source = "".join(notebook["cells"][2]["source"])

    assert "%env GRADIO_SHARE=1" in launch_source
    assert "%env GRADIO_SERVER_NAME=0.0.0.0" in launch_source
    assert "%env GRADIO_DEBUG=1" in launch_source
    assert "%env GRADIO_STATUS_UPDATE_RATE=1" in launch_source
    assert "import gradio; print('Gradio', gradio.__version__)" in launch_source
    assert launch_source.rstrip().endswith("!verification-platform")
