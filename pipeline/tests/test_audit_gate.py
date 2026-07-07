import os
import json
import pytest
from pipeline.audit_gate import main

def create_jsonl_file(path, emails):
    with open(path, "w", encoding="utf-8") as f:
        for email in emails:
            f.write(json.dumps(email) + "\n")

def test_missing_file(tmp_path, capsys):
    missing_path = tmp_path / "does_not_exist.jsonl"
    
    with pytest.raises(SystemExit) as excinfo:
        main([str(missing_path)])
    
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "Run clean_sent.py first." in captured.out

def test_less_than_100_usable_emails(tmp_path, capsys):
    emails = []
    # 99 usable emails
    for i in range(99):
        emails.append({
            "subject": f"Subject {i}",
            "body": f"This is a long valid body {i} that passes all restrictions and has more than fifty characters.",
            "date": "Tue, 7 Jul 2026 12:00:00 +0000",
            "char_count": 100
        })
    # Add 1 email with <= 50 char_count (not usable)
    emails.append({
        "subject": "Short body",
        "body": "Short",
        "date": "Tue, 7 Jul 2026 12:00:00 +0000",
        "char_count": 5
    })
    
    jsonl_path = tmp_path / "sent_clean.jsonl"
    create_jsonl_file(jsonl_path, emails)
    
    with pytest.raises(SystemExit) as excinfo:
        main([str(jsonl_path)])
        
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Corpus audit: 99 usable emails found." in captured.out
    assert "Gate: FAIL — need at least 100 usable emails, found 99." in captured.out
    assert "Action: Export more sent mail from Google Takeout and re-run clean_sent.py" in captured.out

def test_100_plus_usable_emails(tmp_path, capsys):
    emails = []
    # 105 usable emails
    for i in range(105):
        emails.append({
            "subject": f"Subject {i}",
            "body": f"This is a long valid body {i} that passes all restrictions and has more than fifty characters.",
            "date": "Tue, 7 Jul 2026 12:00:00 +0000",
            "char_count": 100
        })
        
    jsonl_path = tmp_path / "sent_clean.jsonl"
    create_jsonl_file(jsonl_path, emails)
    
    with pytest.raises(SystemExit) as excinfo:
        main([str(jsonl_path)])
        
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "Corpus audit: 105 usable emails found." in captured.out
    assert "Gate: PASS — ready to embed." in captured.out

def test_automated_messages_excluded(tmp_path, capsys):
    emails = []
    # 5 usable emails
    for i in range(5):
        emails.append({
            "subject": f"Subject {i}",
            "body": "This is a long valid body that passes all restrictions and has more than fifty characters.",
            "char_count": 90
        })
    # Add automated messages (should be excluded)
    automated_bodies = [
        "This is an automated message from the system.",
        "Please do not reply to this email, replies are not monitored.",
        "You are receiving this because you signed up for notifications.",
        "Click here to unsubscribe from this list."
    ]
    for i, body in enumerate(automated_bodies):
        emails.append({
            "subject": f"Automated {i}",
            "body": body,
            "char_count": len(body)
        })
        
    jsonl_path = tmp_path / "sent_clean.jsonl"
    create_jsonl_file(jsonl_path, emails)
    
    with pytest.raises(SystemExit) as excinfo:
        main([str(jsonl_path)])
        
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Corpus audit: 5 usable emails found." in captured.out

def test_short_emails_excluded(tmp_path, capsys):
    emails = []
    # 10 usable emails
    for i in range(10):
        emails.append({
            "subject": f"Subject {i}",
            "body": "This is a long valid body that has more than 50 chars in it to pass gate.",
            "char_count": 75
        })
    # 5 emails with char_count <= 50 (should be excluded)
    for i in range(5):
        emails.append({
            "subject": f"Short {i}",
            "body": "Very short email body that is small.",
            "char_count": len("Very short email body that is small.")
        })
        
    jsonl_path = tmp_path / "sent_clean.jsonl"
    create_jsonl_file(jsonl_path, emails)
    
    with pytest.raises(SystemExit) as excinfo:
        main([str(jsonl_path)])
        
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Corpus audit: 10 usable emails found." in captured.out
