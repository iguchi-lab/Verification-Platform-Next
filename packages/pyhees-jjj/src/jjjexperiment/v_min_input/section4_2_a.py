"""Compatibility imports for the former section-style module name."""

from jjjexperiment.v_min_input.fan_power import (
    _solve_cubic_system,
    _solve_linear_system,
    get_E_E_fan_d_t,
)

__all__ = ["get_E_E_fan_d_t", "_solve_linear_system", "_solve_cubic_system"]
