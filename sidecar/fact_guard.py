"""Word-level fact guard to prevent modification of factual details."""

import re

# Regex patterns for fact detection (case-insensitive where appropriate)
DATE_PATTERNS = [
    r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b',
    r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
    r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b'
]

COMMITMENT_PATTERNS = [
    r'\b(by|before|until)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec|\d{1,2})\b',
    r'\b(i\'ll|i will|we\'ll|we will|i\'m going to)\s+\w+'
]

NUMBER_WITH_UNIT_PATTERNS = [
    r'\b\d+\s*(k|m|b|%|hr|hrs|hour|hours|day|days|week|weeks|month|months)\b',
    r'\+\d+[\.\d]*%'
]

def is_named_person(text: str) -> bool:
    """
    Checks for 2-3 word title-case sequences.
    To avoid matching capitalized words starting a sentence, the sequence is
    only flagged if it is not at the start of a sentence (unless it spans the entire string).
    """
    pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b'
    for m in re.finditer(pattern, text):
        start, end = m.span()
        # If it spans the entire string (standalone fragment/name)
        if start == 0 and end == len(text.strip()):
            return True
        # If it is not preceded by a sentence terminator
        prefix = text[:start].strip()
        if prefix and not re.search(r'[.!?]$', prefix):
            return True
    return False

def contains_fact(text: str) -> bool:
    """Checks if the original string matches any defined fact patterns."""
    # Check DATE
    for p in DATE_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return True

    # Check COMMITMENT
    for p in COMMITMENT_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return True

    # Check NUMBER_WITH_UNIT
    for p in NUMBER_WITH_UNIT_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return True

    # Check QUOTE
    if re.search(r'".*?"', text) or re.search(r"'.*?'", text):
        return True

    # Check NAMED_PERSON
    if is_named_person(text):
        return True

    return False

def flag_facts(diff_objects: list[dict]) -> list[dict]:
    """
    Flags deletions and substitutions containing facts in their original field.
    Leaves equal and insertion type blocks untouched.
    """
    for obj in diff_objects:
        if obj.get("type") in ("equal", "insertion"):
            continue
            
        original_text = obj.get("original", "")
        if contains_fact(original_text):
            obj["fact_flag"] = True
            
    return diff_objects
