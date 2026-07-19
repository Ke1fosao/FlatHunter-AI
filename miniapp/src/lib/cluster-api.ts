import {
  fetchListings,
  fetchMatches,
  type ListingFeedItem,
  type ListingUserState,
  type MatchComponent,
  type SearchProfileSummary,
} from "@/lib/api";
import { apiRequest } from "@/lib/api-client";

export type ClusterListing = ListingFeedItem & {
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

export function sourceLabel(count: number): string {
  const absolute = Math.abs(count);
  const lastTwo = absolute % 100;
  const last = absolute % 10;
  if (lastTwo >= 11 && lastTwo <= 14) return `${String(count)} джерел`;
  if (last === 1) return `${String(count)} джерело`;
  if (last >= 2 && last <= 4) return `${String(count)} джерела`;
  return `${String(count)} джерел`;
}

export function formatClusterPriceRange(
  minimum: number,
  maximum: number,
): string {
  const numberFormat = new Intl.NumberFormat("uk-UA");
  const format = (value: number) =>
    numberFormat
      .format(value)
      .replaceAll("\u00A0", " ")
      .replaceAll("\u202F", " ");
  if (minimum === maximum) return `${format(minimum)} грн`;
  return `${format(minimum)}–${format(maximum)} грн`;
}

export async function fetchClusterFeed(
  profile: SearchProfileSummary | null,
  minScore: number,
  signal?: AbortSignal,
): Promise<ClusterFeedItem[]> {
  if (profile !== null) {
    const response = await fetchMatches(
      profile.id,
      { minScore, ordering: "-match_score" },
      signal,
    );
    return response.results.map((item) => ({
      listing: item.listing as ClusterListing,
      match: item.match,
    }));
  }
  const response = await fetchListings({}, signal);
  return response.results.map((listing) => ({
    listing: listing as ClusterListing,
    match: null,
  }));
}

export function fetchListingCluster(
  clusterId: string,
  profileId?: string,
  signal?: AbortSignal,
): Promise<ListingClusterDetail> {
  const params = new URLSearchParams();
  if (profileId) params.set("profile_id", profileId);
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return apiRequest<ListingClusterDetail>(
    `/listing-clusters/${clusterId}/${suffix}`,
    { signal },
  );
}

export function setClusterState(
  clusterId: string,
  values: Partial<
    Pick<
      ListingUserState,
      "is_favorite" | "is_hidden" | "is_compared" | "note"
    >
  >,
): Promise<ListingClusterDetail> {
  return apiRequest<ListingClusterDetail>(
    `/listing-clusters/${clusterId}/state/`,
    {
      method: "PATCH",
      body: values,
    },
  );
}
