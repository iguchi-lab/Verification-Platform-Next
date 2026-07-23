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
