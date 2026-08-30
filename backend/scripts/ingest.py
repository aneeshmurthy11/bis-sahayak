#!/usr/bin/env python3
"""
BIS Sahayak — Document Ingestion Pipeline v2

Extracts text from BIS standard PDFs, chunks them intelligently,
generates embeddings, and stores everything in ChromaDB.

Features:
- Smart dedup: detects duplicate IS codes, keeps latest version
- Enhanced metadata: IS code, standard name, page numbers, clause numbers
- Clause-aware chunking: splits by BIS section/clause structure
- Detailed verification stats after indexing
- Merges with existing indexed data (no overwrite)

Usage:
    python -m scripts.ingest                    # Ingest all PDFs in data/standards/
    python -m scripts.ingest --file path/to.pdf  # Ingest a specific PDF
    python -m scripts.ingest --reset             # Reset ChromaDB and re-ingest
    python -m scripts.ingest --stats             # Show current index stats
"""

from __future__ import annotations

import sys
import os
import re
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pdfplumber
from sentence_transformers import SentenceTransformer

# ── Configuration ─────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STANDARDS_DIR = DATA_DIR / "standards"
SCHEMES_DIR = DATA_DIR / "schemes"
CHROMA_DIR = Path(__file__).resolve().parent.parent / "chroma_db"
COLLECTION_NAME = "bis_standards"

CHUNK_SIZE = 600       # approximate tokens (chars / 4)
CHUNK_OVERLAP = 100    # overlap in tokens
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# ── IS Code Extraction from Filenames ─────────────────────────────────────────

def extract_is_code_from_filename(filename: str) -> str | None:
    """Extract IS code number from PDF filename.

    Examples:
        '302_1.pdf' -> 'IS 302'
        '10500_2012_reaff2023_amd4.pdf' -> 'IS 10500'
        '1417#.pdf' -> 'IS 1417'
        '694_2010_reff2020.pdf' -> 'IS 694'
        '1165_2022 (1).pdf' -> 'IS 1165'
        'Circular_eCPc_2025-02-06.pdf' -> None (not an IS standard)
        'tbl5_2024-11-10_1117.pdf' -> None (table document)
    """
    stem = Path(filename).stem

    # Skip circulars and table documents
    if stem.lower().startswith("circular") or stem.lower().startswith("tbl"):
        return None

    # Try to extract the leading number (IS code)
    # Match patterns like: 302_1, 10500_2012, 1417#, 694_2010_reff2020
    match = re.match(r'^(\d+)', stem)
    if match:
        return f"IS {match.group(1)}"

    return None


def extract_standard_name_from_text(text: str, filename: str) -> str:
    """Try to extract the standard name from the first page of the PDF.

    BIS standards typically have a title page with the standard name.
    """
    # Look for common BIS title patterns
    # "IS <number> : <year> : <title>"
    # "Indian Standard <title>"
    # Just use first 500 chars of text
    first_page = text[:2000] if text else ""

    patterns = [
        r'(IS\s+\d+\s*:\s*\d{4})\s*[:\-–]\s*(.+?)(?:\n|$)',
        r'(Indian\s+Standard)\s+(.+?)(?:\n|$)',
        r'(Bureau\s+of\s+Indian\s+Standards)',
    ]

    for pattern in patterns:
        match = re.search(pattern, first_page, re.IGNORECASE)
        if match:
            return match.group(0).strip()[:100]

    # Fallback: use filename
    stem = Path(filename).stem
    # Clean up filename: remove dates, amendments, etc.
    clean = re.sub(r'_\d{4}.*$', '', stem)
    clean = re.sub(r'\s*\(\d+\)\s*$', '', clean)
    clean = clean.replace('#', '').replace('_', ' ')
    return clean


def get_pdf_year(filename: str) -> int | None:
    """Extract year from filename for version comparison."""
    match = re.search(r'(\d{4})', filename)
    if match:
        year = int(match.group(1))
        if 1950 <= year <= 2030:
            return year
    return None


