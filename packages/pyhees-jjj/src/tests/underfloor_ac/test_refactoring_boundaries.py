from jjjexperiment.underfloor_ac import section4_2_f40_jjj as formula40


def test_get_formula_40_properties_preserves_pyhees_values(monkeypatch):
    monkeypatch.setattr(formula40.dc, 'get_c_p_air', lambda: 1.0)
    monkeypatch.setattr(formula40.dc, 'get_rho_air', lambda: 2.0)
    monkeypatch.setattr(formula40.dc, 'get_Theta_set_H', lambda: 3.0)
    monkeypatch.setattr(formula40.dc, 'get_Theta_set_C', lambda: 4.0)
    monkeypatch.setattr(formula40.dc, 'get_X_set_C', lambda: 5.0)

    assert formula40._get_formula_40_properties() == (1.0, 2.0, 3.0, 4.0, 5.0)


def test_get_Q_hat_hs_H_envelope_40_1b_preserves_envelope_and_ventilation():
    result = formula40._get_Q_hat_hs_H_envelope_40_1b(2.5, 100.0, 1000.0, 1.2, 120.0, 60.0, 20.0, 5.0)
    expected = ((2.5 - 0.35 * 0.5 * 2.4) * 100.0 + 1000.0 * 1.2 * 180.0 / 3600) * 15.0
    assert result == expected
