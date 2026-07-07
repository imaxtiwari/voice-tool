import os
# Mock env configuration before import
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock.azure.com"
os.environ["AZURE_OPENAI_KEY"] = "mockkey"

import pytest
from unittest.mock import MagicMock, patch
from sidecar.corpus import retrieve, get_top_similarity, collection_exists, collection_count
from sidecar import corpus

@pytest.fixture(autouse=True)
def reset_globals():
    corpus._chroma_client = None
    corpus._azure_client = None
    yield
    corpus._chroma_client = None
    corpus._azure_client = None

@patch("sidecar.corpus.chromadb.PersistentClient")
@patch("sidecar.corpus.AzureOpenAI")
def test_retrieve_success(mock_azure, mock_chroma):
    """Verifies that retrieve() queries ChromaDB correctly and returns cosine similarity (1 - distance)."""
    # Mock Azure OpenAI Embeddings API
    mock_azure_client = MagicMock()
    mock_emb_res = MagicMock()
    mock_emb_data = MagicMock()
    mock_emb_data.embedding = [0.1] * 1536
    mock_emb_res.data = [mock_emb_data]
    mock_azure_client.embeddings.create.return_value = mock_emb_res
    mock_azure.return_value = mock_azure_client

    # Mock ChromaDB query output
    mock_chroma_client = MagicMock()
    mock_col = MagicMock()
    mock_col.query.return_value = {
        "documents": [["Mock chunk text"]],
        "distances": [[0.2]],
        "metadatas": [[{"char_count": 15}]]
    }
    mock_chroma_client.get_collection.return_value = mock_col
    mock_chroma.return_value = mock_chroma_client

    res = retrieve("hello world", "my_voice", n=1)
    
    assert len(res) == 1
    assert res[0]["text"] == "Mock chunk text"
    assert abs(res[0]["similarity"] - 0.8) < 1e-5  # distance 0.2 -> similarity 0.8
    assert res[0]["metadata"] == {"char_count": 15}

@patch("sidecar.corpus.chromadb.PersistentClient")
def test_retrieve_collection_not_found(mock_chroma):
    """Verifies that retrieve() returns an empty list and does not raise on missing collections."""
    mock_chroma_client = MagicMock()
    mock_chroma_client.get_collection.side_effect = Exception("Collection not found")
    mock_chroma.return_value = mock_chroma_client

    res = retrieve("hello world", "missing_collection")
    assert res == []

def test_get_top_similarity_empty():
    """Verifies that get_top_similarity() returns 0.0 on empty lists, and the correct similarity otherwise."""
    assert get_top_similarity([]) == 0.0
    assert get_top_similarity([{"similarity": 0.85}]) == 0.85