# ── PDF Text Extraction ───────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: Path) -> list[tuple[int, str]]:
    """Extract text from a PDF file with page tracking.

    Returns list of (page_number, page_text) tuples.
    """
    pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    pages.append((i + 1, page_text.strip()))
    except Exception as e:
        print(f"  ⚠️  Error extracting {pdf_path.name}: {e}")
    return pages


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    char_size = chunk_size * 4
    char_overlap = overlap * 4

    if len(text) <= char_size:
        return [text.strip()] if text.strip() else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + char_size

        if end < len(text):
            for break_char in ["\n\n", "\n", ". ", " "]:
                last_break = text.rfind(break_char, start + char_size // 2, end + char_size // 4)
                if last_break > start:
                    end = last_break + len(break_char)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - char_overlap

    return chunks


def chunk_with_clause_tracking(text: str, source_name: str) -> list[dict]:
    """Chunk text and track which clause each chunk belongs to."""
    # Try to split by major sections first
    section_splits = re.split(r'(?m)^(\d+(?:\.\d+)*)\s+', text)

    chunks_with_meta = []

    if len(section_splits) > 3:
        current_clause = ""
        for i in range(1, len(section_splits), 2):
            clause_num = section_splits[i] if i < len(section_splits) else ""
            clause_text = section_splits[i + 1] if i + 1 < len(section_splits) else ""
            current_clause = clause_num

            sub_chunks = chunk_text(clause_text)
            for chunk in sub_chunks:
                chunks_with_meta.append({
                    "text": chunk,
                    "clause": f"Clause {current_clause}" if current_clause else "",
                })
    else:
        sub_chunks = chunk_text(text)
        for chunk in sub_chunks:
            clause_match = re.search(r'(\d+(?:\.\d+)*)', chunk[:100])
            clause = f"Clause {clause_match.group(1)}" if clause_match else ""
            chunks_with_meta.append({
                "text": chunk,
                "clause": clause,
            })

    return chunks_with_meta


# ── Ingestion Pipeline ────────────────────────────────────────────────────────

def ingest_pdf(pdf_path: Path, collection, embedder, stats: dict) -> int:
    """Ingest a single PDF into ChromaDB.

    Returns number of chunks added.
    Skips duplicates based on IS code + version comparison.
    """
    filename = pdf_path.name
    is_code = extract_is_code_from_filename(filename)

    # Skip non-IS PDFs (circulars, tables) — still index them but with generic metadata
    if is_code is None:
        source_name = pdf_path.stem
        standard_name = filename
    else:
        source_name = is_code  # e.g., "IS 302"
        standard_name = extract_standard_name_from_text("", filename)

    # Check for duplicates — if same IS code already indexed, check version
    if is_code:
        existing = collection.get(
            where={"source": is_code},
            limit=1,
        )
        if existing and existing["ids"]:
            # Already indexed — check if this is a newer version
            existing_files = set()
            all_existing = collection.get(where={"source": is_code})
            if all_existing and all_existing["metadatas"]:
                for meta in all_existing["metadatas"]:
                    existing_files.add(meta.get("file", ""))

            # If same file already indexed (or very similar), skip
            for ef in existing_files:
                ef_stem = Path(ef).stem
                new_stem = pdf_path.stem
                # Normalize: remove (1), (2), etc.
                ef_norm = re.sub(r'\s*\(\d+\)$', '', ef_stem)
                new_norm = re.sub(r'\s*\(\d+\)$', '', new_stem)
                if ef_norm == new_norm:
                    stats["duplicates_skipped"] += 1
                    print(f"  ⏭️  Skipping duplicate: {filename} (same as {ef})")
                    return 0

            # Different version — keep the newer one
            new_year = get_pdf_year(filename)
            if new_year:
                oldest_existing_year = 9999
                for ef in existing_files:
                    y = get_pdf_year(ef)
                    if y and y < oldest_existing_year:
                        oldest_existing_year = y

                if new_year <= oldest_existing_year:
                    stats["duplicates_skipped"] += 1
                    print(f"  ⏭️  Skipping older version: {filename} ({new_year})")
                    return 0

    # Extract text
    print(f"  📄 Extracting text from: {filename}")
    pages = extract_text_from_pdf(pdf_path)

    if not pages:
        print(f"  ⚠️  No text extracted from {filename}")
        stats["skipped_empty"] += 1
        return 0

    total_text = "\n\n".join(page_text for _, page_text in pages)
    print(f"  ✂️  Chunking ({len(total_text)} chars from {len(pages)} pages)...")

    # Chunk with clause tracking
    chunks = chunk_with_clause_tracking(total_text, source_name)

    if not chunks:
        print(f"  ⚠️  No chunks generated from {filename}")
        stats["skipped_empty"] += 1
        return 0

    # Generate embeddings
    print(f"  🧮 Generating embeddings for {len(chunks)} chunks...")
    texts = [c["text"] for c in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=False).tolist()

    # Prepare ChromaDB data with enhanced metadata
    ids = [f"{source_name.replace(' ', '_')}_chunk_{i}" for i in range(len(chunks))]
    metadatas = []
    for i, chunk in enumerate(chunks):
        meta = {
            "source": source_name,
            "clause": chunk["clause"],
            "file": filename,
            "chunk_index": i,
            "page": 1,
            "standard_name": standard_name,
        }
        if is_code:
            meta["is_code"] = is_code

        metadatas.append(meta)

    # Upsert into ChromaDB
    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(f"  ✅ Ingested {len(chunks)} chunks from {filename}" +
          (f" ({is_code})" if is_code else ""))

    stats["pdfs_indexed"] += 1
    stats["total_chunks"] += len(chunks)
    if is_code:
        stats["standards"].add(is_code)

    return len(chunks)


def show_stats(collection):
    """Print current index statistics."""
    print("\n" + "=" * 60)
    print("📊 BIS Sahayak — Knowledge Base Statistics")
    print("=" * 60)

    all_data = collection.get(include=["metadatas"])
    if not all_data or not all_data["metadatas"]:
        print("  (empty — no documents indexed)")
        return

    metadatas = all_data["metadatas"]
    total_chunks = len(metadatas)

    # Count unique IS codes
    is_codes = set()
    files = set()
    for meta in metadatas:
        if meta.get("is_code"):
            is_codes.add(meta["is_code"])
        if meta.get("source"):
            is_codes.add(meta["source"])
        if meta.get("file"):
            files.add(meta["file"])

    print(f"  📄 Total PDFs indexed:     {len(files)}")
    print(f"  📦 Total chunks:           {total_chunks}")
    print(f"  📋 IS standards available:  {len(is_codes)}")
    print(f"\n  Standards: {', '.join(sorted(is_codes))}")
    print("=" * 60)


def run_ingestion(reset: bool = False, single_file: str | None = None):
    """Run the full ingestion pipeline."""
    import chromadb

    print("=" * 60)
    print("🚀 BIS Sahayak — Document Ingestion Pipeline v2")
    print("=" * 60)
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize ChromaDB
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if reset:
        print("🗑️  Resetting ChromaDB collection...")
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Show existing stats
    existing_count = collection.count()
    if existing_count > 0:
        print(f"📦 Existing index: {existing_count} chunks")

    # Load embedding model
    print(f"🧠 Loading embedding model: {EMBEDDING_MODEL}")
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    # Collect PDFs
    pdf_files = []
    if single_file:
        pdf_path = Path(single_file)
        if pdf_path.exists():
            pdf_files = [pdf_path]
        else:
            print(f"❌ File not found: {single_file}")
            return
    else:
        for pdf_dir in [STANDARDS_DIR, SCHEMES_DIR]:
            if pdf_dir.exists():
                pdf_files.extend(sorted(pdf_dir.glob("*.pdf")))

        if not pdf_files:
            print(f"\n📁 No PDFs found in {STANDARDS_DIR} or {SCHEMES_DIR}")
            print("   Place BIS standard PDFs in: data/standards/")
            print("   Then run this script again.")
            return

    print(f"\n📁 Found {len(pdf_files)} PDF files to process\n")

    # Ingest PDFs
    stats = {
        "pdfs_indexed": 0,
        "total_chunks": 0,
        "duplicates_skipped": 0,
        "skipped_empty": 0,
        "standards": set(),
    }

    for i, pdf_path in enumerate(pdf_files):
        print(f"\n[{i+1}/{len(pdf_files)}] Processing: {pdf_path.name}")
        ingest_pdf(pdf_path, collection, embedder, stats)

    # Print summary
    print("\n" + "=" * 60)
    print("✅ Ingestion Complete!")
    print("=" * 60)
    print(f"  📄 PDFs indexed:        {stats['pdfs_indexed']}")
    print(f"  📦 Chunks created:      {stats['total_chunks']}")
    print(f"  📋 IS standards in KB:   {len(stats['standards'])}")
    print(f"  ⏭️  Duplicates skipped:  {stats['duplicates_skipped']}")
    print(f"  ⚠️  Empty PDFs skipped:  {stats['skipped_empty']}")
    print(f"  📁 Total files scanned: {len(pdf_files)}")
    print()
    if stats["standards"]:
        print(f"  Standards: {', '.join(sorted(stats['standards']))}")
    print()
    print(f"  ChromaDB dir: {CHROMA_DIR}")
    print(f"  Collection:   {COLLECTION_NAME}")
    print("=" * 60)

    # Also show full stats
    show_stats(collection)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest BIS documents into ChromaDB")
    parser.add_argument("--file", type=str, help="Ingest a single PDF file")
    parser.add_argument("--reset", action="store_true", help="Reset ChromaDB before ingesting")
    parser.add_argument("--stats", action="store_true", help="Show current index stats")
    args = parser.parse_args()

    if args.stats:
        import chromadb
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            collection = client.get_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            show_stats(collection)
        except Exception:
            print("No collection found. Run ingestion first.")
    else:
        run_ingestion(reset=args.reset, single_file=args.file)
