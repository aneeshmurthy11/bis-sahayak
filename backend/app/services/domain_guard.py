"""Domain guard — determines if a query belongs to BIS domain.

Uses keyword/intent detection (no LLM call needed) for fast classification.
"""

from __future__ import annotations

import re

# ── BIS Domain Keywords ──────────────────────────────────────────────────────
# These keywords/phrases indicate the query IS about BIS standards.

_BIS_KEYWORDS = [
    # IS codes
    r"\bIS\s*\d+", r"\bIS\s*\d+\s*part", r"\bIS\s*\d+\s*section",
    r"\bIndian\s+Standard", r"\bis\s+code", r"\bis\s+number",
    # Certification
    r"\bBIS\b", r"\bBureau\s+of\s+Indian\s+Standards\b",
    r"\bISI\b", r"\bISI\s+mark", r"\bISI\s+certification",
    r"\bCRS\b", r"\bcompulsory\s+registration\b",
    r"\bFMCS\b", r"\bECO\s+mark\b", r"\bECO\s+certification",
    r"\bcertification\b", r"\bcertified\b", r"\bcertify\b",
    r"\bcertification\s+scheme", r"\bcertification\s+process",
    r"\blicense\b.*\bBIS\b", r"\blicence\b.*\bBIS\b",
    r"\bmanak\b", r"\bmanak\s+online",
    # Hallmarking
    r"\bhallmark\b", r"\bhallmarking\b", r"\bHUID\b",
    r"\bgold\s+hallmark", r"\bsilver\s+hallmark", r"\bplatinum\s+hallmark",
    r"\bpurity\s+grade", r"\b22k\b", r"\b18k\b", r"\b24k\b",
    r"\b916\b", r"\b750\b", r"\b999\b", r"\b925\b",
    r"\bjeweler\s+registration\b", r"\bjeweller\s+registration\b",
    r"\bAHC\b", r"\bassaying\b",
    # Products under BIS
    r"\btoys?\b", r"\bhelmet\b", r"\bcement\b", r"\bsteel\b",
    r"\bwire\b", r"\bcable\b", r"\bPVC\b", r"\bHDPE\b", r"\bLDPE\b",
    r"\bLED\s+bulb", r"\bLED\s+light", r"\bLED\s+lamp",
    r"\bbulb\b", r"\blight\b.*\bstandard\b", r"\blamp\b.*\bstandard\b",
    r"\bbattery\b", r"\bbatteries\b",
    r"\bswitch\b", r"\bsocket\b", r"\bplug\b",
    r"\btransformer\b", r"\bmeter\b", r"\belectric\s+meter",
    r"\bpressure\s+cooker\b", r"\bwater\s+bottle\b",
    r"\bpackaged\s+water\b", r"\bmineral\s+water\b",
    r"\bdrinking\s+water\b", r"\bfood\b.*\bstandard\b",
    r"\btextile\b", r"\bfabric\b", r"\bcotton\b.*\bstandard\b",
    r"\bleather\b", r"\bfootwear\b", r"\bshoe\b",
    r"\bpaint\b", r"\bbearing\b", r"\bsolar\s+panel\b",
    r"\bmatch\b", r"\bspectacle\b", r"\bglasses\b",
    r"\bTMT\s+bar", r"\brebar\b",
    # Testing / Labs
    r"\btesting\b.*\blab\b", r"\blab\b.*\btesting\b",
    r"\bNABL\b", r"\baccredited\b",
    r"\bbis\s+approved\s+lab\b", r"\bbis\s+recognized\s+lab\b",
    r"\bbis\s+testing\b", r"\btesting\s+requirement",
    r"\btest\s+method", r"\btest\s+procedure",
    # Compliance / Safety / Quality
    r"\bcompliance\b", r"\bsafety\s+standard\b",
    r"\bquality\s+standard\b", r"\bmanufacturing\s+standard",
    r"\bsafety\s+requirement\b", r"\bquality\s+requirement",
    r"\blabelling\b", r"\blabeling\b", r"\bpackaging\s+requirement",
    r"\bQCO\b", r"\bquality\s+control\s+order",
    r"\bsafety\s+of\b", r"\bprotective\b.*\bstandard",
    r"\bBIS\s+mark\b", r"\bmarking\s+requirement",
    # General BIS queries
    r"\bwhich\s+standard\b", r"\bwhat\s+standard\b",
    r"\bapplicable\s+standard", r"\bIS\s+standard",
    r"\bstandard\s+for\b", r"\bstandard\s+covers\b",
    r"\bstandard\s+applies\b", r"\bstandard\s+require",
    r"\bcompliance\s+guide", r"\bcompliance\s+checklist",
    r"\bcertification\s+cost", r"\bcost\s+of\s+certification",
    r"\bcertification\s+timeline", r"\bhow\s+long\s+certification",
    r"\bcompare\s+IS\b", r"\bdifference\s+between\s+IS\b",
    r"\bexplain\s+IS\b", r"\bwhat\s+is\s+IS\b",
    r"\btell\s+me\s+about\s+IS\b", r"\bwhat\s+does\s+clause\b",
    r"\bexplain\s+clause\b", r"\bwhat\s+is\s+clause\b",
]

