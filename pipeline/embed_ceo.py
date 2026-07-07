"""Embed CEO Archetype documents.

This script reads the raw scraped CEO texts, chunks them,
embeds them, and stores them in ChromaDB collection 'ceo_archetype'.
"""

import os
import sys
import chromadb
from datetime import datetime
from dotenv import load_dotenv
from openai import AzureOpenAI
from pipeline.embed_utils import chunk_text, embed_batch, batch_add_to_chroma

RAW_DOCS_DIR = "pipeline/data/raw_ceo_docs"

def embed_ceo_docs(chroma_path, docs_dir, drop_collection=False):
    """
    Core embedding logic for CEO Archetype.
    """
    if not os.path.exists(docs_dir):
        sys.stderr.write(f"Error: Scraped docs directory '{docs_dir}' does not exist.\n")
        sys.exit(1)
        
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    deployment_name = os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    
    missing = []
    if not azure_endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not azure_key:
        missing.append("AZURE_OPENAI_KEY")
        
    if missing:
        sys.stderr.write(f"Error: Required environment variables are missing: {', '.join(missing)}\n")
        sys.exit(1)
        
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    
    if drop_collection:
        try:
            chroma_client.delete_collection("ceo_archetype")
        except Exception:
            pass
            
    try:
        collection = chroma_client.get_collection("ceo_archetype")
    except Exception:
        collection = chroma_client.create_collection("ceo_archetype")
        
    openai_client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=azure_key,
        api_version="2023-05-15"
    )
    
    txt_files = [f for f in os.listdir(docs_dir) if f.lower().endswith(".txt")]
    if not txt_files:
        print("No CEO text files found to embed.")
        return
        
    all_chunks = []
    today_iso = datetime.utcnow().date().isoformat()
    
    for filename in txt_files:
        filepath = os.path.join(docs_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
            
        chunks = chunk_text(text, target_words=337, overlap_words=37)
        
        for chunk_idx, chunk_str in enumerate(chunks):
            filename_no_ext = os.path.splitext(filename)[0]
            chunk_id = f"{filename_no_ext}_{chunk_idx}"
            
            chunk_item = {
                "id": chunk_id,
                "document": chunk_str,
                "metadata": {
                    "source_file": filename,
                    "chunk_index": chunk_idx,
                    "date_scraped": today_iso
                }
            }
            all_chunks.append(chunk_item)
            
    texts_to_embed = [c["document"] for c in all_chunks]
    embeddings = embed_batch(texts_to_embed, openai_client, deployment_name)
    
    ids = [c["id"] for c in all_chunks]
    documents = [c["document"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]
    
    batch_add_to_chroma(collection, ids, documents, embeddings, metadatas, batch_size=100)
    
    added_count = sum(1 for emb in embeddings if emb is not None)
    
    print(f"Done. Embedded {len(txt_files)} files, {added_count} chunks into ceo_archetype collection.")
    print(f"ChromaDB path: {chroma_path}")

def main():
    load_dotenv()
    chroma_path = os.getenv("CHROMA_PATH")
    if not chroma_path:
        sys.stderr.write("Error: CHROMA_PATH environment variable is missing.\n")
        sys.exit(1)
        
    embed_ceo_docs(chroma_path, RAW_DOCS_DIR, drop_collection=False)

if __name__ == "__main__":
    main()
