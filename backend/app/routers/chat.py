"""Chat API router — the main conversational endpoint.

Upgraded in 2.1: domain guard, expansion detection, clause-aware search,
compliance checklists, and richer responses.
"""

from __future__ import annotations

import re
from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ChatRequest, ChatResponse, Source, CorrectionInfo,
    ProductInfo, ComparisonResult, CompareRequest, CompareResponse,
)
from app.services.rag import rag_query
from app.services.translator import detect_language, translate_to_english, translate_from_english
from app.services.matcher import recommend_standards
from app.services.certification import get_certification_guide, get_hallmarking_faq, CERTIFICATION_SCHEMES
from app.services.labs import search_labs
from app.services.fuzzy_matcher import match_query, apply_correction, get_no_match_message
from app.services.product_kb import (
    search_products, get_product_by_name, get_product_by_is_code,
    generate_comparison, CERTIFICATION_COSTS,
)
from app.services.domain_guard import (
    is_bis_domain, is_expansion_request,
    extract_is_codes, extract_clause_reference,
)

router = APIRouter(prefix="/api", tags=["chat"])


def _compute_confidence(
    query: str,
    sources: list[Source],
    product_info: ProductInfo | None,
    has_pdf_chunks: bool = False,
) -> float:
    """Compute a confidence score 0-100 based on available data."""
    score = 50.0

    # Boost for RAG sources found
    if sources:
        score += min(len(sources) * 8, 25)

    # Boost for product info match from KB
    if product_info:
        score += 15

    # Boost for IS code in query that matches a source
    query_codes = re.findall(r'IS\s*\d+', query, re.IGNORECASE)
    if query_codes and sources:
        for code in query_codes:
            for src in sources:
                if code.lower().replace(" ", "") in src.document.lower().replace(" ", ""):
                    score += 10
                    break

    # Boost for PDF-verified content
    if has_pdf_chunks:
        score += 5

    return min(score, 99.0)


def _extract_follow_ups(answer: str) -> list[str]:
    """Extract follow-up questions from the LLM answer."""
    questions = []
    for line in answer.split("\n"):
        line = line.strip()
        if "?" in line:
            clean = re.sub(r'^[\d\.\-\*]+\s*', '', line)
            clean = clean.strip("*_`").strip()
            if clean and len(clean) > 10 and clean not in questions:
                # Skip lines that are just source citations
                if "source:" not in clean.lower() and "clause" not in clean.lower():
                    questions.append(clean)
    return questions[:6]