_BIS_PATTERN = re.compile("|".join(_BIS_KEYWORDS), re.IGNORECASE)

# ── Blocking Keywords ────────────────────────────────────────────────────────
# These make the domain guard LESS likely to block (they're ambiguous).
# We don't block easily — err on the side of allowing.

_NON_BIS_EXPLICIT = [
    r"\bsolve\s+(?:this\s+|that\s+|the\s+)?(?:equation|math|calculus|problem)",
    r"\bwrite\s+(a|me|some|the)?\s*(code|program|script|python|javascript)",
    r"\bprogram\s+(me|in|for)\b", r"\bcoding\b",
    r"\bwho\s+is\s+(the\s+)?(prime\s+minister|president|minister)",
    r"\bwhat\s+(is|are)\s+the\s+(weather|temperature)\b",
    r"\btell\s+me\s+a\s+joke\b", r"\bwhat\s+is\s+the\s+time\b",
    r"\brecommend\s+a\s+movie\b", r"\bplay\s+music\b",
    r"\brecipe\b", r"\bhow\s+to\s+cook\b",
    r"\bnews\b", r"\bsports\s+score\b",
]

_NON_BIS_PATTERN = re.compile("|".join(_NON_BIS_EXPLICIT), re.IGNORECASE)


def is_bis_domain(query: str) -> tuple[bool, str | None]:
    """Check if a query belongs to the BIS domain.

    Returns:
        (True, None) if the query is BIS-related.
        (False, refusal_message) if the query is clearly outside BIS domain.
    """
    query_stripped = query.strip()

    # Very short queries — assume BIS domain (let RAG handle it)
    if len(query_stripped) <= 3:
        return True, None

    # Check for explicit non-BIS patterns first
    if _NON_BIS_PATTERN.search(query_stripped):
        return False, (
            "I'm BIS Sahayak, an AI assistant focused on Indian Standards and "
            "BIS services. I can help you with:\n\n"
            "• Indian Standards (IS codes) and their requirements\n"
            "• BIS certification processes (ISI, CRS, FMCS)\n"
            "• Hallmarking for gold, silver, and platinum\n"
            "• BIS-approved testing laboratories\n"
            "• Product compliance and safety standards\n\n"
            "Please ask a question related to BIS standards or certification."
        )

    # Check for BIS domain keywords
    if _BIS_PATTERN.search(query_stripped):
        return True, None

    # Edge case: the query mentions a product category that's commonly BIS-regulated
    product_hints = [
        r"\bcement\b", r"\bsteel\b", r"\bwire\b", r"\bcable\b",
        r"\bhelmet\b", r"\bbulb\b", r"\bLED\b", r"\bPVC\b",
        r"\bbattery\b", r"\bswitch\b", r"\bsocket\b", r"\bplug\b",
        r"\btransformer\b", r"\btoys?\b", r"\btextile\b",
        r"\bleather\b", r"\bfootwear\b", r"\bfood\b.*\b(bis|standard|certif)\b",
        r"\bpressure\s+cooker\b", r"\bwire\s+rope\b",
        r"\bsolar\b", r"\bpipe\b", r"\bpaint\b",
        r"\bglass\b.*\bstandard\b", r"\bmetal\b.*\bstandard\b",
    ]
    for hint in product_hints:
        if re.search(hint, query_stripped, re.IGNORECASE):
            return True, None

    # If it's a question that might be BIS-adjacent (e.g., "how to check quality"),
    # allow it and let the RAG decide
    vague_quality = [
        r"\bquality\b", r"\bsafety\b", r"\bcompliance\b",
        r"\bstandard\b", r"\bcertif\b", r"\blab\b",
        r"\btest\b", r"\bregulat\b", r"\bgovernment\b",
    ]
    for pattern in vague_quality:
        if re.search(pattern, query_stripped, re.IGNORECASE):
            return True, None

    # Default: allow — don't be too aggressive with blocking
    # It's better to give a slightly off-topic answer than to refuse a valid query
    return True, None


