"""Primitives for the chronological underfloor heat-balance calculation.

The functions in this module express Appendix E equations without deciding the
surrounding HVAC orchestration. Pass 1 and Pass 2 use the same heat balance,
respectively solved backwards and forwards.
"""

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import ArrayLike, NDArray

import pyhees.section3_1_e as appendix_e


HOURS_PER_YEAR = 24 * 365
GROUND_RESPONSE_TERMS = 10
PHI_A_0 = 0.025504994


def get_runup_floor_temperature(
    underfloor_insulation: bool,
    theta_ex_d_t: ArrayLike,
) -> NDArray[np.float64]:
    """Return the Appendix E equation (13) run-up floor temperatures."""
    theta_ex = np.asarray(theta_ex_d_t, dtype=float)
    if theta_ex.shape != (HOURS_PER_YEAR,):
        raise ValueError(
            f"theta_ex_d_t must have shape ({HOURS_PER_YEAR},), "
            f"got {theta_ex.shape}"
        )

    if underfloor_insulation:
        return np.clip(theta_ex, 20.0, 27.0)

    theta_uf = theta_ex.copy()
    below_heating = theta_ex < 20.0
    above_cooling = 27.0 < theta_ex
    theta_uf[below_heating] = theta_ex[below_heating] * 0.7 + 20.0 * 0.3
    theta_uf[above_cooling] = theta_ex[above_cooling] * 0.7 + 27.0 * 0.3
    return theta_uf


@dataclass
class GroundResponseState:
    """State carried between hours by Appendix E equations (9) to (12)."""

    theta_g_avg: float
    r_g: float = 0.15
    theta_uf_prev: float = 0.0
    theta_g_surf_prev: float = 0.0
    theta_dash_g_surf_a_m_prev: NDArray[np.float64] = field(
        default_factory=lambda: np.zeros(GROUND_RESPONSE_TERMS, dtype=float)
    )
    phi_1_a_m: NDArray[np.float64] = field(
        default_factory=lambda: np.array(
            [
                appendix_e.get_phi_1_A_m(m)
                for m in range(1, GROUND_RESPONSE_TERMS + 1)
            ],
            dtype=float,
        )
    )
    r_m: NDArray[np.float64] = field(
        default_factory=lambda: np.array(
            [
                appendix_e.get_r_m(m)
                for m in range(1, GROUND_RESPONSE_TERMS + 1)
            ],
            dtype=float,
        )
    )

    def response_terms(self) -> NDArray[np.float64]:
        """Calculate current-hour terms without advancing the state."""
        q_g_prev = (
            self.theta_uf_prev - self.theta_g_surf_prev
        ) / self.r_g
        return (
            self.phi_1_a_m * q_g_prev
            + self.r_m * self.theta_dash_g_surf_a_m_prev
        )

    def ground_surface_temperature(
        self,
        theta_uf: float,
        response_terms: ArrayLike,
    ) -> float:
        """Calculate equation (9) for a floor temperature."""
        response_sum = float(np.sum(response_terms))
        return (
            (PHI_A_0 / self.r_g) * theta_uf
            + response_sum
            + self.theta_g_avg
        ) / (1.0 + PHI_A_0 / self.r_g)

    def commit(
        self,
        theta_uf: float,
        response_terms: ArrayLike,
    ) -> float:
        """Advance state using the actual current-hour floor temperature."""
        response = np.asarray(response_terms, dtype=float)
        if response.shape != (GROUND_RESPONSE_TERMS,):
            raise ValueError(
                "response_terms must have shape "
                f"({GROUND_RESPONSE_TERMS},), got {response.shape}"
            )

        theta_g_surf = self.ground_surface_temperature(theta_uf, response)
        self.theta_uf_prev = float(theta_uf)
        self.theta_g_surf_prev = theta_g_surf
        self.theta_dash_g_surf_a_m_prev = response.copy()
        return theta_g_surf


