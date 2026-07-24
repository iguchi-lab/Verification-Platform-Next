import os
import subprocess
import sys

import jjjexperiment.constants as jjj_consts
import pyhees.section4_2_b as dc_spec
import pyhees.section4_3_a as rac_spec


def test_pyhees_scalar_defaults_do_not_import_jjjexperiment():
    script = """
import sys
import pyhees.section4_2_b as dc_spec
import pyhees.section4_3_a as rac_spec
assert 'jjjexperiment.constants' not in sys.modules
assert dc_spec.get_V_fan_dsgn_H(1000.0) == 790.0
assert dc_spec.get_V_fan_dsgn_C(1000.0) == 790.0
assert rac_spec.get_q_rtd_C(100.0) == 5600
"""
    subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )


def test_registered_providers_preserve_direct_constant_assignment(monkeypatch):
    monkeypatch.setattr(jjj_consts, "C_V_fan_dsgn_H", 0.82)
    monkeypatch.setattr(jjj_consts, "C_V_fan_dsgn_C", 0.81)
    monkeypatch.setattr(jjj_consts, "q_rtd_C_limit", 3500.0)

    assert dc_spec.get_V_fan_dsgn_H(1000.0) == 820.0
    assert dc_spec.get_V_fan_dsgn_C(1000.0) == 810.0
    assert rac_spec.get_q_rtd_C(100.0) == 3500.0


def test_registered_providers_preserve_partial_set_constants(monkeypatch):
    monkeypatch.setattr(jjj_consts, "C_V_fan_dsgn_H", 0.79)
    monkeypatch.setattr(jjj_consts, "C_V_fan_dsgn_C", 0.79)
    monkeypatch.setattr(jjj_consts, "q_rtd_C_limit", 5600.0)

    jjj_consts.set_constants({
        "C_V_fan_dsgn_H": "0.82",
        "C_V_fan_dsgn_C": "0.81",
        "q_rtd_C_limit": "3500",
    })

    assert dc_spec.get_V_fan_dsgn_H(1000.0) == 820.0
    assert dc_spec.get_V_fan_dsgn_C(1000.0) == 810.0
    assert rac_spec.get_q_rtd_C(100.0) == 3500.0