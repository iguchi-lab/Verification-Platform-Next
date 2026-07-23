import numpy as np
import pytest

from jjjexperiment.carryover_heat import section4_2


def test_prepare_carryover_zone_areas_preserves_shape_contract():
    areas = np.arange(1.0, 6.0)
    temperatures = np.zeros((5, 1))

    result = section4_2._prepare_carryover_zone_areas(areas, temperatures)

    np.testing.assert_array_equal(result, areas.reshape(5, 1))
    with pytest.raises(AssertionError):
        section4_2._prepare_carryover_zone_areas(areas.reshape(5, 1), temperatures)


def test_get_carryover_C_BR_i_delegates_with_reshaped_areas(monkeypatch):
    areas = np.arange(1.0, 6.0).reshape(5, 1)
    expected = np.full((5, 1), 42.0)
    monkeypatch.setattr(section4_2.jjj_carryover_heat, 'get_C_BR_i', lambda value: expected if value is areas else None)

    result = section4_2._get_carryover_C_BR_i(areas)

    assert result is expected


def test_get_carryover_temperature_diff_preserves_season_branches():
    temperatures = np.arange(20.0, 25.0).reshape(5, 1)

    np.testing.assert_array_equal(
        section4_2._get_carryover_temperature_diff(np.True_, np.False_, temperatures, 21.0),
        temperatures - 21.0,
    )
    np.testing.assert_array_equal(
        section4_2._get_carryover_temperature_diff(np.False_, np.True_, temperatures, 21.0),
        21.0 - temperatures,
    )
    assert section4_2._get_carryover_temperature_diff(np.False_, np.False_, temperatures, 21.0) is None
    with pytest.raises(ValueError):
        section4_2._get_carryover_temperature_diff(np.True_, np.True_, temperatures, 21.0)


def test_calculate_carryover_result_preserves_units_and_capacity_contract():
    capacities = np.full((5, 1), 2_000_000.0)
    temperature_diff = np.arange(-2.0, 3.0).reshape(5, 1)

    result = section4_2._calculate_carryover_result(capacities, temperature_diff)

    np.testing.assert_array_equal(result, 2.0 * temperature_diff)
    with pytest.raises(AssertionError):
        section4_2._calculate_carryover_result(-capacities, temperature_diff)


def test_assert_Theta_HBR_i_2023_shapes_checks_all_zone_arrays():
    valid = np.zeros((5, 1))
    section4_2._assert_Theta_HBR_i_2023_shapes(*([valid] * 7))

    with pytest.raises(AssertionError):
        section4_2._assert_Theta_HBR_i_2023_shapes(valid.reshape(1, 5), *([valid] * 6))


def test_get_c_prt_46_preserves_hourly_conductance_units():
    areas = np.arange(1.0, 6.0).reshape(5, 1)
    np.testing.assert_array_equal(section4_2._get_c_prt_46(2.5, areas), 2.5 * areas * 3600)


def test_get_heat_loss_46_preserves_hourly_heat_loss_units():
    areas = np.arange(1.0, 6.0).reshape(5, 1)
    np.testing.assert_array_equal(section4_2._get_heat_loss_46(2.5, areas), 2.5 * areas * 3600)


def test_get_C_BR_i_46_preserves_capacity_lookup(monkeypatch):
    areas = np.arange(1.0, 6.0).reshape(5, 1)
    expected = np.full((5, 1), 99.0)
    monkeypatch.setattr(section4_2.jjj_carryover_heat, 'get_C_BR_i', lambda value: expected if value is areas else None)
    assert section4_2._get_C_BR_i_46(areas) is expected


def test_get_ac_capacity_46_preserves_air_capacity_and_absolute_difference(monkeypatch):
    monkeypatch.setattr(section4_2.dc, 'get_c_p_air', lambda: 2.0)
    monkeypatch.setattr(section4_2.dc, 'get_rho_air', lambda: 3.0)
    supply_volume = np.arange(1.0, 6.0).reshape(5, 1)
    supply_temperature = np.arange(18.0, 23.0).reshape(5, 1)

    c_ac_air, ac_capacity = section4_2._get_ac_capacity_46(supply_volume, supply_temperature, 20.0)

    np.testing.assert_array_equal(c_ac_air, 6.0 * supply_volume)
    np.testing.assert_array_equal(ac_capacity, c_ac_air * np.abs(supply_temperature - 20.0))


