import { ApiError } from "@/lib/api";
import { apiRequest } from "@/lib/api-client";
import {
  isMapFeatureCollection,
  type GeocodingPreview,
  type ImportantPlace,
  type MapContextResponse,
  type MapFeatureCollection,
} from "@/lib/map-types";

export type MapListingOptions = {
  profileId?: string;
  bbox?: string;
  minScore?: number;
  favorites?: boolean;
  limit?: number;
};

export async function fetchMapListings(
  options: MapListingOptions = {},
  signal?: AbortSignal,
): Promise<MapFeatureCollection> {
  const params = new URLSearchParams();
  if (options.profileId) params.set("profile_id", options.profileId);
  if (options.bbox) params.set("bbox", options.bbox);
  if (options.minScore !== undefined) {
    params.set("min_score", String(options.minScore));
  }
  if (options.favorites !== undefined) {
    params.set("favorites", String(options.favorites));
  }
  if (options.limit !== undefined) {
    params.set("limit", String(options.limit));
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const payload = await apiRequest<unknown>(`/map/listings/${query}`, {
    signal,
  });
  if (!isMapFeatureCollection(payload)) {
    throw new ApiError(
      "Map API returned an invalid GeoJSON payload",
      502,
      "invalid_geojson",
    );
  }
  return payload;
}

export function fetchImportantPlaces(
  profileId: string,
  signal?: AbortSignal,
): Promise<ImportantPlace[]> {
  return apiRequest<ImportantPlace[]>(
    `/search-profiles/${profileId}/important-places/`,
    { signal },
  );
}

export function previewImportantPlaceGeocode(
  profileId: string,
  address: string,
): Promise<GeocodingPreview> {
  return apiRequest<GeocodingPreview>(
    `/search-profiles/${profileId}/important-places/geocode/`,
    {
      method: "POST",
      body: { address },
    },
  );
}

export type ImportantPlaceInput = {
  name: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  max_distance_km?: number;
  importance?: number;
};

export function createImportantPlace(
  profileId: string,
  payload: ImportantPlaceInput,
): Promise<ImportantPlace> {
  return apiRequest<ImportantPlace>(
    `/search-profiles/${profileId}/important-places/`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export async function deleteImportantPlace(
  profileId: string,
  placeId: string,
): Promise<void> {
  await apiRequest<void>(
    `/search-profiles/${profileId}/important-places/${placeId}/`,
    { method: "DELETE" },
  );
}

export function fetchMapContext(
  profileId: string,
  listingIds: string[],
  signal?: AbortSignal,
): Promise<MapContextResponse> {
  const params = new URLSearchParams();
  if (listingIds.length > 0) {
    params.set("listing_ids", listingIds.join(","));
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  return apiRequest<MapContextResponse>(
    `/search-profiles/${profileId}/map-context/${query}`,
    { signal },
  );
}
