"""Sidecar health check endpoint."""

import chromadb
from fastapi import APIRouter
from sidecar import config

router = APIRouter()

@router.get("/health")
def get_health():
    """
    Checks the status of the ChromaDB collections and the FT endpoint state.
    Always returns HTTP 200, representing ok/degraded state via the status field.
    """
    my_voice_exists = False
    my_voice_count = 0
    ceo_archetype_exists = False
    ceo_archetype_count = 0
    
    try:
        # Initialize a persistent client for validation
        client = chromadb.PersistentClient(path=config.CHROMA_PATH)
        
        # Validate my_voice collection
        try:
            col = client.get_collection("my_voice")
            my_voice_exists = True
            my_voice_count = col.count()
        except Exception:
            pass
            
        # Validate ceo_archetype collection
        try:
            col2 = client.get_collection("ceo_archetype")
            ceo_archetype_exists = True
            ceo_archetype_count = col2.count()
        except Exception:
            pass
            
    except Exception:
        # Gracefully catch persistent client errors and report as degraded
        pass
        
    # Determine status based on exists and count > 0 for both collections
    if my_voice_exists and my_voice_count > 0 and ceo_archetype_exists and ceo_archetype_count > 0:
        status = "ok"
    else:
        status = "degraded"
        
    return {
        "status": status,
        "collections": {
            "my_voice": {"exists": my_voice_exists, "count": my_voice_count},
            "ceo_archetype": {"exists": ceo_archetype_exists, "count": ceo_archetype_count}
        },
        "ft_endpoint_active": config.FT_ENDPOINT_ACTIVE
    }
