import { ApiError, buildApiUrl } from "@/lib/api";

export type AnalysisStatus =
  | "pending"
  | "ready"
  | "insufficient_data"
  | "stale"
  | "failed"
  | "disabled";

export type ConfidenceLabel = "none" | "low" | "medium" | "high";
export type RiskLevel = "low" | "review" | "elevated" | "insufficient_data";

export type PriceChangeSummary = {
  previous_price_uah: number;
  new_price_uah: number;
  change_amount_uah: number;
  change_percent: string;
  direction: "increase" | "decrease";
  changed_at: string;
};

export type AnalysisSummary = {
  market: {
    status: AnalysisStatus;
    median_price_uah?: number | null;
    q1_price_uah?: number | null;
    q3_price_uah?: number | null;
    deviation_percent?: string | null;
    comparable_count?: number;
    confidence_label?: ConfidenceLabel;
    calculated_at?: string;
  };
  risk: {
    status: AnalysisStatus;
    score?: number;
    level?: RiskLevel;
    summary?: string;
    calculated_at?: string;
  };
  latest_price_change: PriceChangeSummary | null;
};

export type PriceHistoryEvent = PriceChangeSummary & {
  id: string;
  detected_at: string;
};

export type PriceHistoryResponse = {
  listing_id: string;
  current_price_uah: number;
  events: PriceHistoryEvent[];
};

export type MarketAssessment = {
  id: string;
  status: Exclude<AnalysisStatus, "pending">;
  provider: string;
  algorithm_version: string;
  median_price_uah: number | null;
  q1_price_uah: number | null;
  q3_price_uah: number | null;
  median_price_per_sqm: string | null;
  target_price_per_sqm: string | null;
  deviation_percent: string | null;
  comparable_count: number;
  confidence_score: string;
  confidence_label: ConfidenceLabel;
  selection_summary: Record<string, unknown>;
  explanation: string;
  calculated_at: string;
  valid_until: string | null;
  is_stale: boolean;
};

export type MarketAnalysisResponse = {
  listing_id: string;
  current_price_uah: number;
  assessment: MarketAssessment;
};

export type RiskSignal = {
  code: string;
  weight: number;
  severity: "low" | "medium" | "high" | "protective" | string;
  evidence: Record<string, unknown>;
  label: string;
  recommendation: string;
};

export type RiskAssessment = {
  id: string;
  status: Exclude<AnalysisStatus, "pending">;
  score: number;
  level: RiskLevel;
  signals: RiskSignal[];
  protective_signals: RiskSignal[];
  summary: string;
  safety_advice: string;
  algorithm_version: string;
  calculated_at: string;
  valid_until: string | null;
  is_stale: boolean;
};

export type RiskAnalysisResponse = {
  listing_id: string;
  assessment: RiskAssessment;
  disclaimer: string;
};

export type AnalysisRefreshResponse = {
  listing_id: string;
  market: MarketAssessment;
  risk: RiskAssessment;
};

type ApiErrorPayload = { error?: { code?: string; message?: string } };

function csrfToken(): string {
  if (typeof document === "undefined") return "";
  return document.cookie.split("; ").find((row) => row.startsWith("csrftoken="))?.split("=")[1] ?? "";
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => ({}))) as T & ApiErrorPayload;
  if (!response.ok) {
    throw new ApiError(
      payload.error?.message ?? `API request failed with status ${String(response.status)}`,
      response.status,
      payload.error?.code
    );
  }
  return payload;
}

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

function getJson<T>(endpoint: string, signal?: AbortSignal): Promise<T> {
  return fetch(buildApiUrl(apiBaseUrl, endpoint), {
    credentials: "include",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal
  }).then(parseResponse<T>);
}

export function fetchPriceHistory(listingId: string, signal?: AbortSignal): Promise<PriceHistoryResponse> {
  return getJson<PriceHistoryResponse>(`/listings/${listingId}/price-history/`, signal);
}

export function fetchMarketAnalysis(listingId: string, signal?: AbortSignal): Promise<MarketAnalysisResponse> {
  return getJson<MarketAnalysisResponse>(`/listings/${listingId}/market-analysis/`, signal);
}

export function fetchRiskAnalysis(listingId: string, signal?: AbortSignal): Promise<RiskAnalysisResponse> {
  return getJson<RiskAnalysisResponse>(`/listings/${listingId}/risk-analysis/`, signal);
}

export async function refreshListingAnalysis(
  listingId: string,
  idempotencyKey = `manual-${listingId}`
): Promise<AnalysisRefreshResponse> {
  const response = await fetch(buildApiUrl(apiBaseUrl, `/listings/${listingId}/analysis/refresh/`), {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken(),
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ force: true })
  });
  return parseResponse<AnalysisRefreshResponse>(response);
}