def run_up_ground_response(
    theta_uf_runup_d_t: ArrayLike,
    theta_g_avg: float,
    r_g: float = 0.15,
) -> GroundResponseState:
    """Run Appendix E ground response through one preliminary year."""
    theta_uf_runup = np.asarray(theta_uf_runup_d_t, dtype=float)
    if theta_uf_runup.shape != (HOURS_PER_YEAR,):
        raise ValueError(
            f"theta_uf_runup_d_t must have shape ({HOURS_PER_YEAR},), "
            f"got {theta_uf_runup.shape}"
        )

    state = GroundResponseState(theta_g_avg=theta_g_avg, r_g=r_g)
    # The workbook's row immediately before the run-up year evaluates
    # equation (9) at theta_uf=0 with zero response terms. Its resulting
    # surface temperature is therefore the previous-hour state for the first
    # run-up row.
    state.commit(
        theta_uf=0.0,
        response_terms=np.zeros(GROUND_RESPONSE_TERMS, dtype=float),
    )
    for theta_uf in theta_uf_runup:
        response = state.response_terms()
        state.commit(float(theta_uf), response)
    return state


@dataclass(frozen=True)
class UnderfloorHeatBalance:
    """The common linear floor-temperature equation used by both passes."""

    air_heat_capacity: float
    room_conductance: float
    exterior_conductance: float
    ground_conductance: float
    room_weighted_temperature: float
    exterior_weighted_temperature: float
    ground_weighted_temperature: float

    @property
    def total_conductance(self) -> float:
        return (
            self.room_conductance
            + self.exterior_conductance
            + self.ground_conductance
        )

    @property
    def weighted_temperature(self) -> float:
        return (
            self.room_weighted_temperature
            + self.exterior_weighted_temperature
            + self.ground_weighted_temperature
        )

    @property
    def denominator(self) -> float:
        return self.air_heat_capacity + 3.6 * self.total_conductance

    def actual_floor_temperature(self, theta_supply: float) -> float:
        """Solve the heat balance forwards for Pass 2."""
        numerator = (
            self.air_heat_capacity * theta_supply
            + 3.6 * self.weighted_temperature
        )
        return numerator / self.denominator

    def required_supply_temperature(
        self,
        theta_uf_target: float,
        *,
        heating: bool,
    ) -> float:
        """Solve the same heat balance directly backwards for Pass 1."""
        theta_supply = (
            theta_uf_target * self.denominator
            - 3.6 * self.weighted_temperature
        ) / self.air_heat_capacity
        if heating:
            return max(theta_supply, 20.0)
        return min(theta_supply, 27.0)

def calculate_ground_response_history(
    theta_uf_d_t: ArrayLike,
    theta_ex_d_t: ArrayLike,
    underfloor_insulation: bool,
    *,
    r_g: float = 0.15,
) -> NDArray[np.float64]:
    """Return Appendix E response sums for an actual annual floor history."""
    theta_uf = np.asarray(theta_uf_d_t, dtype=float)
    theta_ex = np.asarray(theta_ex_d_t, dtype=float)
    if theta_uf.shape != (HOURS_PER_YEAR,):
        raise ValueError(
            f"theta_uf_d_t must have shape ({HOURS_PER_YEAR},), "
            f"got {theta_uf.shape}"
        )
    if theta_ex.shape != (HOURS_PER_YEAR,):
        raise ValueError(
            f"theta_ex_d_t must have shape ({HOURS_PER_YEAR},), "
            f"got {theta_ex.shape}"
        )

    state = run_up_ground_response(
        get_runup_floor_temperature(underfloor_insulation, theta_ex),
        float(np.average(theta_ex)),
        r_g,
    )
    response_d_t = np.zeros(HOURS_PER_YEAR, dtype=float)
    for hour, floor_temperature in enumerate(theta_uf):
        response = state.response_terms()
        response_d_t[hour] = float(np.sum(response))
        state.commit(float(floor_temperature), response)
    return response_d_t
