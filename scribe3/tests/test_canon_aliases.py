from scribe3.canon_aliases import (
    normalize_char_importance,
    normalize_rule_category,
)


def test_importance_aliases():
    assert normalize_char_importance("protagonist") == "protagonist"
    assert normalize_char_importance("supporting") == "major"
    assert normalize_char_importance("mentioned") == "background"
    assert normalize_char_importance("配角") == "major"


def test_rule_category_aliases():
    assert normalize_rule_category(None) == "social"
    assert normalize_rule_category("民俗") == "social"
    assert normalize_rule_category("禁忌") == "social"
    assert normalize_rule_category("magic") == "magic"
