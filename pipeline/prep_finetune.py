"""Prep fine-tuning dataset and upload to Azure OpenAI."""

import os
import sys
import json
import random
import re
from datetime import datetime
from dotenv import load_dotenv
from openai import AzureOpenAI

INPUT_PATH = "pipeline/data/sent_clean.jsonl"
OUTPUT_PATH = "pipeline/data/finetune_upload.jsonl"
LOG_PATH = "pipeline/data/ft_version_log.json"

def add_em_dash_to_sentence(s):
    """Inserts an em-dash before the last clause/comma of a sentence if possible."""
    if ',' in s:
        parts = s.rsplit(',', 1)
        if parts[0].strip() and parts[1].strip():
            return f"{parts[0]} —{parts[1]}"
            
    for conj in [' and ', ' but ', ' so ', ' or ']:
        if conj in s:
            parts = s.rsplit(conj, 1)
            if parts[0].strip() and parts[1].strip():
                return f"{parts[0]} — {conj.strip()}{parts[1]}"
                
    words = s.split()
    if len(words) > 6:
        idx = len(words) - 3
        return " ".join(words[:idx]) + " — " + " ".join(words[idx:])
        
    return s

def ai_ify_body(body):
    """
    Applies 2-3 randomly selected rules to make the email body look 'AI-ified'.
    Uses random.seed(42) for reproducibility during generation.
    """
    # Split body into sentences (preserving punctuation)
    sentences = re.split(r'(?<=[.!?])\s+', body)
    if not sentences or not [s for s in sentences if s.strip()]:
        return body
        
    # Filter empty elements
    sentences = [s for s in sentences if s.strip()]

    # Choose 2 or 3 rules to apply
    num_rules = random.choice([2, 3])
    rules_to_apply = sorted(random.sample(range(5), num_rules))

    # Apply Rule A: Prepend first sentence with "I wanted to reach out to "
    if 0 in rules_to_apply:
        s = sentences[0]
        if s and s[0].isupper() and not s.startswith("I "):
            s = s[0].lower() + s[1:]
        sentences[0] = f"I wanted to reach out to {s}"

    # Apply Rule B: Replace use->utilize, help->facilitate, show->demonstrate
    if 1 in rules_to_apply:
        for idx, s in enumerate(sentences):
            s = re.sub(r'\buse\b', 'utilize', s)
            s = re.sub(r'\bUse\b', 'Utilize', s)
            s = re.sub(r'\bhelp\b', 'facilitate', s)
            s = re.sub(r'\bHelp\b', 'Facilitate', s)
            s = re.sub(r'\bshow\b', 'demonstrate', s)
            s = re.sub(r'\bShow\b', 'Demonstrate', s)
            sentences[idx] = s

    # Apply Rule C: Append " at your earliest convenience" to last sentence if it ends in '?'
    if 2 in rules_to_apply:
        last_s = sentences[-1].strip()
        if last_s.endswith('?'):
            sentences[-1] = last_s[:-1].strip() + " at your earliest convenience?"

    # Apply Rule D: Add " — " (em-dash) before last clause
    if 3 in rules_to_apply:
        for idx in range(len(sentences)):
            s = sentences[idx]
            if len(s.split()) > 5:
                sentences[idx] = add_em_dash_to_sentence(s)
                break

    # Apply Rule E: Prepend a short direct statement with "I believe that "
    if 4 in rules_to_apply:
        for idx in range(len(sentences)):
            s = sentences[idx]
            words = s.split()
            if 3 <= len(words) <= 12 and not s.strip().endswith('?'):
                if s and s[0].isupper() and not s.startswith("I "):
                    s = s[0].lower() + s[1:]
                sentences[idx] = f"I believe that {s}"
                break

    return " ".join(sentences)

def validate_example(example):
    """
    Validates a training example according to spec:
    - Has exactly 3 messages
    - Roles: system, user, assistant (in that order)
    - No field is empty string
    - assistant content != user content
    """
    messages = example.get("messages", [])
    if len(messages) != 3:
        return False
        
    roles = ["system", "user", "assistant"]
    for idx, role in enumerate(roles):
        msg = messages[idx]
        if msg.get("role") != role:
            return False
        content = msg.get("content", "")
        if not content or not content.strip():
            return False
            
    # Check that assistant content is not identical to user content
    user_content = messages[1].get("content", "")
    assistant_content = messages[2].get("content", "")
    if user_content == assistant_content:
        return False
        
    return True

def main(argv=None):
    load_dotenv()
    
    # We must seed random to ensure reproducibility
    random.seed(42)
    
    input_path = INPUT_PATH
    output_path = OUTPUT_PATH
    
    # Enable test overrides
    if argv and len(argv) > 0:
        input_path = argv[0]
    if argv and len(argv) > 1:
        output_path = argv[1]

    if not os.path.exists(input_path):
        sys.stderr.write(f"Error: Input file '{input_path}' not found.\n")
        sys.exit(1)

    raw_examples = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                email_data = json.loads(line)
            except json.JSONDecodeError:
                continue
                
            original_body = email_data.get("body", "")
            ai_ified = ai_ify_body(original_body)
            
            example = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a rewrite assistant. Rewrite the following email in the user's natural voice. Preserve all facts, dates, names, and commitments exactly. Do not add em-dashes as stylistic flourish. Do not add hedging. Do not add formal openers or closers the user did not write."
                    },
                    {
                        "role": "user",
                        "content": ai_ified
                    },
                    {
                        "role": "assistant",
                        "content": original_body
                    }
                ]
            }
            raw_examples.append(example)

    # Perform validation
    valid_examples = []
    failed_count = 0
    for ex in raw_examples:
        if validate_example(ex):
            valid_examples.append(ex)
        else:
            failed_count += 1

    print(f"Validated {len(valid_examples)} examples. {failed_count} failed validation (skipped).")

    if len(valid_examples) < 50:
        sys.stderr.write(f"Error: Fewer than 50 valid examples ({len(valid_examples)} found).\n")
        sys.exit(1)

    # Write output
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        
    with open(output_path, "w", encoding="utf-8") as out_f:
        for ex in valid_examples:
            out_f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    # Upload to Azure
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    
    if not azure_endpoint or not azure_key:
        sys.stderr.write("Error: Required Azure credentials missing from env.\n")
        sys.exit(1)
        
    openai_client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=azure_key,
        api_version="2023-05-15"
    )
    
    try:
        with open(output_path, "rb") as f:
            response = openai_client.files.create(
                file=f,
                purpose="fine-tune"
            )
        file_id = response.id
        print(f"Uploaded. File ID: {file_id}")
    except Exception as e:
        sys.stderr.write(f"Error uploading file: {e}\n")
        sys.exit(1)

    # Save metadata log
    log_data = {
        "file_id": file_id,
        "uploaded_at": datetime.utcnow().isoformat(),
        "example_count": len(valid_examples),
        "job_id": None,
        "ft_endpoint": None,
        "completed_at": None
    }
    
    with open(LOG_PATH, "w", encoding="utf-8") as log_f:
        json.dump(log_data, log_f, indent=2)

if __name__ == "__main__":
    main()