@dataclass
class SequentialGroundModeInputs:
    """Inputs needed to reproduce the workbook's one-way annual calculation."""

    is_heating: bool
    use_load_dependent_cooling_capacity: bool
    vav: bool
    heat_source_cav: bool
    q_hat_before_ground_d_t: NDArray[np.float64]
    q_hat_base_d_t: NDArray[np.float64]
    q_hat_cs_base_d_t: NDArray[np.float64]
    theta_uf_preliminary_d_t: NDArray[np.float64]
    theta_ex_d_t: NDArray[np.float64]
    theta_star_hbr_d_t: NDArray[np.float64]
    theta_sur_d_t_i: NDArray[np.float64]
    r_supply_des_d_t_i: NDArray[np.float64]
    v_dash_supply_d_t_i: NDArray[np.float64]
    theta_hs_out_d_t: NDArray[np.float64]
    v_vent_g_i: NDArray[np.float64]
    v_hs_min: float
    v_hs_dsgn: float
    q_hs_rtd: float
    q_hs_max_h_d_t: NDArray[np.float64]
    q_hs_max_c_d_t: NDArray[np.float64]
    q_hs_max_cs_d_t: NDArray[np.float64]
    l_h_d_t_i: NDArray[np.float64]
    l_cs_d_t_i: NDArray[np.float64]
    l_cl_d_t_i: NDArray[np.float64]
    l_dash_h_r_d_t_i: NDArray[np.float64]
    l_dash_cs_r_d_t_i: NDArray[np.float64]
    v_vent_l_nr_d_t: NDArray[np.float64]
    l_h_nr_d_t_a: NDArray[np.float64]
    l_cs_nr_d_t_a: NDArray[np.float64]
    a_hcz_i: NDArray[np.float64]
    a_prt_i: NDArray[np.float64]
    a_s_ufac_i: NDArray[np.float64]
    a_nr: float
    a_prt_a: float
    a_s_ufac_a: float
    a_s_ufac_hcz_1f: float
    u_prt: float
    u_s_load: float
    u_s_supply: float
    q: float
    phi: float
    l_uf: float
    r_g: float
    phi_a_0: float
    theta_g_avg: float
    r_a_nr_uf_1f: float
    l_duct_i: NDArray[np.float64]
    hcm: NDArray[np.object_]
    q_hat_cl_signed_d_t: NDArray[np.float64] | None = None
    active_load_d_t: NDArray[np.bool_] | None = None
    theta_supply_d_t: NDArray[np.float64] | None = None


def _floor_reference_state(
    theta_ex: float,
) -> tuple[float, float]:
    """Return the workbook's reference temperature and difference factor."""
    if theta_ex < 20.0:
        return 20.0, 1.0
    if theta_ex <= 27.0:
        return theta_ex, 0.7
    return 27.0, 1.0


def _floor_balance_coefficients(
    inputs: SequentialGroundModeInputs,
    hour: int,
    response: float,
) -> tuple[float, float, float]:
    theta_star, h_star = _floor_reference_state(
        float(inputs.theta_ex_d_t[hour])
    )
    airflow = float(np.sum(inputs.v_dash_supply_d_t_i[:2, hour]))
    air_heat_capacity = appendix_e.get_ro_air() * appendix_e.get_c_p_air() * airflow
    room_conductance = inputs.u_s_supply * inputs.a_s_ufac_a * h_star
    exterior_conductance = inputs.phi * inputs.l_uf
    ground_conductance = (
        (inputs.a_s_ufac_a / inputs.r_g)
        / (1.0 + inputs.phi_a_0 / inputs.r_g)
    )
    weighted_temperature = (
        room_conductance * theta_star
        + exterior_conductance * inputs.theta_ex_d_t[hour]
        + ground_conductance * (response + inputs.theta_g_avg)
    )
    denominator = (
        air_heat_capacity
        + 3.6
        * (room_conductance + exterior_conductance + ground_conductance)
    )
    return air_heat_capacity, weighted_temperature, denominator


def _floor_temperature_from_supply(
    inputs: SequentialGroundModeInputs,
    hour: int,
    response: float,
    theta_supply: float,
) -> float:
    air_heat_capacity, weighted_temperature, denominator = (
        _floor_balance_coefficients(inputs, hour, response)
    )
    return float(
        (air_heat_capacity * theta_supply + 3.6 * weighted_temperature)
        / denominator
    )


def _room_supply_temperature(
    inputs: SequentialGroundModeInputs,
    hour: int,
    response: float,
    theta_hs_out: float,
) -> float:
    """Return Excel floor13's supply temperature after the underfloor path."""
    airflow = float(np.sum(inputs.v_dash_supply_d_t_i[:2, hour]))
    air_heat_capacity = appendix_e.get_ro_air() * appendix_e.get_c_p_air() * airflow
    room_conductance = inputs.u_s_supply * inputs.a_s_ufac_a
    exterior_conductance = inputs.phi * inputs.l_uf
    ground_conductance = (
        (inputs.a_s_ufac_a / inputs.r_g)
        / (1.0 + inputs.phi_a_0 / inputs.r_g)
    )
    theta_room = 20.0 if inputs.is_heating else 27.0
    numerator = (
        air_heat_capacity * theta_hs_out
        + 3.6
        * (
            room_conductance * theta_room
            + exterior_conductance * inputs.theta_ex_d_t[hour]
            + ground_conductance * (response + inputs.theta_g_avg)
        )
    )
    denominator = air_heat_capacity + 3.6 * (
        room_conductance + exterior_conductance + ground_conductance
    )
    return float(numerator / denominator)