def test_get_Theta_HBR_i_46_preserves_season_equations():
    shape = (5, 1)
    ac_capacity = np.full(shape, 30.0)
    c_ac_air = np.full(shape, 2.0)
    c_prt = np.full(shape, 3.0)
    heat_loss = np.full(shape, 4.0)
    cbri = np.full(shape, 1.0)
    heating_load = np.full(shape, 0.00001)
    cooling_load = np.full(shape, 0.00002)

    heating = section4_2._get_Theta_HBR_i_46(True, False, False, 20.0, heating_load, cooling_load, ac_capacity, c_ac_air, c_prt, heat_loss, cbri)
    cooling = section4_2._get_Theta_HBR_i_46(False, True, False, 20.0, heating_load, cooling_load, ac_capacity, c_ac_air, c_prt, heat_loss, cbri)
    middle = section4_2._get_Theta_HBR_i_46(False, False, True, 20.0, heating_load, cooling_load, ac_capacity, c_ac_air, c_prt, heat_loss, cbri)

    np.testing.assert_array_equal(heating, np.full(shape, 22.0))
    np.testing.assert_array_equal(cooling, np.full(shape, 19.0))
    np.testing.assert_array_equal(middle, np.full(shape, 20.0))
    with pytest.raises(ValueError):
        section4_2._get_Theta_HBR_i_46(True, True, False, 20.0, heating_load, cooling_load, ac_capacity, c_ac_air, c_prt, heat_loss, cbri)


def test_return_Theta_HBR_i_46_preserves_output_shape_contract():
    temperatures = np.zeros((5, 1))
    assert section4_2._return_Theta_HBR_i_46(temperatures) is temperatures
    with pytest.raises(AssertionError):
        section4_2._return_Theta_HBR_i_46(np.zeros(5))


def test_assert_Theta_NR_2023_shapes_checks_four_zone_arrays():
    valid = np.zeros((5, 1))
    section4_2._assert_Theta_NR_2023_shapes(*([valid] * 4))

    with pytest.raises(AssertionError):
        section4_2._assert_Theta_NR_2023_shapes(valid, np.zeros(5), valid, valid)


def test_get_c_prt_48_preserves_watts_per_kelvin_units():
    areas = np.arange(1.0, 6.0).reshape(5, 1)
    np.testing.assert_array_equal(section4_2._get_c_prt_48(2.5, areas), 2.5 * areas)


def test_get_air_properties_48_preserves_pyhees_values(monkeypatch):
    monkeypatch.setattr(section4_2.dc, 'get_c_p_air', lambda: 1006.0)
    monkeypatch.setattr(section4_2.dc, 'get_rho_air', lambda: 1.2)
    assert section4_2._get_air_properties_48() == (1006.0, 1.2)


def test_get_k_prt_dash_i_48_preserves_formula_48d():
    volume = np.arange(1.0, 6.0).reshape(5, 1) * 3600
    c_prt = np.full((5, 1), 7.0)
    np.testing.assert_array_equal(section4_2._get_k_prt_dash_i_48(2.0, 3.0, volume, c_prt), 6.0 * volume / 3600 + c_prt)


def test_get_k_prt_i_48_preserves_formula_48c():
    volume = np.arange(1.0, 6.0).reshape(5, 1) * 3600
    c_prt = np.full((5, 1), 7.0)
    np.testing.assert_array_equal(section4_2._get_k_prt_i_48(2.0, 3.0, volume, c_prt), 6.0 * volume / 3600 + c_prt)


def test_get_k_evp_48_preserves_formula_48b():
    expected = (2.5 - 0.35 * 0.5 * 2.4) * 40.0 + 1006.0 * 1.2 * (120.0 / 3600)
    assert section4_2._get_k_evp_48(2.5, 40.0, 1006.0, 1.2, 120.0) == expected


def test_get_balance_terms_48_preserves_val1_val2_val3():
    k_dash = np.full((5, 1), 2.0)
    k_prt = np.full((5, 1), 3.0)
    temperatures = np.arange(18.0, 23.0).reshape(5, 1)
    result = section4_2._get_balance_terms_48(k_dash, k_prt, 20.0, 18.0, temperatures, 4.0)
    assert result == (-20.0, 30.0, 19.0)


def test_get_carryover_state_48_preserves_activation_and_capacity(monkeypatch):
    monkeypatch.setattr(section4_2.jjj_carryover_heat, 'get_C_NR', lambda area: 3600.0 if area == 40.0 else None)

    assert section4_2._get_carryover_state_48(False, True, False, 19.0, 18.0, 40.0) == (True, False, 1.0, 1.0)
    assert section4_2._get_carryover_state_48(False, True, False, 17.0, 18.0, 40.0) == (False, False, 0, 0)
    assert section4_2._get_carryover_state_48(False, False, True, 17.0, 18.0, 40.0) == (False, True, -1.0, 1.0)
    assert section4_2._get_carryover_state_48(True, True, False, 19.0, 18.0, 40.0) == (True, False, 1.0, 0)
    with pytest.raises(ValueError):
        section4_2._get_carryover_state_48(False, True, True, 18.0, 18.0, 40.0)


def test_get_Theta_NR_48_preserves_formula_clip_and_float_contract():
    neutral = section4_2._get_Theta_NR_48(18.0, 1.0, 2.0, 0.0, 0.0, 6.0, False, False, 20.0)
    heating = section4_2._get_Theta_NR_48(18.0, 12.0, 0.0, 0.0, 0.0, 1.0, True, False, 20.0)
    cooling = section4_2._get_Theta_NR_48(18.0, -12.0, 0.0, 0.0, 0.0, 1.0, False, True, 20.0)

    assert neutral == 18.5
    assert heating == 20.0
    assert cooling == 20.0
    assert isinstance(neutral, float)
