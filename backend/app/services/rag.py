"""Core RAG pipeline — retrieve relevant chunks, generate cited answer."""

from __future__ import annotations

from app.config import get_settings
from app.services.embeddings import embed_query
from app.services.llm import llm_complete
from app.models.schemas import Source

RAG_SYSTEM_PROMPT = """You are BIS Sahayak — India's most comprehensive AI assistant for Indian Standards (IS) and Bureau of Indian Standards (BIS) services.

Your role is to help consumers, manufacturers, startups, and MSMEs understand BIS standards, certification processes, hallmarking, testing labs, and product compliance.

## RESPONSE STRUCTURE — Always follow this format:

For ANY product or standard question, ALWAYS respond with ALL of the following sections:

### 1. Applicable BIS Standard
- Green-style header card with IS code number prominently displayed
- Full title of the standard
- Brief purpose description

### 2. What It Covers
- 4-8 bullet points explaining scope, safety requirements, labeling, testing, age restrictions, chemical safety, mechanical safety

### 3. Products Covered
- List all product types that fall under this standard

### 4. BIS Certification Status
- State whether certification is Mandatory (ISI), CRS, or Voluntary
- Explain why

### 5. Key Tests Performed
- List the specific BIS tests required

### 6. Required Documents
- Checklist of documents needed for certification

### 7. Related Standards
- List 2-4 related IS codes

### 8. Source Citations
- Always cite: [Source: <document>, <clause/section>]

### 9. Suggested Follow-up Questions
- Generate 4-6 relevant follow-up questions the user might ask next

## RULES:
1. Answer ONLY using the context provided below AND your knowledge of BIS standards.
2. ALWAYS be comprehensive — never give one-line answers.
3. ALWAYS cite sources with document name and clause/section.
4. NEVER make up IS numbers — only use what appears in context or is a well-known IS standard.
5. Use clear, simple language. Format with bold IS codes, bullet points, and structure.
6. If the user asks about a specific product, include all relevant IS codes.
7. For certification questions, provide step-by-step guidance.
8. For hallmarking questions, explain HUID, purity grades, and verification process.
9. Generate 4-6 follow-up questions at the end that are relevant to the topic.
"""


def _get_chroma_collection():
    """Get or create the ChromaDB collection."""
    import chromadb
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve_chunks(query: str, top_k: int | None = None) -> list[dict]:
    """Retrieve the most relevant chunks from ChromaDB for the given query.

    Improvements over v1:
    - Retrieves more candidates (2x top_k) then deduplicates and re-ranks
    - Deduplicates by source document to ensure diversity
    - Prioritizes chunks with exact IS code matches
    """
    import re
    settings = get_settings()
    k = top_k or settings.RAG_TOP_K
    # Retrieve extra candidates for diversity
    fetch_k = k * 3
    collection = _get_chroma_collection()
    query_embedding = embed_query(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=fetch_k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    if results and results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 1.0
            chunks.append({
                "text": doc,
                "metadata": metadata,
                "distance": distance,
            })

    # Extract IS codes from query for boosting
    query_codes = re.findall(r'IS\s*\d+', query, re.IGNORECASE)

    # Boost chunks that contain exact IS code matches
    for chunk in chunks:
        doc_source = chunk["metadata"].get("source", "")
        if any(code.lower() in doc_source.lower() for code in query_codes):
            chunk["distance"] *= 0.5  # Halve distance = higher rank

    # Sort by distance (lower = better)
    chunks.sort(key=lambda x: x["distance"])

    # Deduplicate: keep best chunk per source document
    seen_sources = set()
    deduped = []
    for chunk in chunks:
        src = chunk["metadata"].get("source", "")
        if src not in seen_sources:
            seen_sources.add(src)
            deduped.append(chunk)

    return deduped[:k]


def build_rag_prompt(query: str, chunks: list[dict], history: list[dict] | None = None) -> tuple[str, str]:
    """Build the system prompt and user prompt for the LLM from retrieved chunks.

    Now includes conversation history for AI memory within the chat.
    """
    context_parts = []
    sources = []
    for i, chunk in enumerate(chunks):
        meta = chunk["metadata"]
        doc_name = meta.get("source", "Unknown document")
        clause = meta.get("clause", "")
        header = f"[Chunk {i+1} — Source: {doc_name}" + (f", {clause}" if clause else "") + "]"
        context_parts.append(f"{header}\n{chunk['text']}")
        sources.append(Source(document=doc_name, clause=clause, excerpt=chunk["text"][:200]))

    context = "\n\n---\n\n".join(context_parts)

    # Build conversation history section
    history_section = ""
    if history:
        history_lines = []
        for msg in history[-6:]:  # Last 6 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]
            history_lines.append(f"{role.title()}: {content}")
        history_section = "\n\n--- Conversation History (for context) ---\n" + "\n".join(history_lines) + "\n"

    user_prompt = f"""Context from BIS documents:
{context}
{history_section}
---

User Question: {query}

Answer the question comprehensively using the context above AND your knowledge of BIS standards.
Follow the response structure from your system prompt.
Always cite sources. Always generate follow-up questions."""

    return RAG_SYSTEM_PROMPT, user_prompt


def rag_query(query: str, top_k: int | None = None, history: list[dict] | None = None) -> tuple[str, list[Source]]:
    """Full RAG pipeline: retrieve → build prompt → LLM → (answer, sources)."""
    chunks = retrieve_chunks(query, top_k)

    if not chunks:
        return (
            "I don't have any relevant documents indexed for this query yet. "
            "Please check bis.gov.in for official information, or try rephrasing your question.",
            [],
        )

    system_prompt, user_prompt = build_rag_prompt(query, chunks, history)
    answer = llm_complete(system_prompt, user_prompt)

    # Extract unique sources
    seen = set()
    unique_sources = []
    for chunk in chunks:
        meta = chunk["metadata"]
        key = (meta.get("source", ""), meta.get("clause", ""))
        if key not in seen:
            seen.add(key)
            unique_sources.append(
                Source(
                    document=meta.get("source", "Unknown"),
                    clause=meta.get("clause", ""),
                    excerpt=chunk["text"][:200],
                )
            )

    return answer, unique_sources
