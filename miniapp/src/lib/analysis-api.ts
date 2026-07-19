import { apiRequest } from "@/lib/api-client";

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
  severity: string;
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

export function fetchPriceHistory(
  listingId: string,
  signal?: AbortSignal,
): Promise<PriceHistoryResponse> {
  return apiRequest<PriceHistoryResponse>(
    `/listings/${listingId}/price-history/`,
    { signal },
  );
}

export function fetchMarketAnalysis(
  listingId: string,
  signal?: AbortSignal,
): Promise<MarketAnalysisResponse> {
  return apiRequest<MarketAnalysisResponse>(
    `/listings/${listingId}/market-analysis/`,
    { signal },
  );
}

export function fetchRiskAnalysis(
  listingId: string,
  signal?: AbortSignal,
): Promise<RiskAnalysisResponse> {
  return apiRequest<RiskAnalysisResponse>(
    `/listings/${listingId}/risk-analysis/`,
    { signal },
  );
}

export function refreshListingAnalysis(
  listingId: string,
  idempotencyKey = `manual-${listingId}`,
): Promise<AnalysisRefreshResponse> {
  return apiRequest<AnalysisRefreshResponse>(
    `/listings/${listingId}/analysis/refresh/`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: { force: true },
    },
  );
}
