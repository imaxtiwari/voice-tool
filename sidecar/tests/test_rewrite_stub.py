import os
# Set mock environment variables before import to pass validation
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint.azure.com"
os.environ["AZURE_OPENAI_KEY"] = "mock-key-value"

import pytest
from fastapi.testclient import TestClient
from sidecar.main import app

client = TestClient(app)

def test_rewrite_valid_request():
    """Verifies that a valid POST /rewrite request returns HTTP 200 and echoes text."""
    payload = {
        "text": "Hello world email",
        "de_ai_level": 50,
        "voice_level": 75,
        "mode": "my_voice"
    }
    response = client.post("/rewrite", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["rewritten_text"] == "Hello world email"
    assert data["model_used"] == "stub"
    assert data["diff"] == []
    assert data["retrieval_confidence"] == 0.0

def test_rewrite_empty_text():
    """Verifies that empty text parameter returns HTTP 422 validation error."""
    payload = {
        "text": "   ",
        "de_ai_level": 50,
        "voice_level": 50,
        "mode": "my_voice"
    }
    response = client.post("/rewrite", json=payload)
    assert response.status_code == 422

def test_rewrite_de_ai_level_out_of_bounds():
    """Verifies that de_ai_level > 100 returns HTTP 422 validation error."""
    payload = {
        "text": "Hello",
        "de_ai_level": 101,
        "voice_level": 50,
        "mode": "my_voice"
    }
    response = client.post("/rewrite", json=payload)
    assert response.status_code == 422

def test_rewrite_invalid_mode():
    """Verifies that invalid mode parameter returns HTTP 422 validation error."""
    payload = {
        "text": "Hello",
        "de_ai_level": 50,
        "voice_level": 50,
        "mode": "invalid_mode"
    }
    response = client.post("/rewrite", json=payload)
    assert response.status_code == 422
