import os
# Set mock environment variables before import to pass validation
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint.azure.com"
os.environ["AZURE_OPENAI_KEY"] = "mock-key-value"

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from sidecar.main import app

client = TestClient(app)

@patch("sidecar.health.chromadb.PersistentClient")
def test_health_ok(mock_chroma_client):
    """Verifies that /health returns status ok when both collections exist and are non-empty."""
    mock_db = MagicMock()
    mock_col_voice = MagicMock()
    mock_col_voice.count.return_value = 50
    mock_col_ceo = MagicMock()
    mock_col_ceo.count.return_value = 120
    
    def get_col_side_effect(name):
        if name == "my_voice":
            return mock_col_voice
        elif name == "ceo_archetype":
            return mock_col_ceo
        raise ValueError("Not found")
        
    mock_db.get_collection.side_effect = get_col_side_effect
    mock_chroma_client.return_value = mock_db
    
    with patch("sidecar.config.FT_ENDPOINT_ACTIVE", True):
        response = client.get("/health")
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["collections"]["my_voice"]["exists"] is True
    assert data["collections"]["my_voice"]["count"] == 50
    assert data["collections"]["ceo_archetype"]["exists"] is True
    assert data["collections"]["ceo_archetype"]["count"] == 120
    assert data["ft_endpoint_active"] is True

@patch("sidecar.health.chromadb.PersistentClient")
def test_health_degraded_missing_collection(mock_chroma_client):
    """Verifies status is degraded when one collection is missing."""
    mock_db = MagicMock()
    
    def get_col_side_effect(name):
        if name == "my_voice":
            mock_col = MagicMock()
            mock_col.count.return_value = 100
            return mock_col
        # Raise exception for ceo_archetype
        raise Exception("Collection missing")
        
    mock_db.get_collection.side_effect = get_col_side_effect
    mock_chroma_client.return_value = mock_db
    
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["collections"]["my_voice"]["exists"] is True
    assert data["collections"]["ceo_archetype"]["exists"] is False

@patch("sidecar.health.chromadb.PersistentClient")
def test_health_degraded_empty_collection(mock_chroma_client):
    """Verifies status is degraded when a collection has a count of 0."""
    mock_db = MagicMock()
    mock_col_voice = MagicMock()
    mock_col_voice.count.return_value = 10
    mock_col_ceo = MagicMock()
    mock_col_ceo.count.return_value = 0  # Empty!
    
    def get_col_side_effect(name):
        if name == "my_voice":
            return mock_col_voice
        elif name == "ceo_archetype":
            return mock_col_ceo
        raise ValueError("Not found")
        
    mock_db.get_collection.side_effect = get_col_side_effect
    mock_chroma_client.return_value = mock_db
    
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["collections"]["my_voice"]["count"] == 10
    assert data["collections"]["ceo_archetype"]["count"] == 0
