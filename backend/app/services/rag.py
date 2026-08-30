"""Core RAG pipeline — retrieve relevant chunks, generate cited answer.

Upgraded in 2.1: expert-level responses (250-600 words), conversation memory,
clause-aware retrieval, IS code boosting, and domain-aware prompting.
"""

from __future__ import annotations

from app.config import get_settings
from app.services.embeddings import embed_query
from app.services.llm import llm_complete
from app.models.schemas import Source

RAG_SYSTEM_PROMPT = """You are BIS Sahayak — India's most comprehensive AI assistant for Indian Standards (IS) and Bureau of Indian Standards (BIS) services. You are NOT a general chatbot. You are a specialized BIS standards expert.

## YOUR EXPERTISE

- All Indian Standards (IS codes) published by BIS
- BIS certification schemes: ISI Mark, Compulsory Registration Scheme (CRS), FMCS, ECO Mark
- Hallmarking: gold, silver, platinum purity, HUID system, jeweler responsibilities
- Product compliance and safety requirements across all industries
- BIS-approved testing laboratories across India
- Quality Control Orders (QCOs) issued by the government
- Packaging, labelling, and marking requirements

## RESPONSE TEMPLATE — USE THIS EXACT FORMAT

Every BIS answer MUST follow this structure. Do NOT deviate.

---

### ✅ Verified from Official BIS Standard

(Display this green badge when information comes directly from indexed BIS PDFs)

# IS XXXX — Standard Name

(Replace IS XXXX with the actual IS code. Replace Standard Name with the full title.)

## What this standard covers

Write a simple 2–4 sentence explanation in plain English describing the purpose and scope of the standard.

## Why this standard is important

Explain why BIS created this standard and what safety, quality, or compliance problem it solves.

## Who should follow this standard?

Use bullet points:
- Manufacturers
- Importers
- Testing Laboratories
- Retailers
- Consumers (if applicable)

## Key Requirements

Provide 5–8 important requirements in bullet points. Examples:
- Safety tests
- Mechanical tests
- Electrical tests
- Chemical limits
- Labelling rules
- Packaging requirements
- Marking requirements

## Practical Example

Give one real-world example showing how the standard applies to a product.

Example: A plastic toy car for children below 3 years must comply with IS 9873 before receiving BIS certification.

## Certification & Compliance

State clearly:
- Is BIS certification mandatory?
- Is ISI mark required?
- Does it fall under CRS/FMCS/QCO (if applicable)?

## Related BIS Standards

List related IS standards and explain each in one line.

Example:
- **IS 15644** — Electronic toys safety.
- **IS 9873 Part 2** — Flammability.
- **IS 9873 Part 3** — Migration of chemicals.

## Source

Mention page number, clause number, or section title from the PDF whenever available.

Example: Source: IS 9873 Part 1 — Clause 4.3, Page 18.

---

## FORMATTING RULES

1. **Always use the template above** for standard/product/certification questions.
2. Use Markdown headings and bullet points. Never return plain paragraphs.
3. Highlight IS codes in bold (e.g., **IS 302**, **IS 1417**).
4. Keep answers between 200–350 words. Be concise but complete. Only go longer if the user explicitly asks for detail.
5. Never answer with only one paragraph if information exists in the knowledge base.
6. Always cite the source document, clause number, and page number when available.
7. Never fabricate IS numbers — only use what appears in context or is a well-known BIS standard.

## FOLLOW-UP BEHAVIOUR

If the user says:
- explain more
- explain better
- give example
- summarize
- simple words
- difference between these
- continue
- who needs this
- cost
- documents required

Then EXPAND the previous answer instead of searching from scratch. Use conversation history to understand what was discussed and add more detail, examples, or clarification on the SAME topic.

## CONVERSATION MEMORY

You receive conversation history. Use it:
- If the user asks "explain better", expand on the PREVIOUS topic.
- If they say "give me an example", provide a practical example of the same topic.
- If they say "who needs this?", explain which manufacturers/industries must follow the standard.
- Maintain context for at least the last 6-10 messages.
- Always check if the current message is a follow-up to the previous topic.

## CLAUSE-AWARE RESPONSES

If the user asks about a specific clause (e.g., "What does Clause 6.2.1 say?"):
- Find the relevant clause in the provided context
- Explain it in simple, plain English
- Give a practical interpretation
- Don't dump raw text — explain what it MEANS

## CERTIFICATION QUESTIONS

When answering certification questions:
- Provide step-by-step guidance with estimated timelines
- Include required documents
- Mention applicable fees (approximate)
- Specify which scheme applies (ISI, CRS, FMCS, Hallmarking)

## HALLMARKING QUESTIONS

When answering hallmarking questions:
- Explain HUID (Hallmark Unique Identification)
- List purity grades (22K, 18K, 24K for gold; 925 for silver)
- Explain verification process
- Mention jeweler registration requirements

## QUALITY BENCHMARK

Think of yourself as a BIS standards consultant who charges ₹5000/hour.
Every answer should feel like premium consulting advice.
The goal is for BIS Sahayak to feel like ChatGPT trained specifically on BIS standards — not a PDF search engine.
Be thorough, be accurate, be helpful. Never be vague or dismissive.
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
    """Retrieve the most relevant chunks from ChromaDB.

    Improvements in 2.1:
    - Retrieves 3x top_k candidates then deduplicates and re-ranks
    - IS code boosting: chunks matching exact IS codes get priority
    - Source deduplication ensures diversity across documents
    - Clause-aware: if query mentions a clause, boost chunks with that clause
    """
    import re
    settings = get_settings()
    k = top_k or settings.RAG_TOP_K
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

    # Extract clause references for boosting
    clause_ref = re.search(r'(?:clause|section)\s+([\d\.]+)', query, re.IGNORECASE)

    # Boost and rank chunks
    for chunk in chunks:
        doc_source = chunk["metadata"].get("source", "")
        chunk_text = chunk["text"].lower()

        # Boost for exact IS code match in document name
        if any(code.lower().replace(" ", "") in doc_source.lower().replace(" ", "")
               for code in query_codes):
            chunk["distance"] *= 0.4  # Strong boost for IS code match

        # Boost for IS code mentioned in chunk text
        if any(code.lower().replace(" ", "") in chunk_text.replace(" ", "")
               for code in query_codes):
            chunk["distance"] *= 0.7

        # Boost for clause reference match
        if clause_ref:
            clause_num = clause_ref.group(1)
            if clause_num in chunk_text:
                chunk["distance"] *= 0.5

        # Boost for keywords that match the query domain
        query_lower = query.lower()
        domain_keywords = ["safety", "requirement", "certification", "test",
                           "specification", "limit", "standard", "mark"]
        for kw in domain_keywords:
            if kw in query_lower and kw in chunk_text:
                chunk["distance"] *= 0.95

    # Sort by distance (lower = better)
    chunks.sort(key=lambda x: x["distance"])

    # Deduplicate: keep best chunk per source document, max 2 per source
    seen_sources: dict[str, int] = {}
    deduped = []
    for chunk in chunks:
        src = chunk["metadata"].get("source", "")
        count = seen_sources.get(src, 0)
        if count < 2:  # Allow max 2 chunks per source
            seen_sources[src] = count + 1
            deduped.append(chunk)

    return deduped[:k]


def build_rag_prompt(
    query: str,
    chunks: list[dict],
    history: list[dict] | None = None,
    is_expansion: bool = False,
) -> tuple[str, str]:
    """Build the system prompt and user prompt for the LLM.

    Now includes:
    - Conversation history for AI memory
    - Expansion context detection
    - More detailed context formatting
    """
    context_parts = []
    sources = []
    for i, chunk in enumerate(chunks):
        meta = chunk["metadata"]
        doc_name = meta.get("source", "Unknown document")
        clause = meta.get("clause", "")
        header = f"[Chunk {i+1} — Source: {doc_name}" + (f", {clause}" if clause else "") + "]"
        context_parts.append(f"{header}\n{chunk['text']}")
        sources.append(Source(document=doc_name, clause=clause, excerpt=chunk["text"][:300]))

    context = "\n\n---\n\n".join(context_parts)

    # Build conversation history section (expanded to 10 messages)
    history_section = ""
    if history:
        history_lines = []
        for msg in history[-10:]:  # Last 10 messages for better context
            role = msg.get("role", "user")
            content = msg.get("content", "")[:300]  # More context per message
            history_lines.append(f"{role.title()}: {content}")
        history_section = "\n\n--- Conversation History (use this to understand context) ---\n" + "\n".join(history_lines) + "\n"

    # Build expansion instruction
    expansion_instruction = ""
    if is_expansion:
        expansion_instruction = (
            "\n\nIMPORTANT: The user is asking to EXPAND or CLARIFY the previous answer. "
            "Do NOT start a new topic search. Use the conversation history to understand "
            "what was discussed and provide MORE DETAIL, EXAMPLES, or CLARIFICATION on "
            "the SAME topic. Expand with practical examples, related standards, and deeper "
            "technical explanation."
        )

    user_prompt = f"""Context from BIS documents:
{context}
{history_section}
{expansion_instruction}
---

