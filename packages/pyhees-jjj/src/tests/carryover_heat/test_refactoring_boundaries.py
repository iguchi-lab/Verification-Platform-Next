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
