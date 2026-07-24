from typing import Literal

import jjjexperiment.constants as jjj_consts


Season = Literal["H", "C"]
MainOutputNumber = Literal[1, 2]
SeasonalOutputNumber = Literal[3, 4, 5]


def artifact_prefix(case_name: str) -> str:
    return case_name + jjj_consts.version_info()


def input_json_path(case_name: str) -> str:
    return artifact_prefix(case_name) + "_input.json"


def main_output_csv_path(
    case_name: str,
    output_number: MainOutputNumber,
) -> str:
    return artifact_prefix(case_name) + "_output" + str(output_number) + ".csv"


def denchu_constants_csv_path(case_name: str, season: Season) -> str:
    return artifact_prefix(case_name) + "_denchu_consts_" + season + "_output.csv"


def denchu_output_csv_path(case_name: str, season: Season) -> str:
    return artifact_prefix(case_name) + "_denchu_" + season + "_output.csv"


def seasonal_output_csv_path(
    case_name: str,
    season: Season,
    output_number: SeasonalOutputNumber,
) -> str:
    return (
        artifact_prefix(case_name)
        + "_"
        + season
        + "_output"
        + str(output_number)
        + ".csv"
    )


def carryover_output_csv_path(case_name: str, season: Season) -> str:
    return artifact_prefix(case_name) + "_" + season + "_carryover_output.csv"


def underfloor_output_csv_path(prefix: str, season: Season) -> str:
    return prefix + "_" + season + "_output_uf.csv"
