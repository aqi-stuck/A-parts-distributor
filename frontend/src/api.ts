export const API_BASE = "http://127.0.0.1:8000";

export type SearchResult = {
  sku: string;
  description: string;
  score: number;
  confidence: number;
  evidence: string[];
};

export type TimingMs = {
  engine: number;
  routing: number;
  total: number;
};

export type SearchResponse = {
  route: "auto" | "review";
  reason: string | null;
  results: SearchResult[];
  latency_ms: number;
  timing_ms: TimingMs;
};

export type ReviewItem = {
  query: string;
  top_sku: string | null;
  latency_ms: number;
  created_at: string;
};

export type Metrics = {
  total_queries: number;
  review_count: number;
  avg_latency_ms: number;
};

async function handle(res: Response) {
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

export async function search(query: string): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  return handle(res);
}

export async function feedback(query: string, sku: string, decision: "approve" | "reject"): Promise<void> {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, sku, decision, reviewer: null }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

export async function reviewQueue(): Promise<ReviewItem[]> {
  const res = await fetch(`${API_BASE}/review-queue`);
  return handle(res);
}

export async function metrics(): Promise<Metrics> {
  const res = await fetch(`${API_BASE}/metrics`);
  return handle(res);
}
