import pytest
from sidecar.prompt_builder import get_rules

def test_get_rules_boundaries():
    """Verifies that rule list accumulates correctly at boundaries (0, 20, 21, 50, 51, 80, 81, 100)."""
    # Boundary 0 & 20: 0-20 rules (3 items)
    rules_0 = get_rules(0)
    assert len(rules_0) == 3
    rules_20 = get_rules(20)
    assert len(rules_20) == 3
    assert rules_0 == rules_20

    # Boundary 21 & 50: 0-20 + 21-50 rules (6 items)
    rules_21 = get_rules(21)
    assert len(rules_21) == 6
    rules_50 = get_rules(50)
    assert len(rules_50) == 6
    assert rules_21 == rules_50

    # Boundary 51 & 80: 0-20 + 21-50 + 51-80 rules (9 items)
    rules_51 = get_rules(51)
    assert len(rules_51) == 9
    rules_80 = get_rules(80)
    assert len(rules_80) == 9
    assert rules_51 == rules_80

    # Boundary 81 & 100: all rules (13 items)
    rules_81 = get_rules(81)
    assert len(rules_81) == 13
    rules_100 = get_rules(100)
    assert len(rules_100) == 13
    assert rules_81 == rules_100

def test_get_rules_out_of_bounds():
    """Verifies that levels < 0 or > 100 raise ValueError."""
    with pytest.raises(ValueError):
        get_rules(-1)
    with pytest.raises(ValueError):
        get_rules(101)
