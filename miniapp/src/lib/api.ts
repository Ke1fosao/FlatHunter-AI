import {
  ApiClientError,
  apiRequest,
  setCsrfToken,
} from "@/lib/api-client";

export type HealthResponse = {
  status: "ready" | "degraded";
  service: string;
  checks: Record<string, "ok" | "error">;
};

export type AuthenticatedUser = {
  id: string;
  telegramId: number;
  firstName: string;
  lastName: string;
  username: string;
  locale: string;
  role: string;
};

export type SearchProfileInput = {
  name: string;
  city: string;
  deal_type: "rent" | "buy";
  price_min?: number | null;
  price_max?: number | null;
  currency: string;
  rooms: number[];
  desired_districts: string[];
  excluded_districts: string[];
  occupants: number;
  children: boolean;
  pets: Record<string, boolean>;
  property_types: string[];
  filters: Record<string, unknown>;
  source_text?: string;
  notification_preference: {
    frequency: "instant" | "15m" | "hourly" | "twice_daily" | "daily";
    min_match_score: number;
    max_risk_score: number;
    daily_limit: number;
    quiet_hours_enabled: boolean;
    quiet_hours_start: string;
    quiet_hours_end: string;
    notify_price_changes: boolean;
    notify_reactivated: boolean;
  };
};

export type SearchProfileSummary = {
  id: string;
  name: string;
  city: string;
  is_active: boolean;
};

export type AIMeta = {
  feature?: string;
  provider: string;
  model: string;
  prompt_version?: string;
  status: "success" | "cached" | "fallback" | "disabled";
  latency_ms?: number;
  reason?: string;
  attempts?: number;
  cache_key?: string;
};

export type ParsedSearchResponse = {
  data: Partial<SearchProfileInput>;
  confidence: Record<string, number>;
  missing_fields: string[];
  meta?: AIMeta;
};

export type ListingUserState = {
  is_favorite: boolean;
  is_hidden: boolean;
  is_compared: boolean;
  note: string;
  updated_at: string | null;
};

export type ListingFeedItem = {
  id: string;
  source_name: string;
  source_url: string;
  canonical_url: string;
  title: string;
  description: string;
  deal_type: string;
  property_type: string;
  city: string;
  district: string;
  street: string;
  price_uah: number;
  currency: string;
  rooms: number;
  total_area: string | null;
  floor: number | null;
  floors_total: number | null;
  building_type: string;
  renovation_level: string;
  heating_type: string;
  pets_allowed: boolean | null;
  children_allowed: boolean | null;
  commission_percent: string | null;
  is_owner: boolean | null;
  images: string[];
  attributes: Record<string, unknown>;
  published_at: string;
  is_demo: boolean;
  user_state: ListingUserState;
};

export type ListingFeedResponse = {
  count: number;
  next: string | null;
  previous: string | null;
  results: ListingFeedItem[];
};

export type DashboardResponse = {
  stats: {
    active_profiles: number;
    available_listings: number;
    favorites: number;
    hidden: number;
    compared: number;
  };
  recent: ListingFeedItem[];
};

export type MatchComponent = {
  code: string;
  label: string;
  score: number;
  weight: number;
  status: "strong" | "partial" | "miss" | "unknown";
  explanation: string;
};

export type PersonalizedMatch = {
  listing: ListingFeedItem;
  match: {
    score: number;
    eligible: boolean;
    summary: string;
    strengths: string[];
    compromises: string[];
    unknowns: string[];
    components: MatchComponent[];
  };
};

export type MatchFeedResponse = {
  profile: { id: string; name: string; city: string };
  count: number;
  results: PersonalizedMatch[];
  meta: {
    algorithm: string;
    min_score: number;
    eligible_only: boolean;
    ordering: string;
  };
};

export type AISummaryResponse = {
  summary: string;
  advantages: string[];
  caveats: string[];
  unknowns: string[];
  confidence: Record<string, number>;
  meta: AIMeta;
};

export type AIOwnerQuestionsResponse = {
  questions: string[];
  message: string;
  confidence: Record<string, number>;
  meta: AIMeta;
};

export type AIComparisonRow = {
  id: string;
  title: string;
  city: string;
  district: string;
  price_uah: number;
  price: string;
  rooms: number | null;
  area: string;
  area_value: number;
  floor: string;
  commission: string;
  known_first_payment_uah: number | null;
  pets: string;
  children_allowed: boolean | null;
  building_type: string;
  renovation_level: string;
  heating_type: string;
  backup_power: boolean | null;
  parking: boolean | null;
  match_score: number | null;
  risk_score: number | null;
  travel_minutes: number | null;
  advantages: string[];
  disadvantages: string[];
  unknowns: string[];
};

