"""Scrape CEO Archetype documents.

This script fetches articles from web URLs or parses local PDF/TXT files
listed in pipeline/data/ceo_url_list.txt and extracts clean text content.
"""

import os
import sys
import re
import argparse
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text as extract_pdf_text

INPUT_PATH = "pipeline/data/ceo_url_list.txt"
OUTPUT_DIR = "pipeline/data/raw_ceo_docs"

def get_url_slug(url):
    """Generates a sanitized filename slug from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
            
        path = parsed.path.strip("/")
        first_segment = ""
        if path:
            first_segment = path.split("/")[0]
            
        if first_segment:
            slug = f"{domain}_{first_segment}"
        else:
            slug = domain
            
        # Replace non-alphanumeric chars with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '_', slug)
        return sanitized
    except Exception:
        # Fallback sanitize
        return re.sub(r'[^a-zA-Z0-9_\-]', '_', url)

def extract_web_content(html_text):
    """
    Parses HTML, finds the main content region, removes junk tags/elements,
    and returns stripped plain text.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    
    # Try finding main content in order
    main_content = soup.find("article")
    if not main_content:
        main_content = soup.find("main")
    if not main_content:
        divs = soup.find_all("div")
        if divs:
            main_content = max(divs, key=lambda d: len(d.get_text(strip=True)))
        else:
            main_content = soup
            
    if not main_content:
        return ""
        
    # Decompose unwanted elements in-place
    for el in main_content.find_all(["nav", "footer", "header", "aside", "script", "style"]):
        el.decompose()
        
    for el in main_content.select(".comment, #comments"):
        el.decompose()
        
    return main_content.get_text(separator=" ", strip=True)

def process_file_path(local_path):
    """Reads text from a local PDF or TXT file."""
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Local file '{local_path}' does not exist.")
        
    if local_path.lower().endswith(".pdf"):
        return extract_pdf_text(local_path)
    elif local_path.lower().endswith(".txt"):
        with open(local_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError("Unsupported local file type (must be .pdf or .txt).")

def main(argv=None):
    parser = argparse.ArgumentParser(description="Scrape and extract CEO Archetype texts.")
    parser.add_argument("--force", action="store_true", help="Force download/processing of all URLs/files.")
    parser.add_argument("--input", default=INPUT_PATH, help="Path to URL/file list.")
    args = parser.parse_args(argv)
    
    if not os.path.exists(args.input):
        sys.stderr.write(f"Error: Input file '{args.input}' not found.\n")
        sys.exit(1)
        
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    saved_count = 0
    skipped_count = 0
    
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
                
            if line.startswith("file://"):
                # Local file path
                local_path = line[7:]
                filename = os.path.splitext(os.path.basename(local_path))[0]
                output_path = os.path.join(OUTPUT_DIR, f"{filename}.txt")
                
                # Idempotency check
                if os.path.exists(output_path) and not args.force:
                    print(f"✓ {filename} (skipped - exists)")
                    skipped_count += 1
                    continue
                    
                try:
                    text = process_file_path(local_path)
                    word_count = len(text.strip().split())
                    
                    with open(output_path, "w", encoding="utf-8") as out_f:
                        out_f.write(text)
                        
                    print(f"✓ {filename} ({word_count} words)")
                    saved_count += 1
                except Exception as e:
                    sys.stderr.write(f"✗ {line} ({e})\n")
                    skipped_count += 1
            else:
                # Web URL
                slug = get_url_slug(line)
                output_path = os.path.join(OUTPUT_DIR, f"{slug}.txt")
                
                # Idempotency check
                if os.path.exists(output_path) and not args.force:
                    print(f"✓ {slug} (skipped - exists)")
                    skipped_count += 1
                    continue
                    
                try:
                    response = requests.get(
                        line,
                        timeout=10,
                        headers={"User-Agent": "Mozilla/5.0"}
                    )
                    
                    if response.status_code != 200:
                        sys.stderr.write(f"✗ {line} (HTTP status {response.status_code})\n")
                        skipped_count += 1
                        continue
                        
                    text = extract_web_content(response.text)
                    word_count = len(text.strip().split())
                    
                    if word_count < 200:
                        sys.stderr.write(f"✗ {line} (Word count {word_count} < 200)\n")
                        skipped_count += 1
                        continue
                        
                    with open(output_path, "w", encoding="utf-8") as out_f:
                        out_f.write(text)
                        
                    print(f"✓ {slug} ({word_count} words)")
                    saved_count += 1
                except requests.RequestException as e:
                    sys.stderr.write(f"✗ {line} (Request failed: {e})\n")
                    skipped_count += 1
                except Exception as e:
                    sys.stderr.write(f"✗ {line} (Error: {e})\n")
                    skipped_count += 1
                    
    print(f"Done. {saved_count} docs saved, {skipped_count} skipped.")

if __name__ == "__main__":
    main()
