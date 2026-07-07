import os
import json
import pytest
from unittest.mock import MagicMock, patch
from pipeline.prep_finetune import main, ai_ify_body, validate_example

def test_ai_ify_rules_applied():
    """Verifies that at least one of the AI-ification rules is applied and modifies the text."""
    body = "Please help me to show how we use this resource. Can you do it tomorrow?"
    ai_ified = ai_ify_body(body)
    assert ai_ified != body
    
    # Verify that rule modifications exist
    assert any([
        "facilitate" in ai_ified,
        "demonstrate" in ai_ified,
        "utilize" in ai_ified,
        "I wanted to reach out" in ai_ified,
        "at your earliest convenience?" in ai_ified,
        "—" in ai_ified,
        "I believe that" in ai_ified
    ])

def test_ai_ify_reproducibility():
    """Verifies that random.seed(42) produces exact same output for the same input."""
    body = "Please help me to show how we use this resource. Can you do it tomorrow?"
    import random
    
    random.seed(42)
    res1 = ai_ify_body(body)
    
    random.seed(42)
    res2 = ai_ify_body(body)
    
    assert res1 == res2

def test_validate_example_identical():
    """Verifies validation rejects example where assistant content equals user content."""
    ex = {
        "messages": [
            {"role": "system", "content": "system instruction"},
            {"role": "user", "content": "same content"},
            {"role": "assistant", "content": "same content"}
        ]
    }
    assert validate_example(ex) is False

def test_validate_example_empty_field():
    """Verifies validation rejects examples with empty fields or incorrect roles."""
    ex1 = {
        "messages": [
            {"role": "system", "content": "system instruction"},
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "some content"}
        ]
    }
    ex2 = {
        "messages": [
            {"role": "system", "content": "system instruction"},
            {"role": "user", "content": "some content"}
        ]
    }
    assert validate_example(ex1) is False
    assert validate_example(ex2) is False

@patch("pipeline.prep_finetune.AzureOpenAI")
def test_prep_finetune_fewer_than_50_exit_1(mock_azure, tmp_path):
    """Verifies that the script exits with code 1 if fewer than 50 valid examples are processed."""
    input_path = tmp_path / "sent_clean.jsonl"
    output_path = tmp_path / "finetune_upload.jsonl"
    
    emails = []
    for i in range(10):
        emails.append({
            "subject": f"Subj {i}",
            "body": f"This is a valid email body that has more than fifteen words so it will pass the clean checks {i}.",
            "date": "Tue, 07 Jul 2026",
            "char_count": 100
        })
    with open(input_path, "w", encoding="utf-8") as f:
        for ex in emails:
            f.write(json.dumps(ex) + "\n")
            
    with pytest.raises(SystemExit) as excinfo:
        main([str(input_path), str(output_path)])
    assert excinfo.value.code == 1

@patch("pipeline.prep_finetune.AzureOpenAI")
def test_prep_finetune_success(mock_azure, tmp_path):
    """Verifies dataset generation, formatting, log creation, and file upload behavior."""
    input_path = tmp_path / "sent_clean.jsonl"
    output_path = tmp_path / "finetune_upload.jsonl"
    
    emails = []
    for i in range(60):
        emails.append({
            "subject": f"Subj {i}",
            "body": f"I wanted to write you. Please help me to show how we use this resource. We should make a decision soon. Can you do it tomorrow? {i}",
            "date": "Tue, 07 Jul 2026",
            "char_count": 100
        })
    with open(input_path, "w", encoding="utf-8") as f:
        for ex in emails:
            f.write(json.dumps(ex) + "\n")
            
    mock_client = MagicMock()
    mock_file_response = MagicMock()
    mock_file_response.id = "file-12345"
    mock_client.files.create.return_value = mock_file_response
    mock_azure.return_value = mock_client
    
    log_path = tmp_path / "ft_version_log.json"
    
    with patch("pipeline.prep_finetune.LOG_PATH", str(log_path)):
        with patch.dict(os.environ, {
            "AZURE_OPENAI_ENDPOINT": "https://fake.azure.com",
            "AZURE_OPENAI_KEY": "fakekey"
        }):
            main([str(input_path), str(output_path)])
            
    assert output_path.exists()
    with open(output_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 60
    
    first_item = json.loads(lines[0])
    assert len(first_item["messages"]) == 3
    assert first_item["messages"][0]["role"] == "system"
    assert first_item["messages"][1]["role"] == "user"
    assert first_item["messages"][2]["role"] == "assistant"
    assert first_item["messages"][1]["content"] != first_item["messages"][2]["content"]
    
    assert log_path.exists()
    with open(log_path, "r", encoding="utf-8") as f:
        log_data = json.load(f)
    assert log_data["file_id"] == "file-12345"
    assert log_data["example_count"] == 60
    assert "uploaded_at" in log_data
    assert log_data["job_id"] is None
