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