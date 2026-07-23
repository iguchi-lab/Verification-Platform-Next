from jjjexperiment.underfloor_ac import section4_2_f40_jjj as formula40


def test_get_formula_40_properties_preserves_pyhees_values(monkeypatch):
    monkeypatch.setattr(formula40.dc, 'get_c_p_air', lambda: 1.0)
    monkeypatch.setattr(formula40.dc, 'get_rho_air', lambda: 2.0)
    monkeypatch.setattr(formula40.dc, 'get_Theta_set_H', lambda: 3.0)
    monkeypatch.setattr(formula40.dc, 'get_Theta_set_C', lambda: 4.0)
    monkeypatch.setattr(formula40.dc, 'get_X_set_C', lambda: 5.0)

    assert formula40._get_formula_40_properties() == (1.0, 2.0, 3.0, 4.0, 5.0)
