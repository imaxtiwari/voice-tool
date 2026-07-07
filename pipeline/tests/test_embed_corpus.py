import os
import json
import pytest
from unittest.mock import MagicMock, patch
from pipeline.embed_corpus import chunk_text_by_words, main, get_embeddings

def test_chunking_logic_100_words():
    text = "word " * 100
    chunks = chunk_text_by_words(text, chunk_size=300, overlap=37)
    assert len(chunks) == 1
    assert len(chunks[0].split()) == 100

def test_chunking_logic_500_words():
    words = [f"w{i}" for i in range(500)]
    text = " ".join(words)
    chunks = chunk_text_by_words(text, chunk_size=300, overlap=37)
    assert len(chunks) == 2
    
    chunk1_words = chunks[0].split()
    chunk2_words = chunks[1].split()
    
    assert len(chunk1_words) == 300
    assert len(chunk2_words) == 237  # 500 - 263 = 237
    
    # Overlap: last 37 words of chunk 1 are the first 37 of chunk 2
    last_37_of_1 = chunk1_words[-37:]
    first_37_of_2 = chunk2_words[:37]
    assert last_37_of_1 == first_37_of_2
    assert last_37_of_1 == words[263:300]

@patch("pipeline.embed_corpus.chromadb.PersistentClient")
@patch("pipeline.embed_corpus.AzureOpenAI")
@patch("pipeline.embed_corpus.time.sleep")
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

@patch("pipeline.embed_corpus.time.sleep")
def test_azure_429_retry_logic(mock_sleep):
    mock_client = MagicMock()
    error_429 = Exception("Rate limit exceeded. Status: 429")
    
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1, 0.2])]
    
    mock_client.embeddings.create.side_effect = [error_429, mock_response]
    
    embeddings = get_embeddings(mock_client, ["text"], "model-name")
    
    assert embeddings == [[0.1, 0.2]]
    mock_sleep.assert_any_call(0.5)
    mock_sleep.assert_any_call(30)
