from types import SimpleNamespace

import pytest

from jjjexperiment.inputs import di_container as sut


def _module(input_data):
    module = object.__new__(sut.JJJExperimentModule)
    module._input = input_data
    module._test_mode = False
    module._injector = None
    return module


@pytest.mark.parametrize(
    ("method_name", "target"),
    (
        ("create_houseinfo", sut.common_input.HouseInfo),
        ("provide_outer_skin", sut.common_input.OuterSkin),
        ("provide_heatexchangeventilation", sut.common_input.HEX),
        ("provide_v_supply_cap_dto", sut.VSupplyCapDto),
        ("provide_carryover_heat_dto", sut.CarryoverHeatDto),
        ("provide_underfloor_ac_input", sut.ufac_input.UnderfloorAc),
    ),
)
def test_root_input_providers_pass_the_original_dictionary(
    monkeypatch, method_name, target
):
    input_data = {"root": object()}
    expected = object()
    received = []

    def fake_from_dict(cls, data):
        received.append(data)
        return expected

    monkeypatch.setattr(target, "from_dict", classmethod(fake_from_dict))

    actual = getattr(_module(input_data), method_name)()

    assert actual is expected
    assert received == [input_data]


@pytest.mark.parametrize(
    ("method_name", "target", "input_key"),
    (
        ("provide_heating_ac_setting", sut.HeatingAcSetting, "H_A"),
        ("provide_cooling_ac_setting", sut.CoolingAcSetting, "C_A"),
        (
            "provide_denchu_catalog_heating_input",
            sut.denchu_heating_input.DenchuCatalogSpecification,
            "H_A",
        ),
        (
            "provide_denchu_catalog_cooling_input",
            sut.denchu_cooling_input.DenchuCatalogSpecification,
            "C_A",
        ),
        (
            "provide_v_min_heating_input",
            sut.v_min_heating_input.InputMinVolumeInput,
            "H_A",
        ),
        (
            "provide_v_min_cooling_input",
            sut.v_min_cooling_input.InputMinVolumeInput,
            "C_A",
        ),
    ),
)
def test_season_input_providers_pass_the_original_partial_dictionary(
    monkeypatch, method_name, target, input_key
):
    partial_input = {"partial": object()}
    input_data = {input_key: partial_input}
    expected = object()
    received = []

    def fake_from_dict(cls, data):
        received.append(data)
        return expected

    monkeypatch.setattr(target, "from_dict", classmethod(fake_from_dict))

    actual = getattr(_module(input_data), method_name)()

    assert actual is expected
    assert received == [partial_input]


@pytest.mark.parametrize("input_data", (None, {}, {"H_A": {}}))
def test_missing_cooling_input_is_passed_as_an_empty_dictionary(
    monkeypatch, input_data
):
    received = []

    def fake_from_dict(cls, data):
        received.append(data)
        return object()

    monkeypatch.setattr(
        sut.CoolingAcSetting, "from_dict", classmethod(fake_from_dict)
    )

    _module(input_data).provide_cooling_ac_setting()

    assert received == [{}]


def test_common_cooling_provider_preserves_input_and_house_area(monkeypatch):
    cooling_input = {"cooling": object()}
    expected = object()
    received = []
    module = _module({"C_A": cooling_input})
    monkeypatch.setattr(
        module, "create_houseinfo", lambda: SimpleNamespace(A_A=123.4)
    )

    def fake_from_dict(cls, data, A_A):
        received.append((data, A_A))
        return expected

    monkeypatch.setattr(
        sut.common_cooling_input.CRACSpecification,
        "from_dict",
        classmethod(fake_from_dict),
    )

    actual = module.provide_common_cooling_crac_input()

    assert actual is expected
    assert received == [(cooling_input, 123.4)]


def test_common_heating_provider_preserves_input_and_cooling_values(monkeypatch):
    heating_input = {"heating": object()}
    cooling = SimpleNamespace(q_rtd=1.0, q_max=2.0, e_rtd=3.0)
    expected = object()
    received = []
    module = _module({"H_A": heating_input})
    monkeypatch.setattr(
        module, "provide_common_cooling_crac_input", lambda: cooling
    )

    def fake_from_dict(cls, data, q_rtd_C, q_max_C, e_rtd_C):
        received.append((data, q_rtd_C, q_max_C, e_rtd_C))
        return expected

    monkeypatch.setattr(
        sut.common_heating_input.CRACSpecification,
        "from_dict",
        classmethod(fake_from_dict),
    )

    actual = module.provide_common_heating_crac_input()

    assert actual is expected
    assert received == [(heating_input, 1.0, 2.0, 3.0)]