User Question: {query}

Answer the question comprehensively using the context above AND your knowledge of BIS standards.
Follow the EXACT response structure from your system prompt (10 sections).
Target 200-350 words. Be concise but complete. Only go longer if the user explicitly asks for detail.
Always cite sources. Always generate follow-up questions.
Bold all IS codes in your response."""

    return RAG_SYSTEM_PROMPT, user_prompt


# Simple in-memory query cache (LRU, max 200 entries)
_query_cache: dict[str, tuple[str, list[Source]]] = {}
_CACHE_MAX = 200


def _keyword_fallback_search(query: str) -> list[dict]:
    """Broader semantic fallback when primary search returns no results.
    Uses lower similarity threshold to catch more results."""
    import re
    collection = _get_chroma_collection()
    query_embedding = embed_query(query)

    # Try with a much larger fetch and lower threshold
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=10,
            include=["documents", "metadatas", "distances"],
        )
        if not results or not results["documents"] or not results["documents"][0]:
            return []

        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            distance = results["distances"][0][i] if results["distances"] else 1.0
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            # Accept anything with distance < 0.8 (very lenient)
            if distance < 0.8:
                chunks.append({
                    "text": doc,
                    "metadata": metadata,
                    "distance": distance,
                })

        return chunks[:5]
    except Exception:
        return []


def rag_query(
    query: str,
    top_k: int | None = None,
    history: list[dict] | None = None,
    is_expansion: bool = False,
) -> tuple[str, list[Source]]:
    """Full RAG pipeline: retrieve -> build prompt -> LLM -> (answer, sources).

    Features:
    - Query caching for repeated questions
    - Keyword fallback when semantic search fails
    - Graceful degradation with helpful suggestions
    """
    # Check cache (skip for expansion queries)
    cache_key = query.strip().lower()
    if not is_expansion and cache_key in _query_cache:
        return _query_cache[cache_key]

    chunks = retrieve_chunks(query, top_k)

    # If no semantic results, try keyword fallback
    if not chunks:
        chunks = _keyword_fallback_search(query)

    if not chunks:
        # Helpful empty state — never sound broken
        fallback_answer = (
            "I couldn't find a specific match in the indexed BIS standards for this query.\n\n"
            "**Try searching by:**\n"
            "- Product name (e.g., toys, cement, helmet, LED bulb)\n"
            "- IS code (e.g., IS 302, IS 1417, IS 9873)\n"
            "- Certification topic (e.g., ISI mark, CRS registration)\n"
            "- Hallmarking (e.g., gold hallmark, HUID)\n"
            "- Testing lab (e.g., lab in Mumbai, electrical testing)\n\n"
            "For official information, visit [bis.gov.in](https://bis.gov.in)."
        )
        return fallback_answer, []

    system_prompt, user_prompt = build_rag_prompt(query, chunks, history, is_expansion)
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
                    excerpt=chunk["text"][:300],
                )
            )

    result = (answer, unique_sources)

    # Cache the result (skip if too many entries)
    if len(_query_cache) < _CACHE_MAX:
        _query_cache[cache_key] = result

    return result
