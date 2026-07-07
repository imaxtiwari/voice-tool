"""Clean sent emails module.

This script takes a Gmail Takeout .mbox file and produces a clean
JSONL corpus of sent emails.
"""

import argparse
import os
import sys
import mailbox
import json
import re
import html
import bleach

# Drop subjects (case-insensitive substring match)
DROP_SUBJECTS = [
    "calendar", "invite", "unsubscribe", "automated",
    "notification", "noreply", "no-reply", "out of office",
    "do not reply", "auto-reply"
]

def decode_bytes(payload):
    """Decode bytes payload trying UTF-8 first, falling back to latin-1."""
    try:
        return payload.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        try:
            return payload.decode('latin-1')
        except Exception:
            return payload.decode('latin-1', errors='replace')

def get_email_body(message):
    """
    Decodes email body. Prefer text/plain, fallback to text/html.
    Returns (body, content_type). If multipart, walks parts.
    """
    if not message.is_multipart():
        content_type = message.get_content_type()
        if content_type in ('text/plain', 'text/html'):
            payload = message.get_payload(decode=True)
            if payload is not None:
                return decode_bytes(payload), content_type
        return None, None

    # Walk and find first text/plain
    for part in message.walk():
        if part.get_content_type() == 'text/plain':
            payload = part.get_payload(decode=True)
            if payload is not None:
                return decode_bytes(payload), 'text/plain'

    # Fallback to first text/html
    for part in message.walk():
        if part.get_content_type() == 'text/html':
            payload = part.get_payload(decode=True)
            if payload is not None:
                return decode_bytes(payload), 'text/html'

    return None, None

def is_on_date_header(sline):
    """Check if the stripped line matches the 'On [date]' header pattern."""
    if not sline.startswith("On "):
        return False
    if "wrote" in sline.lower() or "sent" in sline.lower():
        return True
    # Matches: On Mon, Jan 1 or On 01/01/2020 or On 2020-01-01
    if re.match(r'^On\s+(?:[A-Za-z]{3,10},?\s+\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})', sline):
        return True
    return False

def is_reply_header(line, prev_blank):
    """Determine if a line is a reply header appearing after a blank line."""
    if not prev_blank:
        return False
    sline = line.strip()
    if sline.startswith("From:"):
        return True
    return is_on_date_header(sline)

def is_name_title_pattern(line):
    """Check if the line matches a name/title pattern (2-4 title-case words)."""
    words = line.strip().split()
    if not (2 <= len(words) <= 4):
        return False

    has_capitalized = False
    for w in words:
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if not w_clean:
            continue
        # Allow minor lowercase words common in titles
        if w_clean.lower() in {'of', 'and', 'for', 'the', 'a', 'in', 'to', 'at', 'on', 'with', 'by'}:
            continue
        if w_clean[0].isupper():
            if len(w_clean) > 1 and not (w_clean[1:].islower() or w_clean.isupper()):
                return False
            has_capitalized = True
        else:
            return False

    return has_capitalized

def matches_sig_line(line):
    """Check if a line matches any of the signature block criteria."""
    stripped = line.strip()
    if not stripped:
        return True  # Is blank
    if stripped.startswith('--'):
        return True
    if stripped.startswith('http'):
        return True
    if re.match(r'^[\+\d\(\)\-\s]{7,20}$', stripped):
        if any(c.isdigit() for c in stripped):
            return True
    if is_name_title_pattern(line):
        return True
    return False

def strip_signature(body):
    """
    Finds the last contiguous block of lines matching signature criteria (max 8 lines)
    and removes it.
    """
    lines = body.splitlines()
    if not lines:
        return body

    matches = [matches_sig_line(line) for line in lines]

    # Find the last contiguous block of True matches
    best_start = -1
    best_end = -1
    current_start = -1

    for i, m in enumerate(matches):
        if m:
            if current_start == -1:
                current_start = i
        else:
            if current_start != -1:
                best_start = current_start
                best_end = i
                current_start = -1
    if current_start != -1:
        best_start = current_start
        best_end = len(lines)

    if best_start != -1:
        block_length = best_end - best_start
        if block_length > 8:
            best_start = best_end - 8
        new_lines = lines[:best_start] + lines[best_end:]
        return "\n".join(new_lines)

    return body

