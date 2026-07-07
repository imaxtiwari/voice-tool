"""Embed corpus module.

This script reads the cleaned sent emails, chunks the bodies,
embeds them using Azure OpenAI, and stores them in ChromaDB.
"""

import os
import sys
import json
import time
import chromadb
from dotenv import load_dotenv
from openai import AzureOpenAI

INPUT_PATH = "pipeline/data/sent_clean.jsonl"

def chunk_text_by_words(text, chunk_size=300, overlap=37):
    """
    Chunks text by words.
    Target chunk size: chunk_size.
    Overlap: overlap.
    """
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [" ".join(words)]
        
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = words[start:end]
        chunks.append(" ".join(chunk))
        if end >= len(words):
            break
        start = end - overlap
        if start >= end:
            start = end - 1
    return chunks

def get_embeddings(client, texts, model_name):
    """
    Call Azure OpenAI embedding API with rate limiting and 429 retry logic.
    """
    # Sleep 0.5s before every Azure call as specified
    time.sleep(0.5)
    try:
        response = client.embeddings.create(input=texts, model=model_name)
        return [item.embedding for item in response.data]
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
                response = client.embeddings.create(input=texts, model=model_name)
                return [item.embedding for item in response.data]
            except Exception as retry_e:
                sys.stderr.write(f"Azure OpenAI Rate Limit retry failed: {retry_e}\n")
                return None
        else:
            sys.stderr.write(f"Azure OpenAI Error: {e}\n")
            return None

def add_to_chroma(collection, chunks):
    """Adds a list of chunks to the ChromaDB collection."""
    ids = [c["id"] for c in chunks]
    embeddings = [c["embedding"] for c in chunks]
    documents = [c["document"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )

def main():
    load_dotenv()
    
    # Check required environment variables
    chroma_path = os.getenv("CHROMA_PATH")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    deployment_name = os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    
    missing = []
    if not chroma_path:
        missing.append("CHROMA_PATH")
    if not azure_endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not azure_key:
        missing.append("AZURE_OPENAI_KEY")
        
    if missing:
        sys.stderr.write(f"Error: Required environment variables are missing: {', '.join(missing)}\n")
        sys.exit(1)
        
    if not os.path.exists(INPUT_PATH):
        sys.stderr.write(f"Error: Cleaned email corpus file '{INPUT_PATH}' does not exist.\n")
        sys.exit(1)
        
    # Count total emails
    total_emails = 0
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                total_emails += 1
                
    # Initialize ChromaDB
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    try:
        chroma_client.delete_collection("my_voice")
    except Exception:
        pass
    collection = chroma_client.create_collection("my_voice")
    
    # Initialize Azure OpenAI client
    openai_client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=azure_key,
        api_version="2023-05-15"
    )
    
    pending_chunks = []
    embedded_chunks = []
    total_chunks_generated = 0
    total_chunks_added = 0
    email_count = 0
    
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            email_count += 1
            try:
                email_data = json.loads(line)
            except json.JSONDecodeError:
                continue
                
            subject = email_data.get("subject", "")
            date = email_data.get("date", "")
            body = email_data.get("body", "")
            
            # Chunk the body (approx 300 words per chunk with 37 words overlap)
            chunks = chunk_text_by_words(body, chunk_size=300, overlap=37)
            
            for chunk_idx, chunk_text in enumerate(chunks):
                chunk_item = {
                    "id": f"{email_count - 1}_{chunk_idx}",
                    "document": chunk_text,
                    "metadata": {
                        "subject": subject,
                        "date": date,
                        "chunk_index": chunk_idx,
                        "char_count": len(chunk_text)
                    }
                }
                pending_chunks.append(chunk_item)
                total_chunks_generated += 1
                
            # Process pending chunks when we have at least 20
            while len(pending_chunks) >= 20:
                batch = pending_chunks[:20]
                pending_chunks = pending_chunks[20:]
                
                batch_texts = [c["document"] for c in batch]
                embeddings = get_embeddings(openai_client, batch_texts, deployment_name)
                
                if embeddings:
                    for item, emb in zip(batch, embeddings):
                        item["embedding"] = emb
                        embedded_chunks.append(item)
                else:
                    sys.stderr.write(f"Skipping batch of {len(batch)} chunks due to embedding error.\n")
                    
            # Add to ChromaDB when we have at least 100 embedded chunks
            while len(embedded_chunks) >= 100:
                batch_to_add = embedded_chunks[:100]
                embedded_chunks = embedded_chunks[100:]
                add_to_chroma(collection, batch_to_add)
                total_chunks_added += len(batch_to_add)
                
            if email_count % 50 == 0:
                print(f"Embedded {email_count}/{total_emails} emails ({total_chunks_added} chunks total so far)...")
                
    # Process remaining pending chunks
    while pending_chunks:
        batch = pending_chunks[:20]
        pending_chunks = pending_chunks[20:]
        
        batch_texts = [c["document"] for c in batch]
        embeddings = get_embeddings(openai_client, batch_texts, deployment_name)
        
        if embeddings:
            for item, emb in zip(batch, embeddings):
                item["embedding"] = emb
                embedded_chunks.append(item)
        else:
            sys.stderr.write(f"Skipping final batch of {len(batch)} chunks due to embedding error.\n")
            
    # Add remaining embedded chunks
    if embedded_chunks:
        add_to_chroma(collection, embedded_chunks)
        total_chunks_added += len(embedded_chunks)
        
    print(f"Done. Embedded {email_count} emails, {total_chunks_added} chunks into my_voice collection.")
    print(f"ChromaDB path: {chroma_path}")

if __name__ == "__main__":
    main()
