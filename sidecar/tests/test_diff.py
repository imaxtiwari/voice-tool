import pytest
from sidecar.diff import generate_diff

def test_identical_strings():
    """Verifies identical strings produce a single 'equal' type diff object."""
    res = generate_diff("Hello world", "Hello world")
    assert len(res) == 1
    assert res[0]["original"] == "Hello world"
    assert res[0]["rewritten"] == "Hello world"
    assert res[0]["type"] == "equal"

def test_single_word_substitution():
    """Verifies single word substitutions are identified correctly."""
    res = generate_diff("Hello world", "Hello there")
    assert len(res) == 2
    assert res[0] == {"original": "Hello", "rewritten": "Hello", "type": "equal", "fact_flag": False}
    assert res[1] == {"original": "world", "rewritten": "there", "type": "substitution", "fact_flag": False}

def test_multi_word_substitution_grouped():
    """Verifies that consecutive changed tokens are grouped into a single substitution block."""
    res = generate_diff("I wanted to reach out", "I am writing")
    assert len(res) == 2
    assert res[0] == {"original": "I", "rewritten": "I", "type": "equal", "fact_flag": False}
    assert res[1] == {"original": "wanted to reach out", "rewritten": "am writing", "type": "substitution", "fact_flag": False}

def test_deletion():
    """Verifies that word deletion is detected and maps to type deletion."""
    res = generate_diff("Hello there friend", "Hello friend")
    assert len(res) == 3
    assert res[0] == {"original": "Hello", "rewritten": "Hello", "type": "equal", "fact_flag": False}
    assert res[1] == {"original": "there", "rewritten": "", "type": "deletion", "fact_flag": False}
    assert res[2] == {"original": "friend", "rewritten": "friend", "type": "equal", "fact_flag": False}

def test_insertion():
    """Verifies that word insertion is detected and maps to type insertion."""
    res = generate_diff("Hello friend", "Hello there friend")
    assert len(res) == 3
    assert res[0] == {"original": "Hello", "rewritten": "Hello", "type": "equal", "fact_flag": False}
    assert res[1] == {"original": "", "rewritten": "there", "type": "insertion", "fact_flag": False}
    assert res[2] == {"original": "friend", "rewritten": "friend", "type": "equal", "fact_flag": False}

def test_both_empty():
    """Verifies that empty/whitespace strings return an empty list."""
    assert generate_diff("", "") == []
    assert generate_diff("   ", "") == []
    assert generate_diff("", "   ") == []

def test_fact_flag_always_false():
    """Verifies that fact_flag is defaulted to False for all computed blocks."""
    res = generate_diff("The quick brown fox jumps over the lazy dog", "The fast brown fox leaped over a lazy dog")
    assert len(res) > 0
    for obj in res:
        assert obj["fact_flag"] is False

def test_type_field_values():
    """Verifies all diff block types are valid strings."""
    res = generate_diff("The quick brown fox", "The fast brown fox leaped")
    assert len(res) > 0
    valid_types = {"equal", "substitution", "deletion", "insertion"}
    for obj in res:
        assert obj["type"] in valid_types
