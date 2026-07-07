"""Sidecar rewrite endpoint handling request routing and post-processing."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from sidecar.router import route_rewrite, CorpusEmptyError
from sidecar.corpus import retrieve, get_top_similarity
from sidecar.diff import generate_diff
from sidecar.fact_guard import flag_facts

router = APIRouter()

class RewriteRequest(BaseModel):
    text: str = Field(..., description="The input text to rewrite")
    de_ai_level: int = Field(..., ge=0, le=100, description="Styling level parameter between 0 and 100")
    voice_level: int = Field(..., ge=0, le=100, description="Styling level parameter between 0 and 100")
    mode: str = Field(..., description="Mode selection: my_voice or ceo_archetype")

    @field_validator("text")
    @classmethod
    def validate_non_empty_text(cls, v):
        if not v.strip():
            raise ValueError("text must not be empty")
        return v

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v):
        if v not in ("my_voice", "ceo_archetype"):
            raise ValueError("mode must be 'my_voice' or 'ceo_archetype'")
        return v

@router.post("/rewrite")
def post_rewrite(request: RewriteRequest):
    """
    Rewrite handler. Routes rewrite request to RAG/FT models,
    computes word-level diffs, flags factual changes, and returns the response.
    """
    try:
        result = route_rewrite(request.mode, request.de_ai_level, request.voice_level, request.text)
    except CorpusEmptyError as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "corpus_empty", "message": str(e)}
        )

    # Compute word-level diffs and guard facts
    diff_objects = generate_diff(request.text, result["rewritten_text"])
    diff_objects = flag_facts(diff_objects)

    # Compute top similarity score
    chunks = retrieve(request.text, request.mode, n=3)
    confidence = get_top_similarity(chunks)

    return {
        "rewritten_text": result["rewritten_text"],
        "diff": diff_objects,
        "retrieval_confidence": confidence,
        "model_used": result["model_used"]
    }
