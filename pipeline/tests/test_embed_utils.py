import pytest
from unittest.mock import MagicMock, patch
from pipeline.embed_utils import chunk_text, embed_batch, batch_add_to_chroma

def test_chunk_text_500_words():
    words = [f"word{i}" for i in range(500)]
    text = " ".join(words)
    chunks = chunk_text(text, target_words=337, overlap_words=37)
    assert len(chunks) == 2
    
    c1 = chunks[0].split()
    c2 = chunks[1].split()
    assert len(c1) == 337
    assert len(c2) == 200  # 500 - (337 - 37) = 200
    
    # Overlap
    assert c1[-37:] == c2[:37]

def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []

@patch("pipeline.embed_utils.time.sleep")
def test_embed_batch_groups_of_20(mock_sleep):
    mock_client = MagicMock()
    
    # 50 texts -> 3 batches: 20, 20, 10
    texts = [f"text{i}" for i in range(50)]
    
    # Side effect to return embeddings matching the batch input size
    def side_effect(input, model):
        res = MagicMock()
        res.data = [MagicMock(embedding=[0.1]*1536) for _ in range(len(input))]
        return res
        
    mock_client.embeddings.create.side_effect = side_effect
    
    embs = embed_batch(texts, mock_client, "deployment-name")
    
    assert len(embs) == 50
    assert mock_client.embeddings.create.call_count == 3
    assert mock_sleep.call_count == 3
    mock_sleep.assert_any_call(0.5)

def test_batch_add_to_chroma_groups_of_100():
    mock_collection = MagicMock()
    
    # 250 items
    ids = [f"id{i}" for i in range(250)]
    docs = [f"doc{i}" for i in range(250)]
    embs = [[0.1]*1536 for _ in range(250)]
    metadatas = [{"idx": i} for i in range(250)]
    
    # Embeddings for index 10 and 200 are None (verify filtering)
    embs[10] = None
    embs[200] = None
    
    # Total valid items = 248 -> batches of 100, 100, 48
    batch_add_to_chroma(mock_collection, ids, docs, embs, metadatas, batch_size=100)
    
    assert mock_collection.add.call_count == 3
    
    # Verify first batch size
    first_call_args = mock_collection.add.call_args_list[0][1]
    assert len(first_call_args["ids"]) == 100
    assert "id10" not in first_call_args["ids"]
    
    # Verify third batch size
    third_call_args = mock_collection.add.call_args_list[2][1]
    assert len(third_call_args["ids"]) == 48
