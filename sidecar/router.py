"""Sidecar rewrite routing logic coordinating RAG and Fine-Tuning."""

from openai import AzureOpenAI
from sidecar import config
from sidecar.corpus import retrieve, get_top_similarity
from sidecar.prompt_builder import get_rules

class CorpusEmptyError(Exception):
    """Raised when a required ChromaDB collection is empty or missing."""
    pass

def get_azure_client():
    """Initializes the Azure OpenAI client."""
    return AzureOpenAI(
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_KEY,
        api_version="2023-05-15"
    )

def format_chunks(chunks: list[dict]) -> str:
    """Formats a list of collection chunks into a numbered list string."""
    if not chunks:
        return "No examples available."
    formatted = []
    for idx, chunk in enumerate(chunks[:3]):
        formatted.append(f"Example {idx + 1}:\n{chunk['text']}")
    return "\n\n".join(formatted)

def rewrite_with_rag(text: str, chunks: list[dict], de_ai_level: int, 
                     voice_level: int, mode: str) -> dict:
    """Executes rewrite request using RAG prompts and base chat model."""
    client = get_azure_client()
    rules = get_rules(de_ai_level)
    formatted_rules = "\n".join(f"- {rule}" for rule in rules)
    
    system_prompt = (
        f"You rewrite emails. Apply these rules exactly:\n{formatted_rules}\n\n"
        f"Here are examples of the target writing style:\n{format_chunks(chunks)}\n\n"
        "Preserve all facts, dates, commitments, and names exactly. "
        "Return ONLY the rewritten email body. No commentary."
    )
    
    response = client.chat.completions.create(
        model=config.AZURE_OPENAI_DEPLOYMENT_BASE,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        temperature=0.3
    )
    rewritten_text = response.choices[0].message.content.strip()
    return {"rewritten_text": rewritten_text, "model_used": "rag_fallback"}

def rewrite_with_ft(text: str, de_ai_level: int, voice_level: int) -> dict:
    """Executes rewrite request using fine-tuned model deployment endpoint."""
    client = get_azure_client()
    rules = get_rules(de_ai_level)
    formatted_rules = "\n".join(f"- {rule}" for rule in rules)
    
    # Fetch top chunks for consistency in system prompt structure
    chunks = retrieve(text, "my_voice", n=3)
    
    system_prompt = (
        f"You rewrite emails. Apply these rules exactly:\n{formatted_rules}\n\n"
        f"Here are examples of the target writing style:\n{format_chunks(chunks)}\n\n"
        "Preserve all facts, dates, commitments, and names exactly. "
        "Return ONLY the rewritten email body. No commentary."
    )
    
    response = client.chat.completions.create(
        model=config.AZURE_OPENAI_DEPLOYMENT_FT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        temperature=0.3
    )
    rewritten_text = response.choices[0].message.content.strip()
    return {"rewritten_text": rewritten_text, "model_used": "ft"}

def route_rewrite(mode: str, de_ai_level: int, voice_level: int, text: str) -> dict:
    """Routes the rewrite request to RAG or FT depending on confidence levels."""
    if mode == "ceo_archetype":
        chunks = retrieve(text, "ceo_archetype", n=3)
        if not chunks:
            raise CorpusEmptyError("ceo_archetype collection is empty. Run embed_ceo.py first.")
        return rewrite_with_rag(text, chunks, de_ai_level, voice_level, mode)

    # mode == "my_voice"
    chunks = retrieve(text, "my_voice", n=3)
    confidence = get_top_similarity(chunks)

    if config.FT_ENDPOINT_ACTIVE and config.AZURE_OPENAI_DEPLOYMENT_FT:
        if confidence >= 0.65:
            return rewrite_with_ft(text, de_ai_level, voice_level)
            
    return rewrite_with_rag(text, chunks, de_ai_level, voice_level, "my_voice")