def _required_supply_temperature(
    inputs: SequentialGroundModeInputs,
    hour: int,
    response: float,
    theta_uf_target: float,
) -> float:
    airflow = float(np.sum(inputs.v_dash_supply_d_t_i[:2, hour]))
    air_heat_capacity = (
        appendix_e.get_ro_air() * appendix_e.get_c_p_air() * airflow
    )
    room_conductance = inputs.u_s_supply * inputs.a_s_ufac_a
    exterior_conductance = inputs.phi * inputs.l_uf
    ground_conductance = (
        (inputs.a_s_ufac_a / inputs.r_g)
        / (1.0 + inputs.phi_a_0 / inputs.r_g)
    )
    theta_room = 20.0 if inputs.is_heating else 27.0
    weighted_temperature = (
        room_conductance * theta_room
        + exterior_conductance * inputs.theta_ex_d_t[hour]
        + ground_conductance * (response + inputs.theta_g_avg)
    )
    denominator = air_heat_capacity + 3.6 * (
        room_conductance + exterior_conductance + ground_conductance
    )
    if air_heat_capacity <= 0:
        return theta_uf_target
    theta_supply = (
        theta_uf_target * denominator - 3.6 * weighted_temperature
    ) / air_heat_capacity
    if inputs.is_heating:
        return max(float(theta_supply), 20.0)
    return min(float(theta_supply), 27.0)


def _v_dash_hs_scalar(
    inputs: SequentialGroundModeInputs,
    q_hat_hs: float,
) -> float:
    if inputs.heat_source_cav:
        return inputs.v_hs_dsgn
    if q_hat_hs < inputs.q_hs_rtd:
        return float(
            (inputs.v_hs_dsgn - inputs.v_hs_min)
            / inputs.q_hs_rtd
            * max(q_hat_hs, 0.0)
            + inputs.v_hs_min
        )
    return inputs.v_hs_dsgn


