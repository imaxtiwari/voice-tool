import os
import json
import mailbox
from email.message import EmailMessage
import pytest
from pipeline.clean_sent import main

def create_mbox_file(path, messages_data):
    mbox = mailbox.mbox(path)
    for data in messages_data:
        msg = EmailMessage()
        msg['Subject'] = data.get('subject', '')
        msg['Date'] = data.get('date', 'Tue, 7 Jul 2026 12:00:00 +0000')
        
        # Check if multipart parts are provided
        parts = data.get('parts', [])
        if parts:
            # EmailMessage requires make_multipart or add_alternative, but add_part handles it
            for content, content_type in parts:
                maintype, subtype = content_type.split('/')
                msg.add_part(content, maintype=maintype, subtype=subtype)
        else:
            body = data.get('body', '')
            is_html = data.get('is_html', False)
            if is_html:
                # Add HTML alternative or set html content
                msg.set_content(body, subtype='html')
            else:
                msg.set_content(body)
        mbox.add(msg)
    mbox.flush()
    mbox.close()

@pytest.fixture(autouse=True)
def cleanup_output():
    output_path = "pipeline/data/sent_clean.jsonl"
    if os.path.exists(output_path):
        os.remove(output_path)
    yield
    if os.path.exists(output_path):
        os.remove(output_path)

def test_word_count_less_than_15_dropped(tmp_path):
    mbox_path = tmp_path / "test.mbox"
    body = "One two three four five six seven eight nine ten eleven twelve thirteen fourteen."
    messages = [{"subject": "Test Short", "body": body}]
    create_mbox_file(mbox_path, messages)
    
    main(["--input", str(mbox_path)])
    
    output_path = "pipeline/data/sent_clean.jsonl"
    assert os.path.exists(output_path)
    with open(output_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 0

def test_noreply_subject_dropped(tmp_path):
    mbox_path = tmp_path / "test.mbox"
    body = "This is a long body that has more than fifteen words so it should not be dropped by the word count check."
    messages = [
        {"subject": "Hello noreply there", "body": body},
        {"subject": "Notification: something happened", "body": body},
        {"subject": "Auto-Reply: away", "body": body},
    ]
    create_mbox_file(mbox_path, messages)
    
    main(["--input", str(mbox_path)])
    
    output_path = "pipeline/data/sent_clean.jsonl"
    with open(output_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 0

def test_quoted_lines_stripped(tmp_path):
    mbox_path = tmp_path / "test.mbox"
    body = (
        "This is a long body that has more than fifteen words so it should not be dropped.\n"
        "> This is a quoted line\n"
        "> And another quoted line\n"
        "This is a normal line after quotes."
    )
    messages = [{"subject": "Test Quotes", "body": body}]
    create_mbox_file(mbox_path, messages)
    
    main(["--input", str(mbox_path)])
    
    output_path = "pipeline/data/sent_clean.jsonl"
    with open(output_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    result = json.loads(lines[0])
    cleaned_body = result["body"]
    assert "quoted line" not in cleaned_body
    assert "This is a normal line after quotes." in cleaned_body

def test_reply_header_stripped(tmp_path):
    mbox_path = tmp_path / "test.mbox"
    body = (
        "This is a long body that has more than fifteen words so it should not be dropped.\n"
        "\n"
        "On Tue, Jul 7, 2026 at 5:00 PM, User <user@example.com> wrote:\n"
        "Some thread message content."
    )
    messages = [{"subject": "Test Reply Header", "body": body}]
    create_mbox_file(mbox_path, messages)
    
    main(["--input", str(mbox_path)])
    
    output_path = "pipeline/data/sent_clean.jsonl"
    with open(output_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    result = json.loads(lines[0])
    cleaned_body = result["body"]
    assert "On Tue, Jul 7" not in cleaned_body
    assert "Some thread message content." in cleaned_body

def test_signature_block_stripped(tmp_path):
    mbox_path = tmp_path / "test.mbox"
    body = (
        "This is a long body that has more than fifteen words so it should not be dropped.\n"
        "\n"
        "--\n"
        "John Doe\n"
        "Software Engineer\n"
        "+1-555-123-4567\n"
        "http://johndoe.com"
    )
    messages = [{"subject": "Test Signature", "body": body}]
    create_mbox_file(mbox_path, messages)
    
    main(["--input", str(mbox_path)])
    
    output_path = "pipeline/data/sent_clean.jsonl"
    with open(output_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    result = json.loads(lines[0])
    cleaned_body = result["body"]
    assert "John Doe" not in cleaned_body
    assert "Software Engineer" not in cleaned_body
    assert "+1-555-123-4567" not in cleaned_body
    assert "http://johndoe.com" not in cleaned_body
    assert "This is a long body" in cleaned_body

def test_html_body_cleaned(tmp_path):
    mbox_path = tmp_path / "test.mbox"
    html_content = (
        "<p>This is a <b>long HTML body</b> that has more than fifteen words "
        "so it should not be dropped. &lt;Hello&gt;</p>"
    )
    messages = [{"subject": "Test HTML", "body": html_content, "is_html": True}]
    create_mbox_file(mbox_path, messages)
    
    main(["--input", str(mbox_path)])
    
    output_path = "pipeline/data/sent_clean.jsonl"
    with open(output_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    result = json.loads(lines[0])
    cleaned_body = result["body"]
    assert "<b>" not in cleaned_body
    assert "<p>" not in cleaned_body
    assert "<Hello>" in cleaned_body
    assert "This is a long HTML body that has more than fifteen words" in cleaned_body

def test_valid_email_passes(tmp_path):
    mbox_path = tmp_path / "test.mbox"
    body = "This is a perfectly valid sent email with more than fifteen words. It should pass through the pipeline and be written to the output file."
    messages = [{"subject": "Valid Email Subject", "body": body, "date": "Tue, 07 Jul 2026 12:34:56 +0000"}]
    create_mbox_file(mbox_path, messages)
    
    main(["--input", str(mbox_path)])
    
    output_path = "pipeline/data/sent_clean.jsonl"
    with open(output_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    result = json.loads(lines[0])
    assert result["subject"] == "Valid Email Subject"
    assert result["body"].strip() == body
    assert result["date"] == "Tue, 07 Jul 2026 12:34:56 +0000"
    assert result["char_count"] == len(body)

def test_empty_mbox_file(tmp_path):
    mbox_path = tmp_path / "empty.mbox"
    # Create empty file
    mbox_path.touch()
    
    main(["--input", str(mbox_path)])
    
    output_path = "pipeline/data/sent_clean.jsonl"
    assert os.path.exists(output_path)
    with open(output_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 0
