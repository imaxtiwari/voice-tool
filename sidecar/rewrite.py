"""Sidecar rewrite endpoint stub."""

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

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
    Stub rewrite handler. Validates parameters and echoes the input text.
    """
    return {
        "rewritten_text": request.text,
        "diff": [],
        "retrieval_confidence": 0.0,
        "model_used": "stub"
    }
