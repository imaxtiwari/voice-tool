import pytest
from sidecar.fact_guard import flag_facts

def test_fact_guard_flagging_patterns():
    """Verifies that dates, commitments, numbers with units, quotes, and names trigger fact_flag correctly."""
    diffs = [
        # NUMBER_WITH_UNIT (+11.65%)
        {"original": "We saw a return of +11.65% in Q3", "rewritten": "returns", "type": "substitution", "fact_flag": False},
        # COMMITMENT (by Thursday)
        {"original": "I will finish this by Thursday", "rewritten": "this week", "type": "substitution", "fact_flag": False},
        # COMMITMENT (I'll send)
        {"original": "I'll send the document", "rewritten": "sending doc", "type": "substitution", "fact_flag": False},
        # NAMED_PERSON (Nandini Singh)
        {"original": "Please call Nandini Singh", "rewritten": "contact her", "type": "substitution", "fact_flag": False},
        # Plain number alone (no unit)
        {"original": "we had 3 options", "rewritten": "several options", "type": "substitution", "fact_flag": False},
        # type equal (should remain False)
        {"original": "I will finish this by Thursday", "rewritten": "I will finish this by Thursday", "type": "equal", "fact_flag": False},
        # type insertion (should remain False)
        {"original": "", "rewritten": "I will finish this by Thursday", "type": "insertion", "fact_flag": False}
    ]

    flagged = flag_facts(diffs)

    assert flagged[0]["fact_flag"] is True
    assert flagged[1]["fact_flag"] is True
    assert flagged[2]["fact_flag"] is True
    assert flagged[3]["fact_flag"] is True
    assert flagged[4]["fact_flag"] is False  # plain number "3" doesn't trigger
    assert flagged[5]["fact_flag"] is False  # type "equal" not modified
    assert flagged[6]["fact_flag"] is False  # type "insertion" not checked