def is_expansion_request(query: str) -> bool:
    """Check if the user is asking to expand/clarify the previous answer.

    These phrases indicate the user wants more detail on the SAME topic,
    not a new search.
    """
    expansion_phrases = [
        r"\bexplain\s+(more|better|further|in\s+detail|in\s+simple)\b",
        r"\btell\s+me\s+more\b",
        r"\bgive\s+(me\s+)?(?:an\s+|some\s+)?(more|detail|example|examples)\b",
        r"\bcan\s+you\s+(explain|elaborate|clarify)\b",
        r"\bwhat\s+do\s+you\s+mean\b",
        r"\bhow\s+so\b", r"\bwhy\b",
        r"\bcontinue\b", r"\bgo\s+on\b", r"\bnext\b",
        r"\bsummarize\b", r"\bsummary\b",
        r"\bbullet\s+points?\b", r"\btable\b",
        r"\bdifference\s+between\b",
        r"\bsimple\s+words\b", r"\bin\s+plain\s+english\b",
        r"\bwhat\s+else\b", r"\banything\s+else\b",
        r"\bwho\s+(needs|uses|follows)\b",
        r"\bwhere\s+(is|are|can)\b.*\b(lab|test|certif)\b",
        r"\bcost\b.*\b(certif|BIS)\b",
        r"\bstep\s*by\s*step\b",
        r"\bhow\s+to\b",
        r"\bdocuments?\s+(required|needed)\b",
        r"\bchecklist\b",
        r"\bfollow\s*up\b",
        r"\bmisr\b",  # Hindi for "tell me"
        r"\bsanga\b",  # Marathi for "tell me"
    ]
    query_lower = query.lower().strip()
    # Very short follow-ups that are clearly expansion
    if query_lower in ("more", "why", "how", "example", "examples", "continue",
                        "elaborate", "explain", "details", "details?", "ok",
                        "and?", "then?", "really?", "seriously?"):
        return True
    for phrase in expansion_phrases:
        if re.search(phrase, query_lower):
            return True
    return False


def extract_is_codes(query: str) -> list[str]:
    """Extract IS code references from a query.

    Handles formats like:
    - IS 302
    - IS-302
    - IS302
    - IS 302 Part 1
    - IS 302 Part 1 Section 4
    """
    patterns = [
        r"IS[\s\-]*(\d+(?:\s*Part\s*\d+)?(?:\s*Section\s*\d+)?)",
        r"IS[\s\-]*(\d+)",
    ]
    codes = []
    for pattern in patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        for m in matches:
            clean = re.sub(r"\s+", " ", m.strip())
            code = f"IS {clean}"
            if code not in codes:
                codes.append(code)
    return codes


def extract_clause_reference(query: str) -> str | None:
    """Extract clause references like 'Clause 6.2.1' or 'Section 4.2'."""
    patterns = [
        r"(?:clause|section|subclause|sub-section)\s+([\d\.]+)",
        r"(?:clause|section)\s+([\d\.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1)
    return None