def _mode_floor_temperature(
    inputs: SequentialGroundModeInputs,
    hour: int,
    response: float,
) -> float:
    import pyhees.section4_2 as ducted
    import jjjexperiment.constants as constants
    import jjjexperiment.underfloor_ac.section4_2_jjj as floor_formulas
    from jjjexperiment.underfloor_ac.section4_2_f52_jjj import get_Theta_star_NR

    ground_delta = floor_formulas.calc_delta_L_uf2gnd(
        1.0 if inputs.is_heating else None,
        None if inputs.is_heating else 1.0,
        inputs.a_s_ufac_a,
        inputs.r_g,
        inputs.phi_a_0,
        inputs.theta_uf_preliminary_d_t[hour],
        response,
        inputs.theta_g_avg,
    )
    adjusted = inputs.q_hat_before_ground_d_t[hour] + ground_delta
    if inputs.is_heating:
        q_hat_hs = max(adjusted, 0.0)
    else:
        sensible = max(adjusted, 0.0)
        latent = max(
            inputs.q_hat_cl_signed_d_t[hour]
            if inputs.q_hat_cl_signed_d_t is not None
            else inputs.q_hat_base_d_t[hour]
            - inputs.q_hat_cs_base_d_t[hour],
            0.0,
        )
        q_hat_hs = sensible + latent
    v_dash_hs = _v_dash_hs_scalar(inputs, q_hat_hs)
    v_dash_supply_i = np.maximum(
        inputs.r_supply_des_d_t_i[:, hour] * v_dash_hs,
        inputs.v_vent_g_i[:5],
    )
    inputs.v_dash_supply_d_t_i[:, hour] = v_dash_supply_i

    theta_star_nr = get_Theta_star_NR(
        Theta_star_HBR=inputs.theta_star_hbr_d_t[hour],
        Q=inputs.q,
        A_NR=inputs.a_nr,
        V_vent_l_NR=inputs.v_vent_l_nr_d_t[hour],
        V_dash_supply_A=float(np.sum(v_dash_supply_i)),
        U_prt=inputs.u_prt,
        A_prt_A=inputs.a_prt_a,
        L_H_NR_A=inputs.l_h_nr_d_t_a[hour],
        L_CS_NR_A=inputs.l_cs_nr_d_t_a[hour],
        Theta_NR=20.0 if inputs.is_heating else 27.0,
        Theta_uf=inputs.theta_uf_preliminary_d_t[hour],
        HCM=inputs.hcm[hour],
        r_A_NR_1F=inputs.r_a_nr_uf_1f,
    )
    q_partition_i = (
        inputs.u_prt
        * inputs.a_prt_i[:5]
        * (inputs.theta_star_hbr_d_t[hour] - theta_star_nr)
        * 3600.0e-6
    )
    l_star_h_i = np.zeros(5, dtype=float)
    l_star_cs_i = np.zeros(5, dtype=float)
    floor_transfer_i = floor_formulas.calc_delta_L_room2uf_i(
        inputs.u_s_load,
        inputs.a_s_ufac_i,
        inputs.theta_star_hbr_d_t[hour] - inputs.theta_ex_d_t[hour],
    )[:5, 0]
    if inputs.is_heating:
        active = inputs.l_h_d_t_i[:5, hour] > 0
        l_star_h_i[active] = np.maximum(
            inputs.l_h_d_t_i[:5, hour][active]
            + q_partition_i[active]
            - floor_transfer_i[active],
            0.0,
        )
    else:
        active = inputs.l_cs_d_t_i[:5, hour] > 0
        l_star_cs_i[active] = np.maximum(
            inputs.l_cs_d_t_i[:5, hour][active]
            - q_partition_i[active]
            - floor_transfer_i[active],
            0.0,
        )

    contact = np.array([appendix_e.get_r_A_uf_i(i) for i in (1, 2)])
    v_first_floor = float(np.sum(contact * v_dash_supply_i[:2]))
    q_air = appendix_e.get_ro_air() * appendix_e.get_c_p_air() * v_first_floor
    q_floor = inputs.u_s_supply * inputs.a_s_ufac_hcz_1f * 3.6
    if inputs.is_heating:
        first_floor_load = float(np.sum(contact * l_star_h_i[:2]) * 1000.0)
        theta_uf_target = (
            first_floor_load + 20.0 * (q_air + q_floor)
        ) / (q_air + q_floor)
    else:
        first_floor_load = float(np.sum(contact * l_star_cs_i[:2]) * 1000.0)
        theta_uf_target = (
            -first_floor_load + 27.0 * (q_air + q_floor)
        ) / (q_air + q_floor)

    c_p_air = ducted.get_c_p_air()
    rho_air = ducted.get_rho_air()
    phi_i = ducted.get_phi_i()
    if inputs.is_heating:
        required_i = inputs.theta_sur_d_t_i[:, hour] + (
            inputs.theta_star_hbr_d_t[hour]
            + l_star_h_i * 1.0e6 / (c_p_air * rho_air * v_dash_supply_i)
            - inputs.theta_sur_d_t_i[:, hour]
        ) * np.exp(
            phi_i * inputs.l_duct_i * 3600.0
            / (c_p_air * rho_air * v_dash_supply_i)
        )
        required_i = np.maximum(required_i, inputs.theta_star_hbr_d_t[hour])
    else:
        required_i = inputs.theta_sur_d_t_i[:, hour] - (
            inputs.theta_sur_d_t_i[:, hour]
            - inputs.theta_star_hbr_d_t[hour]
            + l_star_cs_i * 1.0e6 / (c_p_air * rho_air * v_dash_supply_i)
        ) * np.exp(
            phi_i * inputs.l_duct_i * 3600.0
            / (c_p_air * rho_air * v_dash_supply_i)
        )
        required_i = np.minimum(required_i, inputs.theta_star_hbr_d_t[hour])
    required_i[:2] = _required_supply_temperature(
        inputs, hour, response, theta_uf_target
    )
    required_i = (
        np.maximum(required_i, 20.0)
        if inputs.is_heating
        else np.minimum(required_i, 27.0)
    )

    total_load = float(np.sum(l_star_h_i if inputs.is_heating else l_star_cs_i))
    assert inputs.active_load_d_t is not None
    inputs.active_load_d_t[hour] = total_load > 0
    if total_load <= 0:
        theta_hs_out = theta_star_nr
    elif inputs.vav or constants.change_heat_source_outlet_required_temperature == 2:
        theta_hs_out = float(
            np.max(required_i) if inputs.is_heating else np.min(required_i)
        )
    else:
        theta_hs_out = float(
            np.sum(required_i * v_dash_supply_i) / np.sum(v_dash_supply_i)
        )

    if inputs.is_heating:
        maximum_outlet = np.clip(
            theta_star_nr
            + inputs.q_hs_max_h_d_t[hour]
            * 1.0e6
            / (c_p_air * rho_air * np.sum(v_dash_supply_i)),
            None,
            constants.Theta_hs_out_max_H_d_t_limit,
        )
        theta_hs_out = min(theta_hs_out, float(maximum_outlet))
    else:
        if inputs.use_load_dependent_cooling_capacity:
            sensible = float(np.sum(l_star_cs_i))
            latent = float(
                np.sum(
                    np.where(
                        inputs.l_cs_d_t_i[:5, hour] > 0,
                        inputs.l_cl_d_t_i[:5, hour],
                        0.0,
                    )
                )
            )
            latent_adjusted = min(1.5 * sensible, latent)
            total = sensible + latent_adjusted
            shf = sensible / total if total > 0 else 0.0
            q_hs_max_cs = inputs.q_hs_max_c_d_t[hour] * shf
        else:
            q_hs_max_cs = inputs.q_hs_max_cs_d_t[hour]
        minimum_outlet = np.clip(
            theta_star_nr
            - q_hs_max_cs
            * 1.0e6
            / (c_p_air * rho_air * np.sum(v_dash_supply_i)),
            constants.Theta_hs_out_min_C_d_t_limit,
            None,
        )
        theta_hs_out = max(theta_hs_out, float(minimum_outlet))

    inputs.theta_hs_out_d_t[hour] = theta_hs_out
    assert inputs.theta_supply_d_t is not None
    inputs.theta_supply_d_t[hour] = _room_supply_temperature(
        inputs,
        hour,
        response,
        theta_hs_out,
    )
    return _floor_temperature_from_supply(
        inputs, hour, response, theta_hs_out
    )


