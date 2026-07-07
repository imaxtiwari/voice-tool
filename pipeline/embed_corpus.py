"""Embed corpus module.

This script reads the cleaned sent emails, chunks the bodies,
embeds them using Azure OpenAI, and stores them in ChromaDB.
"""

import os
import sys
import json
import chromadb
from dotenv import load_dotenv
from openai import AzureOpenAI
from pipeline.embed_utils import chunk_text, embed_batch, batch_add_to_chroma

INPUT_PATH = "pipeline/data/sent_clean.jsonl"

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
    
    all_chunks = []
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
            
            # Chunk the body (target 300 words, 37 words overlap)
            chunks = chunk_text(body, target_words=300, overlap_words=37)
            
            for chunk_idx, chunk_str in enumerate(chunks):
                chunk_item = {
                    "id": f"{email_count - 1}_{chunk_idx}",
                    "document": chunk_str,
                    "metadata": {
                        "subject": subject,
                        "date": date,
                        "chunk_index": chunk_idx,
                        "char_count": len(chunk_str)
                    }
                }
                all_chunks.append(chunk_item)
                
            if email_count % 50 == 0:
                print(f"Embedded {email_count}/{total_emails} emails ({len(all_chunks)} chunks total so far)...")
                
    # Now embed all chunks in batches
    texts_to_embed = [c["document"] for c in all_chunks]
    embeddings = embed_batch(texts_to_embed, openai_client, deployment_name)
    
    # Add to ChromaDB in batches
    ids = [c["id"] for c in all_chunks]
    documents = [c["document"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]
    
    batch_add_to_chroma(collection, ids, documents, embeddings, metadatas, batch_size=100)
    
    # Total successfully added chunks
    added_chunks_count = sum(1 for emb in embeddings if emb is not None)
    
    print(f"Done. Embedded {email_count} emails, {added_chunks_count} chunks into my_voice collection.")
    print(f"ChromaDB path: {chroma_path}")

if __name__ == "__main__":
    main()
