"""Comprehensive BIS Product Knowledge Base.

Provides structured product data for:
- Product info cards
- Rich response generation
- Standard comparisons
- Certification guidance
- Test requirements
- Follow-up question generation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class ProductKBEntry:
    name: str
    is_codes: list[str]
    title: str
    category: str
    certification: str  # "Mandatory" | "Voluntary" | "CRS"
    certification_scheme: str  # "ISI" | "CRS" | "Hallmarking" | "None"
    description: str
    scope: list[str]
    products_covered: list[str]
    key_tests: list[str]
    documents_required: list[str]
    related_standards: list[str]
    follow_up_questions: list[str]
    common_mistakes: list[str] = field(default_factory=list)
    key_requirements: list[str] = field(default_factory=list)
    industry: str = ""
    validity: str = "BIS License Required Before Sale"


# ── Full Product Database ──────────────────────────────────────────────────────

PRODUCT_DATABASE: dict[str, ProductKBEntry] = {
    "Toys": ProductKBEntry(
        name="Toys",
        is_codes=["IS 9873 (Parts 1-10)", "IS 15644"],
        title="Safety of Toys",
        category="Consumer Products",
        certification="Mandatory",
        certification_scheme="ISI",
        description="Comprehensive safety requirements for all types of toys sold in India, covering mechanical, physical, flammability, and chemical safety.",
        scope=[
            "Mechanical and physical properties",
            "Flammability requirements",
            "Migration of certain elements (chemical safety)",
            "Age labeling and warnings",
            "Electrical safety for battery-operated toys",
            "Radiation safety for radar/toy gun toys",
        ],
        products_covered=[
            "Plastic toys", "Electronic toys", "Dolls", "Building blocks",
            "Puzzles", "Stuffed toys", "RC toys", "Educational toys",
            "Ride-on toys", "Soft toys", "Board games", "Toy guns",
        ],
        key_tests=[
            "Impact Test", "Sharp Edge Test", "Small Parts Test",
            "Flammability Test", "Chemical Migration Test",
            "Drop Test", "Torque Test", "Tension Test",
            "Battery Accessibility Test", "Noise Level Test",
        ],
        documents_required=[
            "Manufacturer details and factory address",
            "Product technical specifications",
            "Manufacturing process flow chart",
            "Quality control test reports",
            "Product samples for testing",
            "NABL-accredited lab test reports",
            "Application form via Manak Online",
        ],
        related_standards=["IS 15644", "IS 9873 Part 1", "IS 9873 Part 2", "IS 9873 Part 3"],
        follow_up_questions=[
            "What is the BIS certification process for toys?",
            "Which labs test toys in India?",
            "What documents are needed for toy certification?",
            "What are the chemical safety limits for toys?",
            "How long does toy certification take?",
            "What is the cost of BIS certification for toys?",
        ],
        common_mistakes=[
            "Not testing for chemical migration limits",
            "Missing age-appropriate warnings on packaging",
            "Using non-certified raw materials",
            "Ignoring small parts testing for toys under 3 years",
        ],
        key_requirements=[
            "All toys sold in India must carry BIS mark",
            "Age grading must be clearly marked",
            "Warning labels required for toys with small parts",
            "Chemical limits per IS 9873 Part 3 must be met",
        ],
        industry="Toy Manufacturing",
    ),

    "Helmets": ProductKBEntry(
        name="Helmets",
        is_codes=["IS 4151"],
        title="Protective Helmets for Two-Wheeler Riders",
        category="Safety Equipment",
        certification="Mandatory",
        certification_scheme="ISI",
        description="Safety requirements and test methods for protective helmets used by two-wheeler riders in India.",
        scope=[
            "Impact absorption performance",
            "Resistance to penetration",
            "Retention system (chin strap) strength",
            "Field of vision requirements",
            "Ventilation requirements",
            "Shell construction standards",
        ],
        products_covered=[
            "Motorcycle helmets", "Scooter helmets", "Moped helmets",
            "Bicycle helmets (separate standard)", "Pillion rider helmets",
        ],
        key_tests=[
            "Impact Test (drop test)", "Penetration Test",
            "Retention System Test (roll-off)", "Chin Strap Strength Test",
            "Vision Field Test", "Surface Smoothness Test",
        ],
        documents_required=[
            "Manufacturer details and factory address",
            "Product technical specifications",
            "Shell material specifications",
            "Padding material details",
            "Quality control test reports",
            "Product samples (multiple sizes)",
            "NABL-accredited lab test reports",
        ],
        related_standards=["IS 9402", "IS 2516"],
        follow_up_questions=[
            "What is the BIS certification process for helmets?",
            "Which labs test helmets in India?",
            "What is the validity of helmet BIS certification?",
            "What are the test requirements for motorcycle helmets?",
            "Cost of BIS certification for helmets?",
            "How to verify if a helmet has BIS mark?",
        ],
        common_mistakes=[
            "Using cheap ABS instead of proper shell material",
            "Skipping penetration testing",
            "Not testing retention system properly",
            "Ignoring weight limits",
        ],
        key_requirements=[
            "All motorcycle helmets sold in India must have ISI mark",
            "Minimum impact absorption required",
            "Chin strap must withstand specified force",
            "Helmet must provide adequate field of vision",
        ],
        industry="Automotive Safety",
    ),

    "Cement": ProductKBEntry(
        name="Cement",
        is_codes=["IS 269", "IS 455", "IS 8112", "IS 12269", "IS 1489"],
        title="Portland Cement Specifications",
        category="Building Materials",
        certification="Mandatory",
        certification_scheme="ISI",
        description="Specifications for various grades of Portland cement used in construction across India.",
        scope=[
            "Chemical composition requirements",
            "Physical properties (fineness, setting time, soundness)",
            "Compressive strength at 3, 7, and 28 days",
            "Manufacturing quality requirements",
            "Testing frequency and sampling",
            "Marking and packaging requirements",
        ],
        products_covered=[
            "33 grade OPC (IS 269)", "43 grade OPC (IS 8112)",
            "53 grade OPC (IS 12269)", "PPC (IS 1489)",
            "PSC/Slag Cement (IS 455)", "Composite Cement",
        ],
        key_tests=[
            "Fineness Test (Blaine)", "Setting Time Test (Vicat)",
            "Soundness Test (Le Chatelier)", "Compressive Strength Test",
            "Chemical Analysis (C3S, C2S, C3A, C4AF)", "Autoclave Expansion",
            "Drying Shrinkage", "Heat of Hydration",
        ],
        documents_required=[
            "Manufacturer details and factory address",
            "Raw material source details",
            "Kiln and grinding mill specifications",
            "Quality control lab setup details",
            "Product test reports",
            "Manufacturing process flow chart",
        ],
        related_standards=["IS 1489 Part 1", "IS 1489 Part 2", "IS 455", "IS 12269"],
        follow_up_questions=[
            "What is the difference between OPC and PPC?",
            "Which cement grade is best for construction?",
            "How to test cement quality at site?",
            "What is the BIS certification process for cement?",
            "How long does cement certification take?",
            "What are the chemical limits for cement?",
        ],
        industry="Construction Materials",
    ),

    "Steel": ProductKBEntry(
        name="Steel",
        is_codes=["IS 2062", "IS 808", "IS 1570"],
        title="Steel for Structural Purposes",
        category="Building Materials",
        certification="Mandatory",
        certification_scheme="ISI",
        description="Requirements for structural steel used in construction, bridges, and general engineering applications.",
        scope=[
            "Chemical composition (C, Mn, S, P, Si)",
            "Mechanical properties (yield strength, tensile strength, elongation)",
            "Dimensional tolerances",
            "Testing and inspection requirements",
            "Marking and certification",
        ],
        products_covered=[
            "Structural steel sections", "Steel bars and rods",
            "Steel plates and sheets", "TMT bars",
            "Steel pipes and tubes", "Steel wire",
        ],
        key_tests=[
            "Tensile Test", "Yield Stress Test", "Elongation Test",
            "Chemical Analysis (spectrometer)", "Bend Test",
            "Impact Test (Charpy)", "Hardness Test",
        ],
        documents_required=[
            "Manufacturer details and mill address",
            "Raw material sourcing details",
            "Rolling mill specifications",
            "Quality control procedure manual",
            "Test certificates from NABL lab",
        ],
        related_standards=["IS 808", "IS 1570", "IS 1786", "IS 2002"],
        follow_up_questions=[
            "What is the difference between IS 2062 and IS 1786?",
            "How to verify steel quality at site?",
            "What are TMT bar grades?",
            "BIS certification process for steel products?",
            "Which labs test structural steel?",
        ],
        industry="Construction & Infrastructure",
    ),

    "Electrical Appliances": ProductKBEntry(
        name="Electrical Appliances",
        is_codes=["IS 302 (Parts 1 & 2)"],
        title="Safety of Household and Similar Electrical Appliances",
        category="Electrical Products",
        certification="Mandatory",
        certification_scheme="ISI",
        description="General safety requirements for household and similar electrical appliances including ironing, cooking, washing, and cooling appliances.",
        scope=[
            "Protection against electric shock",
            "Protection against fire (flammability)",
            "Protection against mechanical hazards",
            "Protection against excessive temperature",
            "Protection against water and moisture",
            "Operating instructions and markings",
        ],
        products_covered=[
            "Iron", "Mixer grinder", "Fan", "Heater", "Water heater",
            "Refrigerator", "Air conditioner", "Washing machine",
            "Microwave oven", "Induction cooktop", "Toaster", "Kettle",
        ],
        key_tests=[
            "Earth Continuity Test", "Insulation Resistance Test",
            "Dielectric Strength Test", "Leakage Current Test",
            "Temperature Rise Test", "Abnormal Operation Test",
            "Stability Test", "Water Spray Test",
        ],
        documents_required=[
            "Manufacturer details and factory address",
            "Product technical specifications and circuit diagrams",
            "Component specifications (thermostat, fuse, etc.)",
            "Quality control test reports",
            "Product samples for testing",
        ],
        related_standards=["IS 302 Part 1", "IS 302 Part 2", "IS 16102", "IS 16818"],
        follow_up_questions=[
            "What is the difference between ISI and CRS for electronics?",
            "How to get BIS certification for electrical appliances?",
            "Which labs test electrical products?",
            "What documents are needed for ISI certification?",
            "Cost of BIS certification for appliances?",
        ],
        industry="Electronics & Appliances",
    ),

    "Packaged Drinking Water": ProductKBEntry(
        name="Packaged Drinking Water",
        is_codes=["IS 14543"],
        title="Packaged Drinking Water",
        category="Food & Beverages",
        certification="Mandatory",
        certification_scheme="ISI",
        description="Requirements for packaged drinking water including mineral water, purified water, and flavored water products.",
        scope=[
            "Microbiological requirements",
            "Chemical parameters (TDS, pH, minerals)",
            "Heavy metal limits",
            "Packaging and labeling requirements",
            "Manufacturing facility requirements",
            "Testing frequency",
        ],
        products_covered=[
            "Packaged drinking water", "Mineral water",
            "Purified water", "Flavored water",
            "Carbonated water (separate standard)",
        ],
        key_tests=[
            "Microbial Test (E. coli, Coliform)", "pH Test",
            "TDS Test", "Heavy Metal Analysis",
            "Mineral Content Analysis", "Chemical Oxygen Demand",
        ],
        documents_required=[
            "Manufacturer details and plant address",
            "Water source analysis report",
            "Purification process description",
            "BIS-recognized lab test reports",
            "FSSAI license (if applicable)",
        ],
        related_standards=["IS 10500", "IS 13428"],
        follow_up_questions=[
            "What is the difference between IS 10500 and IS 14543?",
            "How to get BIS certification for water plant?",
            "What testing is required for packaged water?",
            "FSSAI vs BIS for water products?",
            "Cost of water plant BIS certification?",
        ],
        industry="Food & Beverages",
    ),

    "Gold Jewelry": ProductKBEntry(
        name="Gold Jewelry",
        is_codes=["IS 1417", "IS 1418"],
        title="Gold Jewelry — Purity Determination",
        category="Precious Metals",
        certification="Mandatory",
        certification_scheme="Hallmarking",
        description="Quality standards for gold jewelry including purity grades, hallmarking requirements, and HUID verification.",
        scope=[
            "Purity grades (14K, 18K, 20K, 22K, 23K, 24K)",
            "Hallmarking requirements",
            "HUID (Hallmark Unique Identification)",
            "Assaying and Hallmarking Centre (AHC) requirements",
            "Jeweler registration requirements",
        ],
        products_covered=[
            "Gold rings", "Gold necklaces", "Gold bangles",
            "Gold bracelets", "Gold chains", "Gold earrings",
            "Gold coins", "Gold artifacts",
        ],
        key_tests=[
            "XRF (X-Ray Fluorescence) Analysis",
            "Fire Assay Test", "Acid Test",
            "Purity Determination", "Hallmark Verification",
        ],
        documents_required=[
            "Jeweler registration application",
            "GST registration certificate",
            "PAN card of the firm",
            "Shop license / trade license",
            "ID proof of authorized person",
        ],
        related_standards=["IS 1418", "IS 1417"],
        follow_up_questions=[
            "What is HUID and how does it work?",
            "How to verify gold hallmark at home?",
            "Is hallmarking mandatory in India?",
            "What are the purity grades for gold?",
            "How to register as a jeweler with BIS?",
            "Difference between 22K and 24K gold?",
        ],
        industry="Jewelry & Precious Metals",
    ),

    "Plastics": ProductKBEntry(
        name="Plastics",
        is_codes=["IS 10146", "IS 4985", "IS 10156"],
        title="Polyethylene and PVC Products",
        category="Polymer Products",
        certification="Voluntary",
        certification_scheme="ISI",
        description="Standards for polyethylene, PVC, and other plastic products used in piping, packaging, and general applications.",
        scope=[
            "Material specifications",
            "Mechanical properties (tensile, impact)",
            "Dimensional tolerances",
            "Chemical resistance",
            "Environmental stress crack resistance",
        ],
        products_covered=[
            "HDPE pipes", "LDPE films", "PVC pipes",
            "Plastic bottles", "Plastic containers",
            "Plastic packaging materials",
        ],
        key_tests=[
            "Tensile Strength Test", "Impact Test (Charpy/Izod)",
            "Dimensional Measurement", "Hydrostatic Pressure Test",
            "Melt Flow Index", "Density Test",
        ],
        documents_required=[
            "Manufacturer details",
            "Raw material specifications",
            "Product technical data sheets",
            "NABL lab test reports",
        ],
        related_standards=["IS 4985", "IS 10146", "IS 10156", "IS 1239"],
        follow_up_questions=[
            "What is the difference between HDPE and PVC pipes?",
            "How to test pipe quality?",
            "BIS certification for plastic pipes?",
            "Which labs test plastic products?",
        ],
        industry="Plastics & Polymers",
    ),

    "LED Bulbs": ProductKBEntry(
        name="LED Bulbs",
        is_codes=["IS 16102 (Part 1)", "IS 16104"],
        title="LED Luminaires and Bulbs",
        category="Electrical Products",
        certification="CRS",
        certification_scheme="CRS",
        description="Requirements for LED bulbs, luminaires, and related products under the Compulsory Registration Scheme.",
        scope=[
            "Luminous efficacy requirements",
            "Color temperature and CRI",
            "Power factor requirements",
            "Lifetime and lumen maintenance",
            "Electrical safety",
            "EMC requirements",
        ],
        products_covered=[
            "LED bulbs", "LED tube lights", "LED panel lights",
            "LED downlights", "LED street lights",
            "LED batten lights",
        ],
        key_tests=[
            "Luminous Flux Test", "Color Temperature Test",
            "Power Consumption Test", "Power Factor Test",
            "Electrical Safety Test", "EMC Test",
            "Lifetime Test (LM-80)", "Flicker Test",
        ],
        documents_required=[
            "Product technical specifications",
            "LED chip and driver specifications",
            "Test reports from CRS-recognized lab",
            "Product photographs",
            "Manufacturing process details",
        ],
        related_standards=["IS 10322", "IS 15885", "IS 16102 Part 2"],
        follow_up_questions=[
            "What is the difference between ISI and CRS for LEDs?",
            "How to register LED products under CRS?",
            "Which labs test LED products?",
            "What are the BIS requirements for LED drivers?",
        ],
        industry="Lighting & Electronics",
    ),

    "Wires and Cables": ProductKBEntry(
        name="Wires and Cables",
        is_codes=["IS 694", "IS 1554", "IS 7098"],
        title="PVC Insulated Wires and Cables",
        category="Electrical Products",
        certification="Mandatory",
        certification_scheme="ISI",
        description="Standards for PVC insulated electrical wires and cables used in domestic, industrial, and underground applications.",
        scope=[
            "Conductor material and size specifications",
            "Insulation thickness requirements",
            "Voltage rating requirements",
            "Current carrying capacity",
            "Fire resistance (FR grade)",
            "Flexibility requirements",
        ],
        products_covered=[
            "House wiring cables", "Industrial cables",
            "Underground cables", "Flexible cords",
            "Control cables", "Submersible pump cables",
        ],
        key_tests=[
            "Conductor Resistance Test", "Insulation Resistance Test",
            "Voltage Withstand Test", "Tensile Strength Test",
            "Elongation Test", "Heat Shock Test",
            "Flame Propagation Test", "Conductor Continuity Test",
        ],
        documents_required=[
            "Manufacturer details and factory address",
            "Conductor and insulation specifications",
            "Manufacturing process details",
            "Quality control procedures",
            "NABL lab test reports",
        ],
        related_standards=["IS 1554 Part 1", "IS 1554 Part 2", "IS 7098 Part 1", "IS 7098 Part 2"],
        follow_up_questions=[
            "What is the difference between IS 694 and IS 1554?",
            "How to select wire size for home wiring?",
            "FR vs FRLS cables — what's the difference?",
            "BIS certification process for cable manufacturers?",
            "Which labs test electrical cables?",
        ],
        industry="Electrical Infrastructure",
    ),

    "PVC Pipes": ProductKBEntry(
        name="PVC Pipes",
        is_codes=["IS 4985", "IS 1239", "IS 15145"],
        title="PVC Pipes for Water Supply and Drainage",
        category="Building Materials",
        certification="Voluntary",
        certification_scheme="ISI",
        description="Standards for unplasticized PVC pipes used in potable water supply, drainage, and sewage applications.",
        scope=[
            "Material specifications",
            "Dimensional tolerances",
            "Hydrostatic pressure requirements",
            "Impact resistance",
            "Chemical resistance",
        ],
        products_covered=[
            "PVC water supply pipes", "PVC drainage pipes",
            "PVC sewage pipes", "PVC conduit pipes",
            "PVC casing pipes",
        ],
        key_tests=[
            "Hydrostatic Pressure Test", "Impact Resistance Test",
            "Dimensional Measurement", "Tensile Strength Test",
            "Flattening Test", "Reversion Test",
        ],
        documents_required=[
            "Manufacturer details",
            "Raw material specifications",
            "Product dimension catalog",
            "NABL lab test reports",
        ],
        related_standards=["IS 1239", "IS 15145", "IS 10146"],
        follow_up_questions=[
            "What is the difference between uPVC and PVC pipes?",
            "How to test PVC pipe quality?",
            "Which pipes are best for home plumbing?",
            "BIS certification for pipe manufacturers?",
        ],
        industry="Construction Materials",
    ),

    "Textiles": ProductKBEntry(
        name="Textiles",
        is_codes=["IS 1966", "IS 14878", "IS 9883"],
        title="Textile Standards",
        category="Textiles & Apparel",
        certification="Voluntary",
        certification_scheme="ISI",
        description="Standards for textile products covering labeling, color fastness, and quality requirements.",
        scope=[
            "Labeling and care instructions",
            "Color fastness requirements",
            "Dimensional stability (shrinkage)",
            "Fabric strength",
            "Pilling resistance",
        ],
        products_covered=[
            "Cotton garments", "Synthetic fabrics",
            "Denim", "Silk products", "Wool products",
            "Blend fabrics",
        ],
        key_tests=[
            "Color Fastness to Washing", "Color Fastness to Light",
            "Dimensional Stability Test", "Tensile Strength Test",
            "Pilling Resistance Test", "GSM Test",
        ],
        documents_required=[
            "Manufacturer details",
            "Fabric specifications",
            "Dye and finish details",
            "NABL lab test reports",
        ],
        related_standards=["IS 1966", "IS 14878", "IS 9883"],
        follow_up_questions=[
            "How to read textile care labels?",
            "What is color fastness testing?",
            "BIS labeling requirements for garments?",
            "Which labs test textiles in India?",
        ],
        industry="Textiles & Apparel",
    ),

    "Batteries": ProductKBEntry(
        name="Batteries",
        is_codes=["IS 8144", "IS 15659"],
        title="Lead-Acid and Lithium Batteries",
        category="Electrical Products",
        certification="Mandatory",
        certification_scheme="ISI",
        description="Standards for automotive, industrial, and lithium batteries used in various applications.",
        scope=[
            "Capacity and performance requirements",
            "Safety requirements",
            "Dimensional specifications",
            "Charge/discharge characteristics",
            "Life cycle requirements",
        ],
        products_covered=[
            "Car batteries", "UPS batteries", "Inverter batteries",
            "Lithium-ion cells", "Lithium-ion batteries",
            "Industrial batteries",
        ],
        key_tests=[
            "Capacity Test", "Internal Resistance Test",
            "Charge/Discharge Cycle Test", "Short Circuit Test",
            "Overcharge Test", "Drop Test",
        ],
        documents_required=[
            "Manufacturer details",
            "Cell/battery specifications",
            "Safety test reports",
            "NABL lab test reports",
        ],
        related_standards=["IS 15659", "IS 16046"],
        follow_up_questions=[
            "What is the difference between ISI and CRS for batteries?",
            "How to test battery capacity?",
            "Lithium battery BIS requirements?",
            "Which labs test batteries?",
        ],
        industry="Energy Storage",
    ),

    "Helmets_bicycle": ProductKBEntry(
        name="Bicycle Helmets",
        is_codes=["IS 5756"],
        title="Protective Helmets for Bicycle Riders",
        category="Safety Equipment",
        certification="Voluntary",
        certification_scheme="ISI",
        description="Safety requirements for helmets used by bicycle riders.",
        scope=["Impact absorption", "Retention system", "Field of vision"],
        products_covered=["Bicycle helmets", "Skating helmets"],
        key_tests=["Impact Test", "Retention Test", "Vision Field Test"],
        documents_required=["Manufacturer details", "Test reports", "Product samples"],
        related_standards=["IS 4151"],
        follow_up_questions=["Is bicycle helmet BIS mandatory?", "How to test bicycle helmets?"],
        industry="Sports & Safety",
    ),
}


# ── Lookup Functions ───────────────────────────────────────────────────────────

def get_product_by_name(name: str) -> ProductKBEntry | None:
    """Look up a product by its canonical name (case-insensitive)."""
    return PRODUCT_DATABASE.get(name)


def search_products(query: str) -> list[tuple[str, ProductKBEntry, float]]:
    """Search products by query. Returns list of (name, entry, score)."""
    from rapidfuzz import fuzz, process

    query_lower = query.lower()
    results = []

    # Direct name match
    for name, entry in PRODUCT_DATABASE.items():
        # Check name match
        name_score = fuzz.partial_ratio(query_lower, name.lower())
        # Check IS code match
        is_score = max(
            (fuzz.partial_ratio(query_lower, code.lower()) for code in entry.is_codes),
            default=0
        )
        # Check category match
        cat_score = fuzz.partial_ratio(query_lower, entry.category.lower())
        # Check products covered
        prod_score = max(
            (fuzz.partial_ratio(query_lower, p.lower()) for p in entry.products_covered),
            default=0
        )

        best_score = max(name_score, is_score, cat_score, prod_score)
        if best_score >= 50:
            results.append((name, entry, best_score))

    results.sort(key=lambda x: x[2], reverse=True)
    return results[:5]


def get_all_product_names() -> list[str]:
    """Return all canonical product names."""
    return list(PRODUCT_DATABASE.keys())


def get_product_by_is_code(is_code: str) -> list[tuple[str, ProductKBEntry]]:
    """Find products that reference a specific IS code."""
    import re
    code_num = re.search(r'(\d+)', is_code)
    if not code_num:
        return []

    results = []
    for name, entry in PRODUCT_DATABASE.items():
        for code in entry.is_codes:
            if code_num.group(1) in code:
                results.append((name, entry))
                break
    return results


def generate_comparison(is_code_a: str, is_code_b: str) -> dict:
    """Generate a structured comparison between two IS standards."""
    products_a = get_product_by_is_code(is_code_a)
    products_b = get_product_by_is_code(is_code_b)

    a_entry = products_a[0][1] if products_a else None
    b_entry = products_b[0][1] if products_b else None

    return {
        "standard_a": is_code_a,
        "standard_b": is_code_b,
        "name_a": a_entry.name if a_entry else is_code_a,
        "name_b": b_entry.name if b_entry else is_code_b,
        "comparison": {
            "purpose": [a_entry.description if a_entry else "N/A", b_entry.description if b_entry else "N/A"],
            "applies_to": [a_entry.category if a_entry else "N/A", b_entry.category if b_entry else "N/A"],
            "certification": [a_entry.certification if a_entry else "N/A", b_entry.certification if b_entry else "N/A"],
            "tests": [len(a_entry.key_tests) if a_entry else 0, len(b_entry.key_tests) if b_entry else 0],
            "products": [a_entry.products_covered if a_entry else [], b_entry.products_covered if b_entry else []],
        },
    }


# ── Certification Cost Estimates ───────────────────────────────────────────────

CERTIFICATION_COSTS = {
    "isi": {
        "application_fee": "₹5,000 – ₹25,000",
        "testing_fee": "₹15,000 – ₹75,000",
        "inspection_fee": "₹10,000 – ₹30,000",
        "license_fee": "₹20,000 – ₹50,000 per annum",
        "renewal_fee": "₹10,000 – ₹25,000 per annum",
        "total_estimate": "₹60,000 – ₹2,00,000",
        "timeline": "2–4 months",
        "disclaimer": "Costs are estimates and may vary based on product type, testing complexity, and factory location.",
    },
    "crs": {
        "application_fee": "₹2,000 – ₹10,000",
        "testing_fee": "₹20,000 – ₹1,00,000",
        "registration_fee": "₹10,000 – ₹30,000",
        "renewal_fee": "₹5,000 – ₹15,000 per annum",
        "total_estimate": "₹37,000 – ₹1,55,000",
        "timeline": "1–3 months",
        "disclaimer": "Costs are estimates and may vary based on product category and testing requirements.",
    },
    "hallmarking": {
        "jeweler_registration": "Free",
        "hallmarking_per_item": "₹45 – ₹200 per item (depending on weight and AHC)",
        "total_estimate": "Per-item pricing, no bulk license needed",
        "timeline": "1–2 months for registration",
        "disclaimer": "Hallmarking is per-item. Costs vary by AHC and jewelry weight.",
    },
}
