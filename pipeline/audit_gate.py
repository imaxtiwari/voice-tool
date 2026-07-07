"""Audit gate module.

This script counts usable examples in the clean sent emails JSONL corpus
and enforces a quality/size gate before embedding.
"""

import os
import sys
import json

INPUT_PATH = "pipeline/data/sent_clean.jsonl"

AUTO_KEYWORDS = [
    "this is an automated message",
    "do not reply to this email",
    "you are receiving this because",
    "unsubscribe"
]

def is_usable(email_dict):
    """
    Checks if an email is usable based on:
    - char_count > 50
    - body does not contain automated message phrases (case-insensitive)
    """
    body = email_dict.get("body", "")
    # Note: char_count can also be checked directly via len(body), 
    # but we check the stored 'char_count' field as specified.
    char_count = email_dict.get("char_count", 0)
    
    if char_count <= 50:
        return False
        
    body_lower = body.lower()
    for kw in AUTO_KEYWORDS:
        if kw in body_lower:
            return False
            
    return True

def run_audit(file_path):
    """
    Reads the file, counts usable messages, and returns usability count.
    If file doesn't exist, raises FileNotFoundError.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} not found.")
        
    usable_count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                email_data = json.loads(line)
                if is_usable(email_data):
                    usable_count += 1
            except json.JSONDecodeError:
                continue
    return usable_count

def main(argv=None):
    # Overridable input path for testing/flexibility
    file_path = INPUT_PATH
    if argv and len(argv) > 0:
        file_path = argv[0]

    try:
        usable_count = run_audit(file_path)
    except FileNotFoundError:
        print("Run clean_sent.py first.")
        sys.exit(2)

    print(f"Corpus audit: {usable_count} usable emails found.")
    if usable_count >= 100:
        print("Gate: PASS — ready to embed.")
        sys.exit(0)
    else:
        print(f"Gate: FAIL — need at least 100 usable emails, found {usable_count}.")
        print("Action: Export more sent mail from Google Takeout and re-run clean_sent.py")
        sys.exit(1)

if __name__ == "__main__":
    # We pass sys.argv[1:] only if arguments are provided, otherwise None
    main(sys.argv[1:] if len(sys.argv) > 1 else None)
