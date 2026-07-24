"""Compatibility imports for the former section-style module name."""

from jjjexperiment.latent_load.compressor_efficiency import (
    get_e_r_C_d_t,
    get_e_r_H_d_t,
)
from jjjexperiment.latent_load.fan_power import (
    _calc_E_E_fan_d_t,
    _calc_polynomial_4th,
    get_E_E_fan_C_d_t,
    get_E_E_fan_H_d_t,
)

__all__ = [
    "get_e_r_H_d_t",
    "get_e_r_C_d_t",
    "get_E_E_fan_H_d_t",
    "get_E_E_fan_C_d_t",
    "_calc_polynomial_4th",
    "_calc_E_E_fan_d_t",
]
