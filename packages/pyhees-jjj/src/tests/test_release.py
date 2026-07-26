import json
from pathlib import Path

import jjjexperiment.main as experiment_main
from jjjexperiment import release


def test_input_sha256_is_independent_of_mapping_order():
    first = {"case_name": "case", "region": 6, "nested": {"b": 2, "a": 1}}
    second = {"nested": {"a": 1, "b": 2}, "region": 6, "case_name": "case"}

    assert release.input_sha256(first) == release.input_sha256(second)
    assert len(release.input_sha256(first)) == 64


def test_source_commit_prefers_deployment_metadata(monkeypatch):
    monkeypatch.setenv("VERIFICATION_SOURCE_COMMIT", "release-commit")

    assert release.source_commit() == "release-commit"


def test_write_artifact_manifest_records_release_and_input(tmp_path, monkeypatch):
    monkeypatch.setenv("VERIFICATION_SOURCE_COMMIT", "0123456789abcdef")
    input_data = {"case_name": "case", "region": 6}
    path = tmp_path / "case_v1.0.0_manifest.json"

    release.write_artifact_manifest(path, input_data)

    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest == {
        "schema_version": 1,
        "product": "Verification Platform Next",
        "version": "1.0.0",
        "display_version": "ver.1.0.0",
        "release_date": "2026-07-26",
        "artifact_version": "_v1.0.0",
        "source_commit": "0123456789abcdef",
        "upstream_pyhees_version": "3.10.0",
        "upstream_pyhees_commit": "d5224c4a01def00a8421bcd2fcc0d4b4a5b88644",
        "underfloor_specification": "floor14",
        "input_sha256": release.input_sha256(input_data),
        "generated_at_utc": manifest["generated_at_utc"],
    }
    assert manifest["generated_at_utc"].endswith("+00:00")


def test_calc_writes_manifest_only_after_success(tmp_path, monkeypatch):
    events = []
    result = object()
    injector = type(
        "InjectorStub",
        (),
        {
            "call_with_injection": lambda self, function: (
                events.append(("calculate", function)),
                result,
            )[1],
        },
    )()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        experiment_main.jjj_consts,
        "set_constants",
        lambda data: events.append(("constants", data)),
    )
    monkeypatch.setattr(
        experiment_main.jjj_ipt_di,
        "create_injector_from_json",
        lambda data, test_mode: (
            events.append(("injector", data, test_mode)),
            injector,
        )[1],
    )
    monkeypatch.setattr(
        experiment_main,
        "write_artifact_manifest",
        lambda path, data: events.append(("manifest", Path(path), data)),
    )

    input_data = {"case_name": "release-case", "region": 6}
    actual = experiment_main.calc(input_data, test_mode=True)

    assert actual is result
    assert json.loads(
        (tmp_path / "release-case_v1.0.0_input.json").read_text(encoding="utf-8")
    ) == input_data
    assert events == [
        ("constants", input_data),
        ("injector", input_data, True),
        ("calculate", experiment_main.calc_main),
        (
            "manifest",
            Path("release-case_v1.0.0_manifest.json"),
            input_data,
        ),
    ]
