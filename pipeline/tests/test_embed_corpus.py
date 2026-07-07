import os
import json
import pytest
from unittest.mock import MagicMock, patch
from pipeline.embed_corpus import main

@patch("pipeline.embed_corpus.chromadb.PersistentClient")
@patch("pipeline.embed_corpus.AzureOpenAI")
@patch("pipeline.embed_utils.time.sleep")
def test_embed_corpus_batches_and_metadata(mock_sleep, mock_azure, mock_chroma, tmp_path):
    input_path = tmp_path / "sent_clean.jsonl"
    emails = []
    # 60 emails, each having 50 words (produces 1 chunk each)
    for i in range(60):
        emails.append({
            "subject": f"Subj {i}",
            "body": f"bodyword " * 50,
            "date": f"Date {i}",
            "char_count": 100
        })
    with open(input_path, "w", encoding="utf-8") as f:
        for email in emails:
            f.write(json.dumps(email) + "\n")
            
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.create_collection.return_value = mock_collection
    mock_chroma.return_value = mock_client
    
    mock_openai_instance = MagicMock()
    mock_azure.return_value = mock_openai_instance
    
    # Return 20 embeddings per call
    fake_embeddings = [[0.1] * 1536 for _ in range(20)]
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=emb) for emb in fake_embeddings]
    mock_openai_instance.embeddings.create.return_value = mock_response
    
    with patch.dict(os.environ, {
        "CHROMA_PATH": "/fake/chroma",
        "AZURE_OPENAI_ENDPOINT": "https://fake.azure.com",
        "AZURE_OPENAI_KEY": "fakekey",
        "AZURE_EMBEDDING_DEPLOYMENT": "text-embedding-3-small"
    }):
        with patch("pipeline.embed_corpus.INPUT_PATH", str(input_path)):
            main()
            
    assert mock_openai_instance.embeddings.create.call_count == 3
    for call_args in mock_openai_instance.embeddings.create.call_args_list:
        kwargs = call_args[1]
        assert len(kwargs["input"]) == 20
        assert kwargs["model"] == "text-embedding-3-small"
        
    mock_collection.add.assert_called_once()
    add_kwargs = mock_collection.add.call_args[1]
    assert len(add_kwargs["ids"]) == 60
    assert len(add_kwargs["embeddings"]) == 60
    assert len(add_kwargs["documents"]) == 60
    assert len(add_kwargs["metadatas"]) == 60
    
    first_metadata = add_kwargs["metadatas"][0]
    assert "subject" in first_metadata
    assert "date" in first_metadata
    assert "chunk_index" in first_metadata
    assert "char_count" in first_metadata
