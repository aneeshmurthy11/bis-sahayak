"""Pydantic request / response schemas."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


# ── Chat ──────────────────────────────────────────────────────────────────────

class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class Source(BaseModel):
    document: str = Field(..., description="e.g. 'IS 302 Part 1'")
    clause: str = Field(default="", description="e.g. 'Clause 4.2'")
    excerpt: str = Field(default="", description="Relevant text snippet")


class ChatRequest(BaseModel):
    message: str
    language: str = Field(default="en", description="ISO 639-1 code: en, hi, bn, ta, te, mr, etc.")
    mode: str = Field(default="general", description="general | recommend | certify | hallmark | lab")
    history: list[dict] = Field(default_factory=list, description="Previous messages for AI memory context")


class CorrectionInfo(BaseModel):
    """Info about auto-corrected typos in the user query."""
    original_word: str
    corrected_word: str
    confidence: float
    suggestions: list[str] = []


class ProductInfo(BaseModel):
    """Structured product information for info cards."""
    name: str
    is_codes: list[str] = []
    category: str = ""
    certification: str = ""
    certification_scheme: str = ""
    description: str = ""
    products_covered: list[str] = []
    key_tests: list[str] = []
    documents_required: list[str] = []
    related_standards: list[str] = []
    key_requirements: list[str] = []
    validity: str = ""


class ComparisonResult(BaseModel):
    """Structured comparison between two IS standards."""
    standard_a: str
    standard_b: str
    name_a: str
    name_b: str
    purpose: list[str] = []
    applies_to: list[str] = []
    certification: list[str] = []
    tests_count: list[int] = []
    products: list[list[str]] = []


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = []
    mode: str = "general"
    correction: CorrectionInfo | None = None
    confidence: float | None = Field(default=None, description="Match confidence 0-100")
    product_info: ProductInfo | None = None
    related_questions: list[str] = []
    comparison: ComparisonResult | None = None
    follow_ups: list[str] = []


# ── Product Recommendation ────────────────────────────────────────────────────

class StandardRecommendation(BaseModel):
    is_number: str
    title: str
    relevance_score: float
    explanation: str


class RecommendRequest(BaseModel):
    product_description: str
    language: str = "en"


class RecommendResponse(BaseModel):
    recommendations: list[StandardRecommendation]
    query: str


# ── Lab Lookup ────────────────────────────────────────────────────────────────

class Lab(BaseModel):
    name: str
    address: str = ""
    city: str = ""
    state: str = ""
    phone: str = ""
    email: str = ""
    categories: list[str] = []
    accreditation: str = ""


class LabSearchResponse(BaseModel):
    labs: list[Lab]
    total: int


# ── Certification ─────────────────────────────────────────────────────────────

class CertStep(BaseModel):
    step_number: int
    title: str
    description: str
    tips: str = ""


class CertificationGuide(BaseModel):
    scheme: str
    description: str = ""
    product_type: str
    steps: list[CertStep]
    estimated_time: str = ""
    documents_required: list[str] = []


# ── Comparison ────────────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    standard_a: str
    standard_b: str


class CompareResponse(BaseModel):
    comparison: ComparisonResult
