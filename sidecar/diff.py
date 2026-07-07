"""Diff computation and markup generation."""

import difflib

def generate_diff(original: str, rewritten: str) -> list[dict]:
    """
    Computes a word-level diff between original and rewritten strings.
    Returns a list of dicts with keys: original, rewritten, type, fact_flag.
    """
    # Edge case: both strings empty or contain only whitespace
    if not original.strip() and not rewritten.strip():
        return []

    original_tokens = original.split()
    rewritten_tokens = rewritten.split()

    # Edge case: one string is completely empty
    if not original_tokens and rewritten_tokens:
        return [{
            "original": "",
            "rewritten": " ".join(rewritten_tokens),
            "type": "insertion",
            "fact_flag": False
        }]
    if original_tokens and not rewritten_tokens:
        return [{
            "original": " ".join(original_tokens),
            "rewritten": "",
            "type": "deletion",
            "fact_flag": False
        }]

    matcher = difflib.SequenceMatcher(None, original_tokens, rewritten_tokens)
    opcodes = matcher.get_opcodes()

    results = []
    for tag, i1, i2, j1, j2 in opcodes:
        orig_slice = " ".join(original_tokens[i1:i2])
        rewr_slice = " ".join(rewritten_tokens[j1:j2])

        if tag == 'equal':
            diff_type = 'equal'
        elif tag == 'replace':
            diff_type = 'substitution'
        elif tag == 'delete':
            diff_type = 'deletion'
            rewr_slice = ""
        elif tag == 'insert':
            diff_type = 'insertion'
            orig_slice = ""
        else:
            continue

        results.append({
            "original": orig_slice,
            "rewritten": rewr_slice,
            "type": diff_type,
            "fact_flag": False
        })

    return results