export type AIComparisonResponse = {
  listings: AIComparisonRow[];
  recommended_listing_id: string | null;
  is_decisive: boolean;
  recommendation: string;
  tradeoffs: string[];
  unknowns: string[];
  confidence: Record<string, number>;
  meta: AIMeta;
};

type PaginatedProfiles = { count: number; results: SearchProfileSummary[] };
type TelegramAuthResponse = { user: AuthenticatedUser; csrfToken: string };

export const TELEGRAM_AUTHENTICATED_EVENT = "flathunter:authenticated";
export { ApiClientError as ApiError };

export function normalizeApiBaseUrl(value: string | undefined): string {
  const candidate = value?.trim();
  if (!candidate) return "/api/v1";
  const normalized = candidate.replace(/\/+$/, "");
  return normalized.length > 0 ? normalized : "/api/v1";
}

export function buildApiUrl(baseUrl: string | undefined, endpoint: string): string {
  const base = normalizeApiBaseUrl(baseUrl);
  const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  return `${base}${path}`;
}

function getJson<T>(endpoint: string, signal?: AbortSignal): Promise<T> {
  return apiRequest<T>(endpoint, { signal });
}

function postJson<T>(endpoint: string, body: unknown): Promise<T> {
  return apiRequest<T>(endpoint, { method: "POST", body });
}

export async function fetchBackendHealth(
  signal?: AbortSignal,
): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health/", signal);
}

export async function authenticateTelegram(
  initData: string,
  signal?: AbortSignal,
): Promise<TelegramAuthResponse> {
  const payload = await apiRequest<TelegramAuthResponse>("/auth/telegram/", {
    method: "POST",
    body: { initData },
    signal,
  });
  setCsrfToken(payload.csrfToken);
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(TELEGRAM_AUTHENTICATED_EVENT));
  }
  return payload;
}

export async function parseNaturalLanguageSearch(
  text: string,
): Promise<ParsedSearchResponse> {
  return postJson<ParsedSearchResponse>(
    "/search-profiles/parse-natural-language/",
    { text },
  );
}

export async function createSearchProfile(
  payload: SearchProfileInput,
): Promise<{ id: string }> {
  return postJson<{ id: string }>("/search-profiles/", payload);
}

export async function fetchSearchProfiles(
  signal?: AbortSignal,
): Promise<SearchProfileSummary[]> {
  const payload = await getJson<PaginatedProfiles | SearchProfileSummary[]>(
    "/search-profiles/",
    signal,
  );
  return Array.isArray(payload) ? payload : payload.results;
}

export async function fetchMatches(
  profileId: string,
  options: { minScore?: number; ordering?: string } = {},
  signal?: AbortSignal,
): Promise<MatchFeedResponse> {
  const params = new URLSearchParams({
    min_score: String(options.minScore ?? 0),
    ordering: options.ordering ?? "-match_score",
  });
  return getJson<MatchFeedResponse>(
    `/search-profiles/${profileId}/matches/?${params.toString()}`,
    signal,
  );
}

export async function fetchListings(
  filters: Record<string, string | number | boolean | undefined> = {},
  signal?: AbortSignal,
): Promise<ListingFeedResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const query = params.size > 0 ? `?${params.toString()}` : "";
  return getJson<ListingFeedResponse>(`/listings/${query}`, signal);
}

export async function fetchListing(
  id: string,
  signal?: AbortSignal,
): Promise<ListingFeedItem> {
  return getJson<ListingFeedItem>(`/listings/${id}/`, signal);
}

export async function fetchDashboard(
  signal?: AbortSignal,
): Promise<DashboardResponse> {
  return getJson<DashboardResponse>("/listings/dashboard/", signal);
}

export async function setListingState(
  id: string,
  action: "favorite" | "hide" | "compare",
  value: boolean,
): Promise<ListingFeedItem> {
  return postJson<ListingFeedItem>(`/listings/${id}/${action}/`, { value });
}

export async function summarizeListingWithAI(
  id: string,
): Promise<AISummaryResponse> {
  return postJson<AISummaryResponse>(`/ai/listings/${id}/summary/`, {});
}

export async function generateOwnerQuestionsWithAI(
  id: string,
  searchProfileId?: string,
): Promise<AIOwnerQuestionsResponse> {
  return postJson<AIOwnerQuestionsResponse>(
    `/ai/listings/${id}/owner-questions/`,
    {
      ...(searchProfileId ? { search_profile_id: searchProfileId } : {}),
    },
  );
}

export async function compareListingsWithAI(
  listingIds: string[],
  searchProfileId?: string,
): Promise<AIComparisonResponse> {
  return postJson<AIComparisonResponse>("/ai/listings/compare/", {
    listing_ids: listingIds,
    ...(searchProfileId ? { search_profile_id: searchProfileId } : {}),
  });
}
