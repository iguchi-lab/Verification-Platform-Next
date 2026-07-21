from enum import Enum

import jjjexperiment.constants as constants
from jjjexperiment.inputs import options


OPTION_ENUM_NAMES = tuple(options.__all__)


def test_constants_preserves_option_enum_exports() -> None:
    for name in OPTION_ENUM_NAMES:
        exported = getattr(constants, name)
        assert exported is getattr(options, name)
        assert issubclass(exported, Enum)


def test_default_vav_supply_volume_formula_is_unchanged() -> None:
    expected = options.VAVありなしの吹出風量.数式を統一しない.value

    assert constants.change_supply_volume_before_vav_adjust == expected
