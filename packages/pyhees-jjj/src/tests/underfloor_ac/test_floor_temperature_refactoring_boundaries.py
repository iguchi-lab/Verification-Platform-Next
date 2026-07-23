import numpy as np
import pytest

from jjjexperiment.underfloor_ac import section3_1_e_jjj as floor_temperature


def test_get_floor_temperature_properties_and_defaults_preserves_values(monkeypatch):
    monkeypatch.setattr(floor_temperature.algo, 'get_ro_air', lambda: 1.0)
    monkeypatch.setattr(floor_temperature.algo, 'get_c_p_air', lambda: 2.0)
    monkeypatch.setattr(floor_temperature.algo, 'get_U_s', lambda: 3.0)

    assert floor_temperature._get_floor_temperature_properties_and_defaults() == (1.0, 2.0, 3.0, 0.7, 27.0, 20.0)


def test_validate_r_A_ufvnt_preserves_precondition():
    floor_temperature._validate_r_A_ufvnt([0.4, 0.4])
    with pytest.raises(ValueError, match='床下空調に使用する面積の割合が有効な値になっていない'):
        floor_temperature._validate_r_A_ufvnt(None)
    with pytest.raises(ValueError):
        floor_temperature._validate_r_A_ufvnt(0)

def test_get_floor_area_and_supply_preserves_first_floor_weighting(monkeypatch):
    monkeypatch.setattr(floor_temperature.algo, 'calc_A_s_ufvnt_i', lambda i, *_: i * 10.0)
    monkeypatch.setattr(floor_temperature.algo, 'get_r_A_uf_i', lambda i: (0.5, 0.25)[i - 1])
    supply = np.array([[2.0, 4.0, 6.0], [10.0, 20.0, 30.0]])

    area, ratios, weighted_supply = floor_temperature._get_floor_area_and_supply(100.0, 40.0, 30.0, [0.4, 0.4], supply, 2)

    assert area == 30.0
    np.testing.assert_array_equal(ratios, np.array([0.5, 0.25]))
    np.testing.assert_array_equal(weighted_supply, np.array([3.5, 7.0, 10.5]))