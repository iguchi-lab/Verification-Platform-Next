from jjjexperiment import common
from pyhees import jjj_markers


def test_jjj_markers_are_identity_decorators():
    def target():
        return "unchanged"

    assert jjj_markers.jjj_cloning(target) is target
    assert jjj_markers.jjj_cloned(target) is target
    assert jjj_markers.jjj_mod(target) is target


def test_jjjexperiment_common_reexports_marker_objects():
    assert common.jjj_cloning is jjj_markers.jjj_cloning
    assert common.jjj_cloned is jjj_markers.jjj_cloned
    assert common.jjj_mod is jjj_markers.jjj_mod
