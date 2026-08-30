"""Chat API router — the main conversational endpoint."""

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

router = APIRouter(prefix="/api", tags=["chat"])


def _compute_confidence(query: str, sources: list[Source], product_info: ProductInfo | None) -> float:
    """Compute a confidence score 0-100 based on available data."""
    score = 50.0  # base

    # Boost for sources found
    if sources:
        score += min(len(sources) * 8, 25)

    # Boost for product info match
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

    return min(score, 99.0)


def _extract_follow_ups(answer: str) -> list[str]:
    """Extract follow-up questions from the LLM answer."""
    # Look for numbered questions or bullet points that are questions
    questions = []
    for line in answer.split("\n"):
        line = line.strip()
        # Match lines that look like questions
        if "?" in line:
            # Clean up markdown formatting
            clean = re.sub(r'^[\d\.\-\*]+\s*', '', line)
            clean = clean.strip("*_`").strip()
            if clean and len(clean) > 10 and clean not in questions:
                questions.append(clean)
    return questions[:6]


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Main chat endpoint — routes to RAG, recommendation, certification, hallmarking, or lab flows."""

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

    # ── Step 2.5: Product KB lookup ──
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
        # Product → Standard recommendation
        recs = recommend_standards(query_en, top_k=5)
        if recs:
            lines = ["### Applicable Indian Standards\n"]
            for r in recs:
                lines.append(f"### **{r.is_number}** — {r.title}\n")
                lines.append(f"_{r.explanation}_\n")
                lines.append("---\n")
            answer = "\n".join(lines)
        elif product_info:
            lines = [f"### Applicable BIS Standard\n"]
            lines.append(f"**{' / '.join(product_info.is_codes)}** — {product_info.name}\n")
            lines.append(f"_{product_info.description}_\n\n")
            lines.append("### What It Covers\n")
            for item in product_info.key_tests:
                lines.append(f"- {item}")
            lines.append("\n### Certification Status\n")
            lines.append(f"**{product_info.certification}** — {product_info.certification_scheme} Scheme\n")
            answer = "\n".join(lines)
        else:
            answer = "I couldn't identify specific standards for your product. Please try describing your product in more detail, or check bis.gov.in for the full product-wise standards list."

    elif req.mode == "certify":
        # Certification process explainer
        q_lower = query_en.lower()

        # Check for cost/timeline questions
        if "cost" in q_lower or "price" in q_lower or "fee" in q_lower:
            # Determine which scheme
            scheme = "isi"
            if "crs" in q_lower:
                scheme = "crs"
            elif "hallmark" in q_lower:
                scheme = "hallmarking"

            cost_data = CERTIFICATION_COSTS.get(scheme, CERTIFICATION_COSTS["isi"])
            lines = [f"### BIS Certification Cost Estimate\n"]
            lines.append(f"**Scheme:** {scheme.upper()}\n")
            for key, value in cost_data.items():
                if key != "disclaimer":
                    label = key.replace("_", " ").title()
                    lines.append(f"**{label}:** {value}")
            lines.append(f"\n⚠️ _{cost_data.get('disclaimer', '')}_\n")
            answer = "\n".join(lines)
        else:
            scheme_key = "isi"
            if "crs" in q_lower or "registration" in q_lower or "electronics" in q_lower or "it goods" in q_lower:
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
                        lines.append(f"💡 _{step.tips}_\n")
                lines.append("\n### Documents Required:\n")
                for doc in guide.documents_required:
                    lines.append(f"- {doc}")
                answer = "\n".join(lines)
            else:
                answer = "Please specify the certification scheme: ISI Mark, Compulsory Registration Scheme (CRS), or Hallmarking."

    elif req.mode == "hallmark":
        # Hallmarking Q&A
        faqs = get_hallmarking_faq(query_en)
        if faqs:
            lines = ["### Hallmarking Information\n"]
            for faq in faqs:
                lines.append(f"**Q: {faq['question']}**\nA: {faq['answer']}\n")
            answer = "\n\n".join(lines)
        else:
            try:
                answer, sources = rag_query(query_en, top_k=3, history=history)
            except Exception:
                answer = "For hallmarking queries, please ask about: HUID verification, purity grades, hallmarking process, or where to get jewelry hallmarked."

    elif req.mode == "lab":
        # Lab lookup — upgraded with structured cards
        q_lower = query_en.lower()
        category_keywords = [
            "electrical", "electronic", "food", "textile", "toys", "steel",
            "cement", "plastics", "chemicals", "metals", "leather", "petroleum",
            "power", "transformers", "cables", "IT equipment", "telecom",
            "polymer", "packaging", "sugar", "lubricants", "fuels",
            "building materials", "rubber", "footwear",
        ]
        city_keywords = [
            "delhi", "mumbai", "chennai", "kolkata", "bangalore", "bengaluru",
            "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow", "guwahati",
            "kanpur", "faridabad", "jamshedpur", "chandigarh",
        ]
        found_category = next((c for c in category_keywords if c in q_lower), "")
        found_city = next((c for c in city_keywords if c in q_lower), "")

        labs_found = search_labs(category=found_category, city=found_city)
        if labs_found:
            lines = [f"### BIS-Recognized Testing Labs" + (f" — {found_category.title()}" if found_category else "") + (f" in {found_city.title()}" if found_city else "") + "\n"]
            lines.append(f"Found **{len(labs_found)}** matching labs.\n")
            for lab in labs_found[:10]:
                lines.append(f"**{lab.name}**")
                lines.append(f"📍 {lab.address}, {lab.city}, {lab.state}")
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
                "- A city (e.g., Mumbai, Delhi, Chennai)\n"
                "- A product category (e.g., electrical, food, textiles)\n"
                "- A lab name\n\n"
                "Available categories: electrical, electronic, food, textile, toys, steel, cement, plastics, chemicals, metals, leather, petroleum."
            )

    else:
        # Default: General RAG query — with AI memory from history
        try:
            answer, sources = rag_query(query_en, history=history)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"RAG pipeline error: {str(e)}")

    # ── Step 4: Compute confidence ──
    confidence = _compute_confidence(query_en, sources, product_info)

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

    # Also add product KB follow-ups if available
    if product_info and product_results:
        _, best_entry, _ = product_results[0]
        for q in best_entry.follow_up_questions[:3]:
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
