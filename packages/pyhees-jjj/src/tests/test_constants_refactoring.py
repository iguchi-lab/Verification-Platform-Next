import pytest

import jjjexperiment.constants as constants


@pytest.mark.parametrize(
  ('key', 'value', 'expected'),
  [
    ('Theta_hs_out_max_H_d_t_limit', '47.5', 47.5),
    ('Theta_hs_out_min_C_d_t_limit', '123.5', 123.5),
    ('C_df_H_d_t_defrost_ductcentral', '123.5', 123.5),
    ('defrost_temp_ductcentral', '123.5', 123.5),
    ('defrost_humid_ductcentral', '123.5', 123.5),
    ('phi_i', '123.5', 123.5),
    ('C_V_fan_dsgn_H', '123.5', 123.5),
    ('C_V_fan_dsgn_C', '123.5', 123.5),
    ('C_df_H_d_t_defrost_rac', '123.5', 123.5),
    ('defrost_temp_rac', '123.5', 123.5),
    ('defrost_humid_rac', '123.5', 123.5),
    ('C_hm_C', '123.5', 123.5),
    ('q_rtd_C_limit', '123.5', 123.5),
  ],
)
def test_set_constants_float_boundary(key, value, expected):
  original = getattr(constants, key)
  try:
    constants.set_constants({key: value})
    assert getattr(constants, key) == expected
    assert isinstance(getattr(constants, key), float)

    constants.set_constants({})
    assert getattr(constants, key) == expected
  finally:
    setattr(constants, key, original)


@pytest.mark.parametrize(
  ('key', 'value', 'expected'),
  [
    ('change_supply_volume_before_vav_adjust', '7', 7),
  ],
)
def test_set_constants_int_boundary(key, value, expected):
  original = getattr(constants, key)
  try:
    constants.set_constants({key: value})
    assert getattr(constants, key) == expected
    assert isinstance(getattr(constants, key), int)

    constants.set_constants({})
    assert getattr(constants, key) == expected
  finally:
    setattr(constants, key, original)
