/**
 * API client — typed functions for every backend endpoint.
 */

const API_BASE = "/api";

export interface Source {
  document: string;
  clause: string;
  excerpt: string;
}

export interface CorrectionInfo {
  original_word: string;
  corrected_word: string;
  confidence: number;
  suggestions: string[];
}

export interface ProductInfo {
  name: string;
  is_codes: string[];
  category: string;
  certification: string;
  certification_scheme: string;
  description: string;
  products_covered: string[];
  key_tests: string[];
  documents_required: string[];
  related_standards: string[];
  key_requirements: string[];
  validity: string;
}

export interface ComparisonResult {
  standard_a: string;
  standard_b: string;
  name_a: string;
  name_b: string;
  purpose: string[];
  applies_to: string[];
  certification: string[];
  tests_count: number[];
  products: string[][];
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  mode: string;
  correction?: CorrectionInfo | null;
  confidence?: number | null;
  product_info?: ProductInfo | null;
  related_questions: string[];
  comparison?: ComparisonResult | null;
  follow_ups: string[];
}

export interface StandardRecommendation {
  is_number: string;
  title: string;
  relevance_score: number;
  explanation: string;
}

export interface RecommendResponse {
  recommendations: StandardRecommendation[];
  query: string;
}

export interface Lab {
  name: string;
  address: string;
  city: string;
  state: string;
  phone: string;
  email: string;
  categories: string[];
  accreditation: string;
}

export interface LabSearchResponse {
  labs: Lab[];
  total: number;
}

export type ChatMode = "general" | "recommend" | "certify" | "hallmark" | "lab";

/**
 * Send a chat message to the backend.
 */
export async function sendChatMessage(
  message: string,
  language: string = "en",
  mode: ChatMode = "general",
  history: { role: string; content: string }[] = []
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, language, mode, history }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Chat API error: ${res.status} — ${err}`);
  }
  return res.json();
}

/**
 * Get standard recommendations for a product description.
 */
export async function getRecommendations(
  productDescription: string,
  language: string = "en"
): Promise<RecommendResponse> {
  const res = await fetch(`${API_BASE}/standards/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_description: productDescription, language }),
  });
  if (!res.ok) throw new Error(`Recommend API error: ${res.status}`);
  return res.json();
}

/**
 * Search BIS-recognized labs.
 */
export async function searchLabs(
  category: string = "",
  city: string = "",
  state: string = ""
): Promise<LabSearchResponse> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (city) params.set("city", city);
  if (state) params.set("state", state);
  const res = await fetch(`${API_BASE}/labs?${params.toString()}`);
  if (!res.ok) throw new Error(`Labs API error: ${res.status}`);
  return res.json();
}

/**
 * Compare two IS standards.
 */
export async function compareStandards(
  standardA: string,
  standardB: string
): Promise<{ comparison: ComparisonResult }> {
  const res = await fetch(`${API_BASE}/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ standard_a: standardA, standard_b: standardB }),
  });
  if (!res.ok) throw new Error(`Compare API error: ${res.status}`);
  return res.json();
}
