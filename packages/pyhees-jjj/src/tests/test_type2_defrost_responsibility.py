import json
from pathlib import Path

import pytest

from jjjexperiment.main import calc


REGRESSION_INPUT_PATH = (
    Path(__file__).parents[1]
    / "test_utils"
    / "input_region2_grade5_type2.json"
)


def test_region2_grade5_type2_applies_only_rac_defrost_correction():
    """Freeze the verifier-reported region-2 case after separating C_df roles."""
    inputs = json.loads(REGRESSION_INPUT_PATH.read_text(encoding="utf-8"))

    result = calc(inputs, test_mode=True)

    assert result["TValue"].E_H == pytest.approx(70154.48430913354)
    assert result["TValue"].E_C == pytest.approx(2010.0591180227493)
