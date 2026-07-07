"""Shared embedding utilities for voice-tool pipeline."""

import time
import sys

def chunk_text(text, target_words=337, overlap_words=37):
    """
    Chunks text by words.
    Target chunk size: target_words (default 337).
    Overlap: overlap_words (default 37).
    """
    words = text.split()
    if not words:
        return []
    if len(words) <= target_words:
        return [" ".join(words)]
        
    chunks = []
    start = 0
    while start < len(words):
        end = start + target_words
        chunk = words[start:end]
        chunks.append(" ".join(chunk))
        if end >= len(words):
            break
        start = end - overlap_words
        if start >= end:
            start = end - 1
    return chunks

def embed_batch(texts, azure_client, deployment):
    """
    Embeds a list of texts using Azure OpenAI, batching in groups of 20,
    with 0.5s sleep and 429 rate limit retry logic.
    """
    results = []
    for i in range(0, len(texts), 20):
        batch = texts[i:i+20]
        time.sleep(0.5)
        try:
            response = azure_client.embeddings.create(input=batch, model=deployment)
            batch_embs = [item.embedding for item in response.data]
            results.extend(batch_embs)
        except Exception as e:
            is_429 = False
            if hasattr(e, "status_code") and e.status_code == 429:
                is_429 = True
            elif "429" in str(e) or "rate limit" in str(e).lower():
                is_429 = True
                
            if is_429:
                sys.stderr.write("Azure OpenAI Rate Limit (429) hit. Waiting 30s to retry once...\n")
                time.sleep(30)
                try:
                    response = azure_client.embeddings.create(input=batch, model=deployment)
                    batch_embs = [item.embedding for item in response.data]
                    results.extend(batch_embs)
                except Exception as retry_e:
                    sys.stderr.write(f"Azure OpenAI Rate Limit retry failed: {retry_e}\n")
                    results.extend([None] * len(batch))
            else:
                sys.stderr.write(f"Azure OpenAI Error: {e}\n")
                results.extend([None] * len(batch))
    return results

def batch_add_to_chroma(collection, ids, documents, embeddings, metadatas, batch_size=100):
    """
    Adds documents, embeddings, and metadata to ChromaDB in batches of batch_size,
    automatically filtering out any None embeddings from failed API calls.
    """
    # Filter out failed (None) embeddings to avoid ChromaDB errors
    valid_indices = [i for i, emb in enumerate(embeddings) if emb is not None]
    
    f_ids = [ids[i] for i in valid_indices]
    f_documents = [documents[i] for i in valid_indices]
    f_embeddings = [embeddings[i] for i in valid_indices]
    f_metadatas = [metadatas[i] for i in valid_indices]
    
    for i in range(0, len(f_ids), batch_size):
        collection.add(
            ids=f_ids[i:i+batch_size],
            documents=f_documents[i:i+batch_size],
            embeddings=f_embeddings[i:i+batch_size],
            metadatas=f_metadatas[i:i+batch_size]
        )
