"""Corpus refresh CEO wrapper.

This script drops and rebuilds the ceo_archetype collection from raw docs.
"""

import os
import sys
from dotenv import load_dotenv
from pipeline.embed_ceo import embed_ceo_docs, RAW_DOCS_DIR

def main():
    load_dotenv()
    chroma_path = os.getenv("CHROMA_PATH")
    if not chroma_path:
        sys.stderr.write("Error: CHROMA_PATH environment variable is missing.\n")
        sys.exit(1)
        
    # Drop and rebuild collection
    embed_ceo_docs(chroma_path, RAW_DOCS_DIR, drop_collection=True)

if __name__ == "__main__":
    main()
