import {
  ApiError,
  buildApiUrl,
  fetchListings,
  fetchMatches,
  type ListingFeedItem,
  type ListingUserState,
  type MatchComponent,
  type SearchProfileSummary
} from "@/lib/api";

export type ClusterListing = Omit<ListingFeedItem, "floors_total"> & {
  floors_total: string | null;
  cluster_id: string | null;
  source_count: number;
  member_count: number;
  is_cluster_primary: boolean;
  price_min_uah: number;
  price_max_uah: number;
};

export type ClusterMember = {
  role: "primary" | "duplicate";
  confidence: string;
  joined_by: "auto" | "manual" | "exact";
  reasons: string[];
  listing: ClusterListing;
};

export type ClusterMatch = {
  score: number;
  eligible: boolean;
  summary: string;
  strengths: string[];
  compromises: string[];
  unknowns: string[];
  components: MatchComponent[];
};

export type ListingClusterDetail = {
  id: string;
  status: "active" | "split" | "archived";
  primary: ClusterListing;
  member_count: number;
  source_count: number;
  confidence_min: string | null;
  confidence_max: string | null;
  price_min_uah: number | null;
  price_max_uah: number | null;
  members: ClusterMember[];
  user_state: ListingUserState;
  match: ClusterMatch | null;
  algorithm_version: number;
  created_at: string;
  updated_at: string;
};

export type ClusterFeedItem = {
  listing: ClusterListing;
  match: ClusterMatch | null;
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

export function sourceLabel(count: number): string {
  const absolute = Math.abs(count);
  const lastTwo = absolute % 100;
  const last = absolute % 10;
  if (lastTwo >= 11 && lastTwo <= 14) return `${String(count)} джерел`;
  if (last === 1) return `${String(count)} джерело`;
  if (last >= 2 && last <= 4) return `${String(count)} джерела`;
  return `${String(count)} джерел`;
}

export function formatClusterPriceRange(minimum: number, maximum: number): string {
  const format = new Intl.NumberFormat("uk-UA");
  if (minimum === maximum) return `${format.format(minimum)} грн`;
  return `${format.format(minimum)}–${format.format(maximum)} грн`;
}

export async function fetchClusterFeed(
  profile: SearchProfileSummary | null,
  minScore: number,
  signal?: AbortSignal
): Promise<ClusterFeedItem[]> {
  if (profile !== null) {
    const response = await fetchMatches(profile.id, { minScore, ordering: "-match_score" }, signal);
    return response.results.map((item) => ({
      listing: item.listing as ClusterListing,
      match: item.match
    }));
  }
  const response = await fetchListings({}, signal);
  return response.results.map((listing) => ({
    listing: listing as ClusterListing,
    match: null
  }));
}

export async function fetchListingCluster(
  clusterId: string,
  profileId?: string,
  signal?: AbortSignal
): Promise<ListingClusterDetail> {
  const params = new URLSearchParams();
  if (profileId) params.set("profile_id", profileId);
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(buildApiUrl(apiBaseUrl, `/listing-clusters/${clusterId}/${suffix}`), {
    credentials: "include",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal
  });
  return parseResponse<ListingClusterDetail>(response);
}

export async function setClusterState(
  clusterId: string,
  values: Partial<Pick<ListingUserState, "is_favorite" | "is_hidden" | "is_compared" | "note">>
): Promise<ListingClusterDetail> {
  const response = await fetch(buildApiUrl(apiBaseUrl, `/listing-clusters/${clusterId}/state/`), {
    method: "PATCH",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken()
    },
    body: JSON.stringify(values)
  });
  return parseResponse<ListingClusterDetail>(response);
}
