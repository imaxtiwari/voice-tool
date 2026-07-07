"""Rule mapping and prompt construction based on styling parameters."""

def get_rules(de_ai_level: int) -> list[str]:
    """
    Returns a cumulative list of stylistic rewrite rules based on the de_ai_level.
    Raises ValueError if de_ai_level is out of bounds (0-100).
    """
    if de_ai_level < 0 or de_ai_level > 100:
        raise ValueError("de_ai_level must be between 0 and 100")

    rules = []

    # Level 0-20 rules (always included for any valid de_ai_level)
    rules.extend([
        "Replace 'utilize' with 'use'",
        "Replace 'leverage' (when used as a verb) with 'use'",
        "Remove these words entirely: synergies, ecosystem, paradigm, circle back, touch base, bandwidth, deep dive"
    ])

    # Level 21-50 rules
    if de_ai_level >= 21:
        rules.extend([
            "Remove hedging stacks: 'hoping to potentially', 'might possibly', 'would potentially'",
            "Remove filler openers: 'I wanted to reach out', 'I hope this email finds you', 'I am writing to'",
            "Remove performative closings: 'please don't hesitate to reach out', 'at your earliest convenience', 'I look forward to hearing from you'"
        ])

    # Level 51-80 rules
    if de_ai_level >= 51:
        rules.extend([
            "Remove em-dashes (—) used as stylistic flourish. Keep em-dashes only when used as list punctuation.",
            "Remove 'not just X but Y' and 'not only X but also Y' constructions. Pick one.",
            "Replace 'at your earliest convenience' → 'soon'. Replace 'would you be available' → 'are you free'."
        ])

    # Level 81-100 rules
    if de_ai_level >= 81:
        rules.extend([
            "Compress to direct declaratives. Remove all meta-commentary about the email itself.",
            "Tighten to minimum viable words. If a sentence can be cut to half its words without losing meaning, cut it.",
            "Apply active voice throughout. No passive constructions.",
            "Remove all sentence-level hedging: 'I think', 'I believe', 'it seems', 'perhaps', 'it might be'."
        ])

    return rules
