import pytest

from verification_core.predicates import parse_binding_predicate


def test_unsupported_binding_condition_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported binding condition syntax: Call",
    ):
        parse_binding_predicate("open('secret')", ())
