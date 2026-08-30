"""Fuzzy matcher for BIS product/category query understanding.

Detects typos, misspellings, and partial words in user queries and maps them
to known BIS products, standards, certification topics, and lab categories.

Thresholds:
  ≥90 → auto-correct silently (replace word)
  75–89 → "Did you mean X?" (single suggestion)
  60–74 → "Did you mean one of these?" (top 3 suggestions)
  <60  → fallback message
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from rapidfuzz import fuzz, process


# ── Knowledge Base ─────────────────────────────────────────────────────────────
# Every entry has a canonical display name and a list of aliases/variations.
# Aliases include common misspellings, abbreviations, and synonyms.

@dataclass(frozen=True)
class KBEntry:
    canonical: str
    aliases: tuple[str, ...]
    category: str  # "product" | "certification" | "hallmarking" | "lab"


_KNOWLEDGE_BASE: list[KBEntry] = [
    # ── Products / Standards ────────────────────────────────────────────────
    KBEntry("Toys", ("toy", "toys", "tyos", "toyss", "toyz", "children toy",
                      "kids toy", "playing toy", "doll", "dolls", "building blocks",
                      "puzzle", "puzzles", "board game"), "product"),
    KBEntry("Electrical Appliances", ("electrical", "electrical appliance", "appliance",
                                       "electrical appliances", "household appliance",
                                       "power appliance", "electric appliance",
                                       "ironing appliance", "washing machine",
                                       "refrigerator", "air conditioner", "mixer",
                                       "grinder", "fan", "heater"), "product"),
    KBEntry("Wires", ("wire", "wires", "wirs", "wir", "wiring", "cable",
                       "cables", "electrical wire", "power cable", "wiring cable",
                       "wire rope", "wire ropes", "copper wire"), "product"),
    KBEntry("Packaged Drinking Water", ("packaged water", "drinking water",
                                         "mineral water", "water bottle",
                                         "bottled water", "packaged drinking water",
                                         "water packaging"), "product"),
    KBEntry("Packaged Food", ("packaged food", "food", "processed food",
                               "edible oil", "milk", "spice", "flour", "rice",
                               "pulse", "food product", "food packaging",
                               "pre-packaged food", "food labeling"), "product"),
    KBEntry("Cement", ("cement", "ceement", "cemment", "cemen", "opc", "ppc",
                        "portland cement", "slag cement", "building material",
                        "concrete", "grading cement", "cement grade"), "product"),
    KBEntry("Steel", ("steel", "steeel", "stel", "steel rod", "steel bar",
                       "structural steel", "iron", "metal rod", "steel pipe",
                       "steel tube", "steel sheet", "steel bottle"), "product"),
    KBEntry("Gold Jewelry", ("gold", "gold jewelry", "gold jewellery",
                              "gold ring", "gold necklace", "gold bangle",
                              "gold bracelet", "22k gold", "22 karat",
                              "carat gold", "karat gold", "jewelry",
                              "jewellery"), "product"),
    KBEntry("Silver Jewelry", ("silver", "silver jewelry", "silver jewellery",
                                "silver ring", "silver necklace",
                                "925 silver", "sterling silver"), "product"),
    KBEntry("Plastics", ("plastic", "plastics", "plastic bottle", "pvc",
                          "pvc pipe", "hdpe", "ldpe", "pet", "polymer",
                          "plastic pipe", "plastic container",
                          "plastic packaging"), "product"),
    KBEntry("Textiles", ("textile", "textiles", "fabric", "cloth", "cotton",
                          "synthetic fabric", "garment", "shirt", "pants",
                          "dress", "apparel", "clothing"), "product"),
    KBEntry("Batteries", ("battery", "batteries", "cell", "accumulator",
                           "rechargeable battery", "dry cell", "lead acid",
                           "car battery"), "product"),
    KBEntry("Solar Panels", ("solar", "solar panel", "solar panels",
                              "photovoltaic", "pv module", "solar module",
                              "solar cell", "renewable energy"), "product"),
    KBEntry("LPG", ("lpg", "cooking gas", "gas cylinder", "gas stove",
                      "burner", "lpg burner"), "product"),
    KBEntry("Helmets", ("helmet", "helmets", "helmit", "helmit",
                          "safety helmet", "bike helmet", "motorcycle helmet",
                          "riding helmet", "two wheeler helmet"), "product"),
    KBEntry("Bulbs", ("bulb", "bulbs", "bulps", "blub", "blubs",
                       "led bulb", "led bulbs", "light bulb",
                       "lighting", "lamp"), "product"),
    KBEntry("Transformers", ("transformer", "transformers", "power transformer",
                              "distribution transformer", "transformor"), "product"),
    KBEntry("Switches", ("switch", "switches", "electrical switch",
                          "power switch", "socket", "sockets",
                          "plug", "plugs", "plug socket"), "product"),
    KBEntry("Meters", ("meter", "meters", "electric meter", "energy meter",
                        "watt meter", "voltmeter", "ammeter"), "product"),
    KBEntry("Pipes", ("pipe", "pipes", "water pipe", "drainage pipe",
                       "sewage pipe", "hdpe pipe"), "product"),
    KBEntry("Bearings", ("bearing", "bearings", "ball bearing",
                          "roller bearing"), "product"),
    KBEntry("Paints", ("paint", "paints", "painting", "wall paint",
                        "industrial paint", "primer"), "product"),
    KBEntry("Leather", ("leather", "leather products", "leather goods",
                         "shoes", "footwear", "leather footwear"), "product"),
    KBEntry("Footwear", ("footwear", "shoes", "shoe", "sandals",
                          "slippers", "boots", "leather footwear"), "product"),
    KBEntry("Kitchen Utensils", ("utensil", "utensils", "kitchen utensil",
                                  "stainless steel utensil", "cooking vessel",
                                  "pressure cooker", "cookware"), "product"),
    KBEntry("Bottles", ("bottle", "bottles", "steel bottle",
                         "water bottle", "plastic bottle",
                         "glass bottle"), "product"),
    KBEntry("Spectacles", ("spectacles", "spectacle", "glasses",
                            "eyeglasses", "sunglasses", "frames",
                            "optical frame"), "product"),
    KBEntry("Matches", ("match", "matches", "matchstick", "matchbox",
                         "safety match"), "product"),
    KBEntry("TMT Bars", ("tmt", "tmt bar", "tmt bars", "rebar",
                          "reinforcement bar", "steel bar"), "product"),

    # ── Certification Topics ────────────────────────────────────────────────
    KBEntry("ISI Mark", ("isi", "isi mark", "isi certification",
                           "bisi mark", "is mark"), "certification"),
    KBEntry("Compulsory Registration Scheme", ("crs", "crs scheme",
                                                "compulsory registration",
                                                "registration scheme",
                                                "crs certification"), "certification"),
    KBEntry("BIS Certification", ("bis certification", "bis cert",
                                   "bis certificate", "certification",
                                   "certify", "certificate"), "certification"),

    # ── Hallmarking Topics ──────────────────────────────────────────────────
    KBEntry("Hallmarking", ("hallmark", "hallmarking", "halmat", "hallmarck",
                              "hallmarking scheme", "hall marking",
                              "gold hallmark", "silver hallmark"), "hallmarking"),
    KBEntry("HUID", ("huid", "hallmark unique identification", "huid number",
                      "huid code", "huid verification", "huid verify"), "hallmarking"),
    KBEntry("Gold Purity", ("gold purity", "purity grade", "purity",
                             "carat", "karat", "22k", "18k", "24k",
                             "916", "750", "999"), "hallmarking"),
    KBEntry("Jeweler Registration", ("jeweler registration", "jeweller registration",
                                      "jeweler license", "jeweler registration bis"), "hallmarking"),

    # ── Lab / Testing Topics ────────────────────────────────────────────────
    KBEntry("Testing Laboratory", ("lab", "laboratory", "testing lab",
                                     "test lab", "testing laboratory",
                                     "bis lab", "bis testing lab",
                                     "bis approved lab", "bis recognized lab",
                                     "testing center", "test center",
                                     "accredited lab", "nabl lab"), "lab"),
    KBEntry("Electrical Testing", ("electrical testing", "electrical test",
                                     "electrical lab"), "lab"),
    KBEntry("Food Testing", ("food testing", "food test", "food lab",
                              "food safety testing"), "lab"),
    KBEntry("Toy Testing", ("toy testing", "toy safety testing"), "lab"),
    KBEntry("Textile Testing", ("textile testing", "fabric testing"), "lab"),
    KBEntry("Steel Testing", ("steel testing", "metal testing",
                               "metallurgical testing"), "lab"),
    KBEntry("Cement Testing", ("cement testing", "cement lab"), "lab"),
    KBEntry("Plastics Testing", ("plastics testing", "polymer testing",
                                   "plastic testing"), "lab"),
    KBEntry("Leather Testing", ("leather testing", "leather lab"), "lab"),
    KBEntry("Chemical Testing", ("chemical testing", "chemical lab",
                                   "chemicals testing"), "lab"),
]

# Build a flat list of (alias → entry) for fast lookup
_ALIAS_MAP: dict[str, KBEntry] = {}
for _entry in _KNOWLEDGE_BASE:
    for _alias in _entry.aliases:
        _ALIAS_MAP[_alias.lower()] = _entry


# ── Fuzzy Match Result ─────────────────────────────────────────────────────────

@dataclass
class FuzzyMatchResult:
    corrected_query: str      # the query with typos replaced
    original_word: str        # the word that was misspelled
    corrected_word: str       # the canonical replacement
    confidence: float         # 0–100
    suggestions: list[str]    # top N canonical names (for ambiguous cases)
    category: str             # "product" | "certification" | "hallmarking" | "lab"


def _extract_query_tokens(query: str) -> list[str]:
    """Extract meaningful tokens from a query, preserving multi-word phrases.

    Skips IS code patterns (IS 15757, IS15757, etc.) to avoid corruption.
    """
    import re
    query_lower = query.lower().strip()

    # Preserve IS codes — remove them before tokenizing
    is_codes = re.findall(r'IS[\s\-]*\d+', query, re.IGNORECASE)
    sanitized = re.sub(r'IS[\s\-]*\d+', ' ', query, flags=re.IGNORECASE)
    sanitized_lower = sanitized.lower().strip()

    tokens = []
    # Try to match longest known phrases first
    sorted_aliases = sorted(_ALIAS_MAP.keys(), key=len, reverse=True)
    remaining = sanitized_lower
    for alias in sorted_aliases:
        while alias in remaining:
            tokens.append(alias)
            remaining = remaining.replace(alias, " ", 1)
    # Add remaining individual words
    for word in remaining.split():
        if len(word) >= 2:
            tokens.append(word)
    return tokens


def match_query(query: str) -> FuzzyMatchResult | None:
    """Match a user query against the knowledge base.

    Returns a FuzzyMatchResult if a match is found above the threshold (60).
    Returns None if nothing matches.

    IMPORTANT: Skips queries containing IS codes (IS 15757, IS15757, etc.)
    to avoid corrupting the query with false corrections.
    """
    import re
    query_lower = query.lower().strip()

    # ── SKIP: If query contains an IS code, don't fuzzy-match ──
    # IS codes should go directly to RAG, not through fuzzy correction
    if re.search(r'IS[\s\-]*\d+', query, re.IGNORECASE):
        return None

    # ── 1. Try exact / substring match first ──
    for alias, entry in _ALIAS_MAP.items():
        if alias in query_lower:
            return FuzzyMatchResult(
                corrected_query=query,
                original_word=alias,
                corrected_word=entry.canonical,
                confidence=100.0,
                suggestions=[entry.canonical],
                category=entry.category,
            )

    # ── 2. Extract tokens and try fuzzy match on each ──
    tokens = _extract_query_tokens(query)
    all_canonicals = list({e.canonical for e in _KNOWLEDGE_BASE})
    all_aliases_flat = list(_ALIAS_MAP.keys())

    best_match: FuzzyMatchResult | None = None

    for token in tokens:
        if len(token) < 2:
            continue

        # Match against canonical names
        result_canonical = process.extractOne(
            token, all_canonicals,
            scorer=fuzz.WRatio,
            score_cutoff=70,
        )
        # Match against all aliases
        result_alias = process.extractOne(
            token, all_aliases_flat,
            scorer=fuzz.WRatio,
            score_cutoff=70,
        )

        # Use whichever scored higher
        candidates = []
        if result_canonical:
            candidates.append(("canonical", result_canonical))
        if result_alias:
            candidates.append(("alias", result_alias))

        if not candidates:
            continue

        # Sort by score descending
        candidates.sort(key=lambda x: x[1][1], reverse=True)
        best_type, (matched_str, score, _idx) = candidates[0]

        # Look up the entry
        if best_type == "alias":
            entry = _ALIAS_MAP.get(matched_str.lower())
        else:
            # Find entry by canonical name
            entry = None
            for e in _KNOWLEDGE_BASE:
                if e.canonical.lower() == matched_str.lower():
                    entry = e
                    break

        if not entry:
            continue

        # Get multiple suggestions for ambiguous cases
        top_matches = process.extract(
            token, all_canonicals,
            scorer=fuzz.WRatio,
            limit=3,
            score_cutoff=50,
        )
        suggestions = list({m[0] for m in top_matches})
        # Ensure the best match is first
        if entry.canonical in suggestions:
            suggestions.remove(entry.canonical)
        suggestions.insert(0, entry.canonical)
        suggestions = suggestions[:3]

        if best_match is None or score > best_match.confidence:
            best_match = FuzzyMatchResult(
                corrected_query=query,
                original_word=token,
                corrected_word=entry.canonical,
                confidence=float(score),
                suggestions=suggestions,
                category=entry.category,
            )

    return best_match


def apply_correction(query: str, match: FuzzyMatchResult) -> str:
    """Replace the misspelled word in the query with the canonical form."""
    # Replace the original word (case-insensitive) with the canonical form
    import re
    pattern = re.compile(re.escape(match.original_word), re.IGNORECASE)
    corrected = pattern.sub(match.corrected_word, query, count=1)
    return corrected


def get_no_match_message(query: str) -> str:
    """Friendly fallback message when nothing matches."""
    return (
        f"I couldn't find a matching BIS product or standard for \"{query}\".\n\n"
        "Try searching with:\n"
        "- Product name (e.g., cement, toys, wires)\n"
        "- IS number (e.g., IS 302, IS 455)\n"
        "- Hallmark or certification topic\n"
        "- Laboratory or testing topic"
    )
