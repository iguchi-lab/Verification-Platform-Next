from jjjexperiment.underfloor_ac import section4_2_f52_jjj as formula52


def test_get_formula_52_properties_preserves_pyhees_values(monkeypatch):
    monkeypatch.setattr(formula52.dc, 'get_c_p_air', lambda: 1.0)
    monkeypatch.setattr(formula52.dc, 'get_rho_air', lambda: 2.0)
    monkeypatch.setattr(formula52.dc, 'get_U_s', lambda: 3.0)

    assert formula52._get_formula_52_properties() == (1.0, 2.0, 3.0)

def test_get_A_NR_1F_52_preserves_floor_area_ratio():
    assert formula52._get_A_NR_1F_52(100.0, 0.4) == 40.0