"""Sidecar environment and application config."""

import os
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")

# Raise ValueError if required Azure OpenAI configuration is missing
if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_KEY:
    missing = []
    if not AZURE_OPENAI_ENDPOINT:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not AZURE_OPENAI_KEY:
        missing.append("AZURE_OPENAI_KEY")
    raise ValueError(f"Required Azure OpenAI credentials missing: {', '.join(missing)}")

AZURE_OPENAI_DEPLOYMENT_BASE = os.getenv("AZURE_OPENAI_DEPLOYMENT_BASE", "gpt-4o")
AZURE_OPENAI_DEPLOYMENT_FT = os.getenv("AZURE_OPENAI_DEPLOYMENT_FT", "")
AZURE_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

# Parse string representation of boolean config
ft_active_str = os.getenv("FT_ENDPOINT_ACTIVE", "false").lower()
FT_ENDPOINT_ACTIVE = ft_active_str in ("true", "1", "yes")

try:
    SIDECAR_PORT = int(os.getenv("SIDECAR_PORT", "8433"))
except ValueError:
    SIDECAR_PORT = 8433

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
