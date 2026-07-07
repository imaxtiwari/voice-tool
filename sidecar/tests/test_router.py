import os
# Set mock environment variables before import to pass validation
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint.azure.com"
os.environ["AZURE_OPENAI_KEY"] = "mock-key-value"

import pytest
from unittest.mock import MagicMock, patch
from sidecar.router import route_rewrite, CorpusEmptyError
from sidecar.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

@patch("sidecar.router.retrieve")
def test_ceo_archetype_empty_corpus(mock_retrieve):
    """Verifies CorpusEmptyError is raised when ceo_archetype retrieval returns no chunks."""
    mock_retrieve.return_value = []
    with pytest.raises(CorpusEmptyError):
        route_rewrite("ceo_archetype", 50, 50, "hello")

@patch("sidecar.router.retrieve")
@patch("sidecar.router.rewrite_with_rag")
def test_ceo_archetype_with_chunks(mock_rewrite_rag, mock_retrieve):
    """Verifies route_rewrite calls rewrite_with_rag when chunks are found for ceo_archetype."""
    mock_retrieve.return_value = [{"text": "chunk1", "similarity": 0.8}]
    mock_rewrite_rag.return_value = {"rewritten_text": "rewritten", "model_used": "rag_fallback"}
    
    res = route_rewrite("ceo_archetype", 50, 50, "hello")
    
    assert res["model_used"] == "rag_fallback"
    mock_rewrite_rag.assert_called_once()

@patch("sidecar.router.retrieve")
@patch("sidecar.router.rewrite_with_ft")
@patch("sidecar.router.get_top_similarity")
def test_my_voice_ft_active_high_confidence(mock_get_top, mock_rewrite_ft, mock_retrieve):
    """Verifies rewrite_with_ft is used when FT is active and retrieval confidence is high (>=0.65)."""
    mock_retrieve.return_value = [{"text": "chunk1", "similarity": 0.8}]
    mock_get_top.return_value = 0.80
    mock_rewrite_ft.return_value = {"rewritten_text": "rewritten ft", "model_used": "ft"}
    
    with patch("sidecar.config.FT_ENDPOINT_ACTIVE", True):
        with patch("sidecar.config.AZURE_OPENAI_DEPLOYMENT_FT", "my-ft-model"):
            res = route_rewrite("my_voice", 50, 50, "hello")
            
    assert res["model_used"] == "ft"
    mock_rewrite_ft.assert_called_once()

@patch("sidecar.router.retrieve")
@patch("sidecar.router.rewrite_with_rag")
@patch("sidecar.router.get_top_similarity")
def test_my_voice_ft_active_low_confidence(mock_get_top, mock_rewrite_rag, mock_retrieve):
    """Verifies rewrite_with_rag is used when FT is active but retrieval confidence is low (<0.65)."""
    mock_retrieve.return_value = [{"text": "chunk1", "similarity": 0.4}]
    mock_get_top.return_value = 0.40
    mock_rewrite_rag.return_value = {"rewritten_text": "rewritten rag", "model_used": "rag_fallback"}
    
    with patch("sidecar.config.FT_ENDPOINT_ACTIVE", True):
        with patch("sidecar.config.AZURE_OPENAI_DEPLOYMENT_FT", "my-ft-model"):
            res = route_rewrite("my_voice", 50, 50, "hello")
            
    assert res["model_used"] == "rag_fallback"
    mock_rewrite_rag.assert_called_once()

@patch("sidecar.router.retrieve")
@patch("sidecar.router.rewrite_with_rag")
@patch("sidecar.router.get_top_similarity")
def test_my_voice_ft_inactive(mock_get_top, mock_rewrite_rag, mock_retrieve):
    """Verifies rewrite_with_rag is used regardless of confidence if FT is inactive."""
    mock_retrieve.return_value = [{"text": "chunk1", "similarity": 0.8}]
    mock_get_top.return_value = 0.80
    mock_rewrite_rag.return_value = {"rewritten_text": "rewritten rag", "model_used": "rag_fallback"}
    
    with patch("sidecar.config.FT_ENDPOINT_ACTIVE", False):
        res = route_rewrite("my_voice", 50, 50, "hello")
        
    assert res["model_used"] == "rag_fallback"
    mock_rewrite_rag.assert_called_once()

@patch("sidecar.rewrite.route_rewrite")
@patch("sidecar.rewrite.retrieve")
@patch("sidecar.rewrite.get_top_similarity")
def test_full_rewrite_response_shape(mock_get_top, mock_retrieve, mock_route_rewrite):
    """Verifies response JSON has the correct fields and types for successful rewrites."""
    mock_route_rewrite.return_value = {"rewritten_text": "rewritten email text", "model_used": "rag_fallback"}
    mock_retrieve.return_value = [{"text": "chunk1", "similarity": 0.7}]
    mock_get_top.return_value = 0.70
    
    payload = {
        "text": "original email text",
        "de_ai_level": 80,
        "voice_level": 50,
        "mode": "my_voice"
    }
    
    response = client.post("/rewrite", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "rewritten_text" in data
    assert "diff" in data
    assert isinstance(data["diff"], list)
    assert "retrieval_confidence" in data
    assert isinstance(data["retrieval_confidence"], float)
    assert data["model_used"] == "rag_fallback"

@patch("sidecar.rewrite.route_rewrite")
def test_corpus_empty_returns_503(mock_route_rewrite):
    """Verifies HTTP 503 is returned when a CorpusEmptyError is raised."""
    mock_route_rewrite.side_effect = CorpusEmptyError("ceo_archetype collection empty")
    
    payload = {
        "text": "original email text",
        "de_ai_level": 80,
        "voice_level": 50,
        "mode": "ceo_archetype"
    }
    
    response = client.post("/rewrite", json=payload)
    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "corpus_empty"
    assert "message" in data
