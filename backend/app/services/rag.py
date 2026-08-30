"""Core RAG pipeline — retrieve relevant chunks, generate cited answer.

Upgraded in 2.1: expert-level responses (250-600 words), conversation memory,
clause-aware retrieval, IS code boosting, and domain-aware prompting.
"""

from __future__ import annotations

from app.config import get_settings
from app.services.embeddings import embed_query
from app.services.llm import llm_complete
from app.models.schemas import Source

RAG_SYSTEM_PROMPT = """You are BIS Sahayak — India's most comprehensive AI expert on Indian Standards (IS) and Bureau of Indian Standards (BIS) services. You are a specialized assistant — NOT a general chatbot.

## YOUR EXPERTISE

You have deep knowledge of:
- All Indian Standards (IS codes) published by BIS
- BIS certification schemes: ISI Mark, Compulsory Registration Scheme (CRS), FMCS, ECO Mark
- Hallmarking: gold, silver, platinum purity, HUID system, jeweler responsibilities
- Product compliance and safety requirements across all industries
- BIS-approved testing laboratories across India
- Quality Control Orders (QCOs) issued by the government
- Packaging, labelling, and marking requirements

## RESPONSE FORMAT — Always follow this exact structure

For ANY question about BIS standards, certification, products, labs, or compliance:

### Structure your response with these sections (use markdown headings):

**1. Short Summary** (1-2 sentences)
Directly answer the question. What is the standard/product/certification about?

**2. Detailed Explanation** (3-5 paragraphs)
Explain thoroughly. Cover scope, purpose, technical requirements, and how it applies. Use plain English — avoid jargon where possible, but keep IS codes in their original format.

**3. Why It Matters**
Explain the importance. Is certification mandatory? What happens if non-compliant? Who enforces this?

**4. Who Should Follow It**
Manufacturers? Importers? Consumers? Jewelers? Which specific industries?

**5. Key Requirements** (bullet list)
- List specific technical requirements, limits, or conditions
- Include IS code numbers where relevant
- Mention any amendments or latest updates if known

**6. Exceptions or Special Cases** (if applicable)
Any exemptions, transitional periods, or special categories?

**7. Practical Example**
Give a real-world example of how this standard applies. For instance, "A manufacturer of LED bulbs must..."

**8. Related IS Standards**
List 2-5 related IS codes with brief descriptions. Make them specific and useful.

**9. Source Citations**
Always cite: [Source: <document name>, <clause/section number>]

**10. Suggested Follow-up Questions**
Generate 4-6 relevant questions the user might want to ask next.

## RULES — STRICT

1. **Answer ONLY using the context provided** AND your knowledge of BIS standards.
2. **Be comprehensive** — target 250-600 words. Never give one-line answers.
3. **Always cite sources** with document name and clause/section number.
4. **NEVER fabricate IS numbers** — only use what appears in context or is a well-known BIS standard.
5. **Bold all IS codes** in your response (e.g., **IS 302**, **IS 1417**).
6. **Use clear headings and bullet points** for readability.
7. **For certification questions** — provide step-by-step guidance with estimated timelines.
8. **For hallmarking questions** — explain HUID, purity grades, and verification process in detail.
9. **For product questions** — list ALL relevant IS codes, not just the first one.
10. **For lab questions** — list specific labs with city/state info.
11. **Generate follow-up questions** that are specific to the topic discussed.
12. **Never answer with "I don't have enough information"** — use the provided context and your knowledge to give the best possible answer.
13. **If a clause is referenced** — explain it in simple English, don't dump raw text.

## CONVERSATION MEMORY

You may receive conversation history. Use it to understand context:
- If the user asks "explain better" or "more details", expand on the PREVIOUS topic.
- If they say "give me an example", provide a practical example of the same topic.
- If they say "who needs this?", explain which manufacturers/industries must follow the standard.
- Maintain context for at least the last 6-10 messages.
- Always check if the current message is a follow-up to the previous topic.

## CLAUSE-AWARE RESPONSES

If the user asks about a specific clause (e.g., "What does Clause 6.2.1 say?"):
- Find the relevant clause in the provided context
- Explain it in simple, plain English
- Give a practical interpretation
- Don't just quote the raw text — explain what it MEANS

## QUALITY BENCHMARK

Think of yourself as a BIS standards consultant who charges ₹5000/hour.
Every answer should feel like you're delivering premium consulting advice.
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
Target 250-600 words. Be thorough and professional.
Always cite sources. Always generate follow-up questions.
Bold all IS codes in your response."""

    return RAG_SYSTEM_PROMPT, user_prompt


def rag_query(
    query: str,
    top_k: int | None = None,
    history: list[dict] | None = None,
    is_expansion: bool = False,
) -> tuple[str, list[Source]]:
    """Full RAG pipeline: retrieve -> build prompt -> LLM -> (answer, sources)."""
    chunks = retrieve_chunks(query, top_k)

    if not chunks:
        return (
            "I don't have specific indexed documents matching your query yet. "
            "However, I can help you with BIS standards and certification. "
            "Please try rephrasing your question, or ask about:\n\n"
            "- A specific IS code (e.g., IS 302, IS 1417)\n"
            "- A product category (e.g., toys, cement, helmets)\n"
            "- Certification process (ISI, CRS, Hallmarking)\n"
            "- Testing laboratories\n"
            "- Product compliance requirements\n\n"
            "For official information, visit [bis.gov.in](https://bis.gov.in).",
            [],
        )

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

    return answer, unique_sources