class EmailCleaner:
    """Class to manage stats and process individual email messages."""
    def __init__(self):
        self.total_count = 0
        self.kept_count = 0
        self.dropped_count = 0
        self.drop_logs_count = 0

    def log_drop(self, reason, subject):
        """Log drop reason to stderr for the first 10 drops only."""
        if self.drop_logs_count < 10:
            sys.stderr.write(f"Drop reason: {reason} | Subject: {subject}\n")
            self.drop_logs_count += 1

    def process_message(self, message):
        """Processes a single email message. Returns dict if kept, None if dropped."""
        self.total_count += 1
        subject = message.get('subject') or ""

        # Step 2 — Decode body
        body, content_type = get_email_body(message)
        if body is None:
            self.dropped_count += 1
            self.log_drop("No valid text/plain or text/html body found", subject)
            return None

        # Step 3 — Drop if word count < 15
        words = body.strip().split()
        if len(words) < 15:
            self.dropped_count += 1
            self.log_drop(f"Word count < 15 ({len(words)} words)", subject)
            return None

        # Step 4 — Drop if subject matches blacklisted terms
        subject_lower = subject.lower()
        for trigger in DROP_SUBJECTS:
            if trigger in subject_lower:
                self.dropped_count += 1
                self.log_drop(f"Subject blacklisted matching term: '{trigger}'", subject)
                return None

        # Step 5 — Strip quoted thread lines
        lines = body.splitlines()
        cleaned_lines = []
        prev_blank = False
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith('>'):
                prev_blank = False
                continue
            if is_reply_header(line, prev_blank):
                prev_blank = False
                continue
            cleaned_lines.append(line)
            prev_blank = (line.strip() == "")

        body = "\n".join(cleaned_lines)

        # Step 6 — Strip signature block
        body = strip_signature(body)

        # Step 7 — Strip HTML if body is HTML
        if content_type == 'text/html':
            body = bleach.clean(body, tags=[], strip=True)
            body = html.unescape(body)

        # Step 8 — Final length check
        char_count = len(body)
        if char_count < 30:
            self.dropped_count += 1
            self.log_drop(f"Character count < 30 ({char_count} chars after cleaning)", subject)
            return None

        # Step 9 — Keep email
        self.kept_count += 1
        email_date = message.get('date') or ""

        return {
            "subject": subject,
            "body": body,
            "date": str(email_date),
            "char_count": char_count
        }

def main(argv=None):
    """Main execution entry point."""
    parser = argparse.ArgumentParser(description="Clean Gmail Takeout sent messages.")
    parser.add_argument("--input", required=True, help="Path to input .mbox file")
    args = parser.parse_args(argv)

    input_path = args.input
    output_path = "pipeline/data/sent_clean.jsonl"

    if not os.path.exists(input_path):
        sys.stderr.write(f"Error: Input file '{input_path}' does not exist.\n")
        sys.exit(1)

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    cleaner = EmailCleaner()

    # Open output file in write mode to ensure idempotency (overwrites existing file)
    with open(output_path, 'w', encoding='utf-8') as out_f:
        try:
            mbox = mailbox.mbox(input_path)
            for message in mbox:
                result = cleaner.process_message(message)
                if result is not None:
                    out_f.write(json.dumps(result, ensure_ascii=False) + "\n")

                if cleaner.total_count % 100 == 0:
                    print(f"Processed {cleaner.total_count} emails... ({cleaner.kept_count} kept, {cleaner.dropped_count} dropped)")
        except Exception as e:
            sys.stderr.write(f"Error processing mbox: {e}\n")
            sys.exit(1)

    print(f"Done. Kept {cleaner.kept_count} / Total {cleaner.total_count} emails. Output: {output_path}")

if __name__ == "__main__":
    main()
