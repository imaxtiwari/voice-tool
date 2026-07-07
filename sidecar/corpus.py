"""ChromaDB collection interface and document retrieval."""

import chromadb
from openai import AzureOpenAI
from sidecar import config

_chroma_client = None
_azure_client = None

def get_chroma_client():
    """Gets or initializes the persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    return _chroma_client

def get_azure_client():
    """Gets or initializes the Azure OpenAI client."""
    global _azure_client
    if _azure_client is None:
        _azure_client = AzureOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_KEY,
            api_version="2023-05-15"
        )
    return _azure_client

def collection_exists(name: str) -> bool:
    """Returns True if the ChromaDB collection exists, False otherwise."""
    client = get_chroma_client()
    try:
        client.get_collection(name)
        return True
    except Exception:
        return False

def collection_count(name: str) -> int:
    """Returns the document count of a collection, or 0 if missing/empty."""
    client = get_chroma_client()
    try:
        col = client.get_collection(name)
        return col.count()
    except Exception:
        return 0

def retrieve(text: str, collection: str, n: int = 3) -> list[dict]:
    """
    Embeds the input text and queries ChromaDB.
    Returns the top-n results with cosine similarity scores.
    """
    if not text.strip():
        return []

    client = get_chroma_client()
    try:
        col = client.get_collection(collection)
    except Exception:
        return []

    # Get Azure text embedding
    azure_client = get_azure_client()
    try:
        response = azure_client.embeddings.create(
            input=[text],
            model=config.AZURE_EMBEDDING_DEPLOYMENT
        )
        embedding = response.data[0].embedding
    except Exception:
        return []

    # Query the collection
    try:
        res = col.query(query_embeddings=[embedding], n_results=n)
    except Exception:
        return []

    results = []
    if res and res.get("documents") and len(res["documents"]) > 0:
        docs = res["documents"][0]
        distances = res["distances"][0] if res.get("distances") else [0.0] * len(docs)
        metadatas = res["metadatas"][0] if res.get("metadatas") else [{}] * len(docs)
        
        for doc, dist, meta in zip(docs, distances, metadatas):
            similarity = 1.0 - float(dist)
            results.append({
                "text": doc,
                "similarity": similarity,
                "metadata": meta
            })
            
    return results

def get_top_similarity(chunks: list[dict]) -> float:
    """Helper to return the highest similarity score from a list of retrieval chunks."""
    return chunks[0]["similarity"] if chunks else 0.0
