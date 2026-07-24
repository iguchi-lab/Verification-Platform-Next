import pytest

import jjjexperiment.artifact_paths as sut


@pytest.mark.parametrize(
    ("builder", "expected"),
    (
        (lambda: sut.input_json_path("case"), "casev-test_input.json"),
        (lambda: sut.main_output_csv_path("case", 1), "casev-test_output1.csv"),
        (lambda: sut.main_output_csv_path("case", 2), "casev-test_output2.csv"),
        (
            lambda: sut.denchu_constants_csv_path("case", "H"),
            "casev-test_denchu_consts_H_output.csv",
        ),
        (
            lambda: sut.denchu_constants_csv_path("case", "C"),
            "casev-test_denchu_consts_C_output.csv",
        ),
        (
            lambda: sut.denchu_output_csv_path("case", "H"),
            "casev-test_denchu_H_output.csv",
        ),
        (
            lambda: sut.denchu_output_csv_path("case", "C"),
            "casev-test_denchu_C_output.csv",
        ),
        (
            lambda: sut.seasonal_output_csv_path("case", "H", 3),
            "casev-test_H_output3.csv",
        ),
        (
            lambda: sut.seasonal_output_csv_path("case", "H", 4),
            "casev-test_H_output4.csv",
        ),
        (
            lambda: sut.seasonal_output_csv_path("case", "H", 5),
            "casev-test_H_output5.csv",
        ),
        (
            lambda: sut.seasonal_output_csv_path("case", "C", 3),
            "casev-test_C_output3.csv",
        ),
        (
            lambda: sut.seasonal_output_csv_path("case", "C", 4),
            "casev-test_C_output4.csv",
        ),
        (
            lambda: sut.seasonal_output_csv_path("case", "C", 5),
            "casev-test_C_output5.csv",
        ),
        (
            lambda: sut.carryover_output_csv_path("case", "H"),
            "casev-test_H_carryover_output.csv",
        ),
        (
            lambda: sut.carryover_output_csv_path("case", "C"),
            "casev-test_C_carryover_output.csv",
        ),
        (
            lambda: sut.underfloor_output_csv_path("case", "H"),
            "casev-test_H_output_uf.csv",
        ),
        (
            lambda: sut.underfloor_output_csv_path("case", "C"),
            "casev-test_C_output_uf.csv",
        ),
    ),
)
def test_artifact_filename_contracts(monkeypatch, builder, expected):
    calls = []

    def version_info():
        calls.append("version")
        return "v-test"

    monkeypatch.setattr(sut.jjj_consts, "version_info", version_info)

    assert builder() == expected
    assert calls == ["version"]
