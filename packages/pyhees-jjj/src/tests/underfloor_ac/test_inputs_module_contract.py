import jjjexperiment.underfloor_ac.inputs as inputs
from jjjexperiment.underfloor_ac.inputs import common


def test_underfloor_inputs_package_preserves_public_name_set():
    assert {
        name for name in vars(inputs) if not name.startswith("_")
    } == {"UnderfloorAc", "UfVarsDataFrame", "common"}


def test_underfloor_inputs_package_preserves_public_objects():
    assert inputs.UnderfloorAc is common.UnderfloorAc
    assert inputs.UfVarsDataFrame is common.UfVarsDataFrame