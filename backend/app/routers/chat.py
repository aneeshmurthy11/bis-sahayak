"""Chat API router — the main conversational endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse, Source
from app.services.rag import rag_query
from app.services.translator import detect_language, translate_to_english, translate_from_english
from app.services.matcher import recommend_standards
from app.services.certification import get_certification_guide, get_hallmarking_faq, CERTIFICATION_SCHEMES
from app.services.labs import search_labs
from app.services.fuzzy_matcher import match_query, apply_correction, get_no_match_message

router = APIRouter(prefix="/api", tags=["chat"])


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
        if fuzzy_match.confidence >= 90:
            # Auto-correct silently
            query_en = apply_correction(query_en, fuzzy_match)
            correction_info = {
                "original_word": fuzzy_match.original_word,
                "corrected_word": fuzzy_match.corrected_word,
                "confidence": fuzzy_match.confidence,
                "suggestions": fuzzy_match.suggestions,
            }
        elif fuzzy_match.confidence >= 75:
            # "Did you mean X?" — still proceed with corrected query
            query_en = apply_correction(query_en, fuzzy_match)
            correction_info = {
                "original_word": fuzzy_match.original_word,
                "corrected_word": fuzzy_match.corrected_word,
                "confidence": fuzzy_match.confidence,
                "suggestions": fuzzy_match.suggestions,
            }
        elif fuzzy_match.confidence >= 60:
            # Multiple suggestions — proceed with best match
            query_en = apply_correction(query_en, fuzzy_match)
            correction_info = {
                "original_word": fuzzy_match.original_word,
                "corrected_word": fuzzy_match.corrected_word,
                "confidence": fuzzy_match.confidence,
                "suggestions": fuzzy_match.suggestions,
            }
        # Below 60: no correction, let it flow through normally

    # ── Step 3: Route by mode ──
    answer = ""
    sources: list[Source] = []

    if req.mode == "recommend":
        # Product → Standard recommendation
        recs = recommend_standards(query_en, top_k=5)
        if recs:
            lines = ["Based on your product description, here are the applicable Indian Standards:\n"]
            for r in recs:
                lines.append(f"**{r.is_number}** — {r.title}\n_{r.explanation}_")
            answer = "\n\n".join(lines)
        else:
            answer = "I couldn't identify specific standards for your product. Please try describing your product in more detail, or check bis.gov.in for the full product-wise standards list."

    elif req.mode == "certify":
        # Certification process explainer
        scheme_key = ""
        q_lower = query_en.lower()
        if "crs" in q_lower or "registration" in q_lower or "electronics" in q_lower or "it goods" in q_lower:
            scheme_key = "crs"
        elif "hallmark" in q_lower:
            scheme_key = "hallmarking"
        else:
            scheme_key = "isi"

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
            lines.append("### Documents Required:\n")
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
            # Fall back to RAG over hallmarking docs
            try:
                answer, sources = rag_query(query_en, top_k=3)
            except Exception:
                answer = "For hallmarking queries, please ask about: HUID verification, purity grades, hallmarking process, or where to get jewelry hallmarked."

    elif req.mode == "lab":
        # Lab lookup
        q_lower = query_en.lower()
        # Try to extract city and category from the query
        category_keywords = ["electrical", "electronic", "food", "textile", "toys", "steel",
                             "cement", "plastics", "chemicals", "metals", "leather", "petroleum"]
        city_keywords = ["delhi", "mumbai", "chennai", "kolkata", "bangalore", "bengaluru",
                         "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow", "guwahati",
                         "kanpur", "faridabad", "jamshedpur", "chandigarh"]
        found_category = next((c for c in category_keywords if c in q_lower), "")
        found_city = next((c for c in city_keywords if c in q_lower), "")

        labs_found = search_labs(category=found_category, city=found_city)
        if labs_found:
            lines = [f"### BIS-Recognized Testing Labs" + (f" ({found_category})" if found_category else "") + (f" in {found_city.title()}" if found_city else "") + "\n"]
            for lab in labs_found[:8]:
                lines.append(f"**{lab.name}**\n📍 {lab.address}, {lab.city}, {lab.state}\n📞 {lab.phone}\n🏷️ Categories: {', '.join(lab.categories)}\n✅ Accreditation: {lab.accreditation}\n")
            if len(labs_found) > 8:
                lines.append(f"_...and {len(labs_found) - 8} more. Refine your search by specifying a city or product category._")
            answer = "\n".join(lines)
        else:
            answer = "No labs found matching your criteria. Try specifying a city (e.g., Mumbai, Delhi) or product category (e.g., electrical, food)."

    else:
        # Default: General RAG query
        try:
            answer, sources = rag_query(query_en)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"RAG pipeline error: {str(e)}")

    # ── Step 3: Translate answer back ──
    if user_lang != "en":
        answer = translate_from_english(answer, user_lang)

    from app.models.schemas import CorrectionInfo
    corr = None
    if correction_info:
        corr = CorrectionInfo(**correction_info)
    return ChatResponse(answer=answer, sources=sources, mode=req.mode, correction=corr)