def _build_compliance_checklist(product_info: ProductInfo) -> str:
    """Generate a compliance checklist for a product."""
    lines = [
        "### Compliance Checklist\n",
    ]

    if product_info.is_codes:
        lines.append(f"**1. Applicable Standard:** {' / '.join(product_info.is_codes)}\n")

    if product_info.certification:
        lines.append(f"**2. BIS Certification Required:** {product_info.certification} ({product_info.certification_scheme})\n")

    if product_info.key_tests:
        lines.append("**3. Mandatory Tests:**")
        for test in product_info.key_tests[:6]:
            lines.append(f"   - {test}")
        lines.append("")

    if product_info.documents_required:
        lines.append("**4. Documents Needed:**")
        for doc in product_info.documents_required[:6]:
            lines.append(f"   - {doc}")
        lines.append("")

    lines.append("**5. Testing Lab:** Find a BIS-recognized lab at [bis.gov.in](https://bis.gov.in)\n")

    if product_info.validity:
        lines.append(f"**6. License Validity:** {product_info.validity}\n")

    return "\n".join(lines)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Main chat endpoint — routes to RAG, recommendation, certification, hallmarking, or lab flows.

    2.1 upgrades:
    - Domain guard (refuse non-BIS questions)
    - Expansion detection (reuse previous context)
    - Clause-aware retrieval
    - Compliance checklists
    - Richer responses
    """

    # ── Step 0: Domain guard ──
    is_bis, refusal = is_bis_domain(req.message)
    if not is_bis:
        return ChatResponse(
            answer=refusal,
            sources=[],
            mode=req.mode,
            confidence=0.0,
            related_questions=[
                "What BIS standard applies to my product?",
                "How do I get BIS certification?",
                "Find a BIS testing lab near me",
                "Explain IS 302 in simple terms",
            ],
        )

    # ── Step 1: Language detection & translation ──
    user_lang = req.language
    if user_lang == "auto" or not user_lang:
        user_lang = detect_language(req.message)

    query_en = translate_to_english(req.message, user_lang) if user_lang != "en" else req.message

    # ── Step 2: Fuzzy match for typos / misspellings ──
    correction_info = None
    fuzzy_match = match_query(query_en)
    if fuzzy_match:
        if fuzzy_match.confidence >= 60:
            query_en = apply_correction(query_en, fuzzy_match)
            correction_info = {
                "original_word": fuzzy_match.original_word,
                "corrected_word": fuzzy_match.corrected_word,
                "confidence": fuzzy_match.confidence,
                "suggestions": fuzzy_match.suggestions,
            }

    # ── Step 2.5: Expansion detection ──
    is_expansion = is_expansion_request(query_en)

    # ── Step 2.6: Extract IS codes and clause references from query ──
    query_is_codes = extract_is_codes(query_en)
    clause_ref = extract_clause_reference(query_en)

    # If IS codes found, ensure they're in the query for RAG retrieval
    if query_is_codes and not any(code.lower() in query_en.lower() for code in query_is_codes):
        query_en = query_en + " " + " ".join(query_is_codes)

    # ── Step 2.7: Product KB lookup ──
    product_info = None
    product_results = search_products(query_en)
    if product_results:
        best_name, best_entry, best_score = product_results[0]
        product_info = ProductInfo(
            name=best_entry.name,
            is_codes=best_entry.is_codes,
            category=best_entry.category,
            certification=best_entry.certification,
            certification_scheme=best_entry.certification_scheme,
            description=best_entry.description,
            products_covered=best_entry.products_covered[:8],
            key_tests=best_entry.key_tests[:8],
            documents_required=best_entry.documents_required[:7],
            related_standards=best_entry.related_standards[:4],
            key_requirements=best_entry.key_requirements[:5] if best_entry.key_requirements else [],
            validity=best_entry.validity,
        )

    # ── Step 3: Route by mode ──
    answer = ""
    sources: list[Source] = []
    history = [h for h in req.history if h.get("content")]

    if req.mode == "recommend":
        # Product -> Standard recommendation with rich responses
        recs = recommend_standards(query_en, top_k=5)
        if recs:
            answer = _build_rich_recommendation(recs, product_info, query_en, history)
            # Also run RAG for additional context on each standard
            try:
                rag_answer, rag_sources = rag_query(query_en, top_k=5, history=history)
                if rag_sources:
                    sources.extend(rag_sources)
            except Exception:
                pass
        elif product_info:
            answer = _build_product_response(product_info, query_en)
            # Also run RAG for additional context
            try:
                rag_answer, rag_sources = rag_query(query_en, top_k=3, history=history)
                if rag_answer and len(rag_answer) > 100:
                    answer += "\n\n---\n\n" + rag_answer
                if rag_sources:
                    sources.extend(rag_sources)
            except Exception:
                pass
        else:
            # No direct match — fall back to RAG
            try:
                answer, sources = rag_query(query_en, top_k=5, history=history, is_expansion=is_expansion)
            except Exception:
                answer = (
                    "I couldn't identify specific standards for your product. "
                    "Please try describing your product in more detail, or check "
                    "[bis.gov.in](https://bis.gov.in) for the full product-wise standards list.\n\n"
                    "**Try asking:**\n"
                    "- What BIS standard applies to [your product]?\n"
                    "- Which IS code covers [product category]?\n"
                    "- BIS certification for [product name]"
                )

    elif req.mode == "certify":
        # Certification process explainer
        q_lower = query_en.lower()

        # Check for cost/timeline questions
        if any(w in q_lower for w in ["cost", "price", "fee", "estimate"]):
            scheme = "isi"
            if "crs" in q_lower:
                scheme = "crs"
            elif "hallmark" in q_lower:
                scheme = "hallmarking"

            cost_data = CERTIFICATION_COSTS.get(scheme, CERTIFICATION_COSTS["isi"])
            lines = [f"### BIS Certification Cost Estimate ({scheme.upper()})\n"]
            for key, value in cost_data.items():
                if key != "disclaimer":
                    label = key.replace("_", " ").title()
                    lines.append(f"**{label}:** {value}")
            lines.append(f"\n> _{cost_data.get('disclaimer', '')}_\n")
            answer = "\n".join(lines)

        # Check for compliance checklist request
        elif any(w in q_lower for w in ["checklist", "compliance", "what do i need"]):
            if product_info:
                answer = _build_compliance_checklist(product_info)
            else:
                answer = (
                    "To generate a compliance checklist, please specify the product.\n\n"
                    "**Example:**\n"
                    "- Compliance checklist for toy manufacturing\n"
                    "- What do I need for BIS certification of LED bulbs?\n"
                    "- Checklist for helmet certification"
                )

        else:
            scheme_key = "isi"
            if any(w in q_lower for w in ["crs", "registration", "electronics", "it goods", "led"]):
                scheme_key = "crs"
            elif "hallmark" in q_lower:
                scheme_key = "hallmarking"

            guide = get_certification_guide(scheme_key, query_en)
            if guide:
                lines = [f"## {guide.scheme}\n"]
                lines.append(f"_{guide.description}_\n")
                lines.append(f"**Estimated time:** {guide.estimated_time}\n")
                lines.append("### Steps:\n")
                for step in guide.steps:
                    lines.append(f"**Step {step.step_number}: {step.title}**\n{step.description}")
                    if step.tips:
                        lines.append(f"\n> _Tip: {step.tips}_\n")
                lines.append("\n### Documents Required:\n")
                for doc in guide.documents_required:
                    lines.append(f"- {doc}")
                answer = "\n".join(lines)
            else:
                answer = (
                    "Please specify the certification scheme:\n\n"
                    "- **ISI Mark** — for products under compulsory certification (safety, quality)\n"
                    "- **CRS** — for electronics and IT products\n"
                    "- **Hallmarking** — for gold, silver, and platinum jewelry\n\n"
                    "**Example:** How do I get BIS ISI certification for my factory?"
                )

    elif req.mode == "hallmark":
        # Hallmarking Q&A
        faqs = get_hallmarking_faq(query_en)
        if faqs:
            lines = ["### Hallmarking Information\n"]
            for faq in faqs:
                lines.append(f"**Q: {faq['question']}**\nA: {faq['answer']}\n")
            answer = "\n\n".join(lines)

            # Also try RAG for additional context
            try:
                rag_answer, rag_sources = rag_query(query_en, top_k=2, history=history, is_expansion=is_expansion)
                if rag_answer and "don't have" not in rag_answer:
                    answer += "\n\n---\n\n" + rag_answer
                    sources.extend(rag_sources)
            except Exception:
                pass
        else:
            try:
                answer, sources = rag_query(query_en, top_k=3, history=history, is_expansion=is_expansion)
            except Exception:
                answer = (
                    "For hallmarking queries, please ask about:\n\n"
                    "- HUID verification\n"
                    "- Gold/silver purity grades\n"
                    "- Hallmarking process and requirements\n"
                    "- Jeweler registration with BIS\n"
                    "- Where to get jewelry hallmarked\n\n"
                    "**Example:** How do I get BIS hallmarking for gold jewelry?"
                )

    elif req.mode == "lab":
        # Lab lookup — upgraded with structured cards
        q_lower = query_en.lower()
        category_keywords = [
            "electrical", "electronic", "food", "textile", "toys", "steel",
            "cement", "plastics", "chemicals", "metals", "leather", "petroleum",
            "power", "transformers", "cables", "IT equipment", "telecom",
            "polymer", "packaging", "sugar", "lubricants", "fuels",
            "building materials", "rubber", "footwear", "helmet",
            "battery", "wire", "cable", "LED",
        ]
        city_keywords = [
            "delhi", "mumbai", "chennai", "kolkata", "bangalore", "bengaluru",
            "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow", "guwahati",
            "kanpur", "faridabad", "jamshedpur", "chandigarh", "noida",
            "gurgaon", "gurugram", "indore", "bhopal", "nagpur", "coimbatore",
            "meerut", "rajkot", "surat", "vadodara",
        ]
        found_category = next((c for c in category_keywords if c in q_lower), "")
        found_city = next((c for c in city_keywords if c in q_lower), "")

        labs_found = search_labs(category=found_category, city=found_city)
        if labs_found:
            lines = ["### BIS-Recognized Testing Labs"]
            if found_category:
                lines[0] += f" — {found_category.title()}"
            if found_city:
                lines[0] += f" in {found_city.title()}"
            lines.append(f"\nFound **{len(labs_found)}** matching labs.\n")
            for lab in labs_found[:10]:
                lines.append(f"**{lab.name}**")
                lines.append(f"📍 {lab.address}, {lab.city}, {lab.state}")
                if lab.phone:
                    lines.append(f"📞 {lab.phone}")
                lines.append(f"🏷️ {', '.join(lab.categories)}")
                lines.append(f"✅ {lab.accreditation}\n")
            if len(labs_found) > 10:
                lines.append(f"_...and {len(labs_found) - 10} more. Try specifying a city or category to narrow results._")
            answer = "\n".join(lines)
        else:
            answer = (
                "**No labs found matching your criteria.**\n\n"
                "Try specifying:\n"
                "- A city (e.g., Mumbai, Delhi, Chennai, Bangalore)\n"
                "- A product category (e.g., electrical, food, textiles, toys)\n"
                "- A lab name\n\n"
                "**Available categories:** electrical, electronic, food, textile, toys, "
                "steel, cement, plastics, chemicals, metals, leather, petroleum, "
                "helmet, battery, wire, cable, LED.\n\n"
                "**Example:** Testing lab for helmets in Mumbai"
            )

    else:
        # Default: General RAG query — with AI memory from history
        try:
            answer, sources = rag_query(
                query_en,
                history=history,
                is_expansion=is_expansion,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"RAG pipeline error: {str(e)}")

    # ── Step 4: Compute confidence ──
    has_pdf_chunks = bool(sources)
    confidence = _compute_confidence(query_en, sources, product_info, has_pdf_chunks)

    # If no product info from KB but we have RAG sources, try to extract IS codes
    if not product_info and sources:
        for src in sources:
            code_match = re.findall(r'IS\s*\d+', src.document, re.IGNORECASE)
            if code_match:
                for code in code_match:
                    kb_products = get_product_by_is_code(code)
                    if kb_products:
                        _, entry = kb_products[0]
                        product_info = ProductInfo(
                            name=entry.name,
                            is_codes=entry.is_codes,
                            category=entry.category,
                            certification=entry.certification,
                            certification_scheme=entry.certification_scheme,
                            description=entry.description,
                            products_covered=entry.products_covered[:8],
                            key_tests=entry.key_tests[:8],
                            documents_required=entry.documents_required[:7],
                            related_standards=entry.related_standards[:4],
                            key_requirements=entry.key_requirements[:5] if entry.key_requirements else [],
                            validity=entry.validity,
                        )
                        break
            if product_info:
                break

    # ── Step 5: Extract follow-up questions ──
    follow_ups = _extract_follow_ups(answer)

    # Add product KB follow-ups if available
    if product_info and product_results:
        _, best_entry, _ = product_results[0]
        for q in best_entry.follow_up_questions[:3]:
            if q not in follow_ups:
                follow_ups.append(q)

    # Add generic follow-ups if too few
    if len(follow_ups) < 3:
        generic_follow_ups = [
            "Explain this standard in simple terms",
            "What is the certification process?",
            "What documents are needed?",
            "Find a testing lab near me",
            "What are the related standards?",
        ]
        for q in generic_follow_ups:
            if q not in follow_ups:
                follow_ups.append(q)

    follow_ups = follow_ups[:6]

    # ── Step 6: Translate answer back ──
    if user_lang != "en":
        answer = translate_from_english(answer, user_lang)

    corr = None
    if correction_info:
        corr = CorrectionInfo(**correction_info)

    return ChatResponse(
        answer=answer,
        sources=sources,
        mode=req.mode,
        correction=corr,
        confidence=confidence,
        product_info=product_info,
        related_questions=follow_ups,
        follow_ups=follow_ups,
    )


def _build_rich_recommendation(recs, product_info, query, history) -> str:
    """Build a rich, structured recommendation response following the professional template."""
    lines = [
        "## ✅ Applicable BIS Standards\n",
        f"Based on your query, these are the official BIS standards that apply.\n",
    ]

    # Product info card at top if available
    if product_info:
        lines.append(f"### **{product_info.name}**\n")
        lines.append(f"_{product_info.description}_\n")
        if product_info.products_covered:
            lines.append("**Products covered:**")
            for p in product_info.products_covered[:6]:
                lines.append(f"- {p}")
            lines.append("")

    # Each standard gets its own rich section
    for i, rec in enumerate(recs):
        lines.append(f"---\n")
        lines.append(f"### **{rec.is_number}** — {rec.title}\n")

        # What this standard covers
        lines.append("#### What this standard covers\n")
        lines.append(f"{rec.explanation}\n")

        # Who should follow this standard
        if product_info and i == 0:
            lines.append("#### Who should follow this standard?\n")
            lines.append("- Manufacturers")
            lines.append("- Importers")
            lines.append("- Testing Laboratories")
            lines.append("- Retailers")
            lines.append("- Consumers (if applicable)\n")

        # Key requirements
        if product_info and i == 0 and product_info.key_requirements:
            lines.append("#### Key Requirements\n")
            for req in product_info.key_requirements:
                lines.append(f"- {req}")
            lines.append("")

        # Key tests
        if product_info and i == 0 and product_info.key_tests:
            lines.append("#### Key Tests\n")
            for test in product_info.key_tests[:6]:
                lines.append(f"- {test}")
            lines.append("")

        # Practical example
        if product_info and i == 0:
            lines.append("#### Practical Example\n")
            name_lower = product_info.name.lower()
            lines.append(
                f"A manufacturer of {product_info.name.lower()} must ensure their product "
                f"complies with {' / '.join(product_info.is_codes)} before applying for BIS certification. "
                f"This involves testing at a BIS-recognized laboratory and meeting all safety and quality "
                f"requirements specified in the standard.\n"
            )

    # Compliance summary table
    if product_info:
        lines.append("---\n")
        lines.append("## Compliance Summary\n")
        lines.append("| Requirement | Status |")
        lines.append("| --- | --- |")
        lines.append(f"| BIS Certification Required | **{product_info.certification}** ({product_info.certification_scheme}) |")
        lines.append(f"| ISI Mark Required | {'Yes' if product_info.certification_scheme == 'ISI' else 'Depends on product category'} |")
        lines.append(f"| Testing Required | Yes — at BIS-recognized laboratory |")
        if product_info.documents_required:
            lines.append(f"| Documents Required | {len(product_info.documents_required)} documents |")
        lines.append("")

    # Related standards
    if product_info and product_info.related_standards:
        lines.append("## Related BIS Standards\n")
        for std in product_info.related_standards:
            lines.append(f"- **{std}**")
        lines.append("")

    # Source
    lines.append("## Source\n")
    lines.append("_Information sourced from indexed BIS standards and official documentation._\n")

    return "\n".join(lines)


def _build_product_response(product_info: ProductInfo, query: str) -> str:
    """Build a rich product response when no recommendation matches but KB has data."""
    lines = [
        f"## ✅ BIS Standards for {product_info.name}\n",
        f"_{product_info.description}_\n",
    ]

    if product_info.is_codes:
        lines.append("### Applicable Standards\n")
        for code in product_info.is_codes:
            lines.append(f"- **{code}**")
        lines.append("")

    if product_info.products_covered:
        lines.append("### Products Covered\n")
        for p in product_info.products_covered[:8]:
            lines.append(f"- {p}")
        lines.append("")

    if product_info.key_requirements:
        lines.append("### Key Requirements\n")
        for req in product_info.key_requirements:
            lines.append(f"- {req}")
        lines.append("")

    if product_info.key_tests:
        lines.append("### Key Tests\n")
        for test in product_info.key_tests[:6]:
            lines.append(f"- {test}")
        lines.append("")

    if product_info.certification:
        lines.append("### Certification Status\n")
        lines.append(f"**{product_info.certification}** — {product_info.certification_scheme} Scheme\n")

    if product_info.documents_required:
        lines.append("### Documents Required\n")
        for doc in product_info.documents_required[:5]:
            lines.append(f"- {doc}")
        lines.append("")

    if product_info.related_standards:
        lines.append("### Related BIS Standards\n")
        for std in product_info.related_standards:
            lines.append(f"- **{std}**")
        lines.append("")

    if product_info.follow_up_questions:
        lines.append("### Suggested Follow-up Questions\n")
        for q in product_info.follow_up_questions[:4]:
            lines.append(f"- {q}")

    return "\n".join(lines)


@router.post("/compare", response_model=CompareResponse)
async def compare_standards(req: CompareRequest):
    """Compare two IS standards side by side."""
    comparison_data = generate_comparison(req.standard_a, req.standard_b)
    return CompareResponse(
        comparison=ComparisonResult(
            standard_a=comparison_data["standard_a"],
            standard_b=comparison_data["standard_b"],
            name_a=comparison_data["name_a"],
            name_b=comparison_data["name_b"],
            purpose=comparison_data["comparison"]["purpose"],
            applies_to=comparison_data["comparison"]["applies_to"],
            certification=comparison_data["comparison"]["certification"],
            tests_count=comparison_data["comparison"]["tests"],
            products=comparison_data["comparison"]["products"],
        )
    )