def solve_shared_ground_sequential(
    heating: SequentialGroundModeInputs,
    cooling: SequentialGroundModeInputs,
    heating_mask: ArrayLike,
    cooling_mask: ArrayLike,
    underfloor_insulation: bool,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Advance Pass 1, controls, Pass 2, and ground state exactly once per hour."""
    heating_hours = np.asarray(heating_mask, dtype=bool)
    cooling_hours = np.asarray(cooling_mask, dtype=bool)
    state = run_up_ground_response(
        get_runup_floor_temperature(
            underfloor_insulation, heating.theta_ex_d_t
        ),
        heating.theta_g_avg,
        heating.r_g,
    )
    floor_d_t = np.zeros(HOURS_PER_YEAR, dtype=float)
    response_d_t = np.zeros(HOURS_PER_YEAR, dtype=float)
    heating.theta_supply_d_t = np.zeros(HOURS_PER_YEAR, dtype=float)
    cooling.theta_supply_d_t = np.zeros(HOURS_PER_YEAR, dtype=float)
    heating.active_load_d_t = np.zeros(HOURS_PER_YEAR, dtype=bool)
    cooling.active_load_d_t = np.zeros(HOURS_PER_YEAR, dtype=bool)
    for hour in range(HOURS_PER_YEAR):
        response = state.response_terms()
        response_d_t[hour] = float(np.sum(response))
        if heating_hours[hour]:
            floor_d_t[hour] = _mode_floor_temperature(
                heating, hour, response_d_t[hour]
            )
        elif cooling_hours[hour]:
            floor_d_t[hour] = _mode_floor_temperature(
                cooling, hour, response_d_t[hour]
            )
        else:
            floor_d_t[hour] = _floor_temperature_from_supply(
                heating, hour, response_d_t[hour], 20.0
            )
        state.commit(floor_d_t[hour], response)
    return floor_d_t, response_d_t
