import os
import sys
import json
import shutil
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

DATA_DIR = Path("data")
CACHE_DIR = Path(".rag_cache")

def convert_txt_to_jsonl(txt_path: Path):
    print(f"📄 Processing TXT: {txt_path.name}")
    content = txt_path.read_text(encoding='utf-8')
    
    # Simple chunking by paragraphs
    chunks = [c.strip() for c in content.split('\n\n') if c.strip()]
    
    output_path = DATA_DIR / f"{txt_path.stem}.jsonl"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, chunk in enumerate(chunks):
            if len(chunk) < 50: continue # Skip tiny chunks
            
            entry = {
                "title": f"Section {i+1}",
                "content": chunk,
                "source": txt_path.name
            }
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
    print(f"   ✅ Converted to {output_path.name} ({len(chunks)} sections)")

def convert_pdf_to_jsonl(pdf_path: Path):
    if not pdfplumber:
        print(f"⚠️  Skipping {pdf_path.name}: pdfplumber not installed. Run `pip install pdfplumber`.")
        return

    print(f"📕 Processing PDF: {pdf_path.name}")
    output_path = DATA_DIR / f"{pdf_path.stem}.jsonl"
    
    entries = []
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"   Scanned {total_pages} pages...")
        
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text: continue
            
            # Simple chunking: 1 page = 1 chunk (can be improved)
            entries.append({
                "title": f"Page {i+1}",
                "content": text.strip(),
                "source": pdf_path.name,
                "page": i+1
            })
            
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
    print(f"   ✅ Converted to {output_path.name} ({len(entries)} pages)")

def main():
    print("📚 Book Ingestion Script")
    print("========================")
    
    # Check for new files in data/
    # We look for .txt and .pdf that don't have a corresponding .jsonl
    
    files_processed = 0
    
    for file_path in DATA_DIR.glob("*"):
        if file_path.suffix.lower() == '.txt':
            jsonl_path = DATA_DIR / f"{file_path.stem}.jsonl"
            if not jsonl_path.exists():
                convert_txt_to_jsonl(file_path)
                files_processed += 1
                
        elif file_path.suffix.lower() == '.pdf':
            jsonl_path = DATA_DIR / f"{file_path.stem}.jsonl"
            if not jsonl_path.exists():
                convert_pdf_to_jsonl(file_path)
                files_processed += 1
    
    # Count total JSONL files
    total_jsonl = len(list(DATA_DIR.glob("*.jsonl")))
    print(f"\n📊 Total Library Size: {total_jsonl} books (JSONL)")

    if files_processed > 0:
        print(f"✨ Processed {files_processed} new raw files.")
        do_reset = True
    else:
        print("✅ No new raw files (PDF/TXT) to convert.")
        # If user ran this script but no conversion needed, they likely want to re-index the JSONL files they dropped
        print("   But you might have added new .jsonl files directly.")
        do_reset = True # Always reset if run, assuming ingestion intent
    
    if do_reset:
        if CACHE_DIR.exists():
            print("🧹 Clearing RAG cache to force re-indexing of all books...")
            shutil.rmtree(CACHE_DIR)
            print("✅ Cache cleared.")
        print("🚀 Ready! Run the debate system now to index all books.")

if __name__ == "__main__":
    # Ensure we are in backend dir
    if not os.path.exists('data'):
        if os.path.exists('backend/data'):
            os.chdir('backend')
        else:
            print("❌ Error: Run this from project root or backend directory")
            sys.exit(1)
            
    main()
