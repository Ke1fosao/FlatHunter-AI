import { ApiError, buildApiUrl } from "@/lib/api";
import {
  isMapFeatureCollection,
  type GeocodingPreview,
  type ImportantPlace,
  type MapContextResponse,
  type MapFeatureCollection
} from "@/lib/map-types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

type ErrorPayload = { error?: { code?: string; message?: string } };

function csrfToken(): string {
  if (typeof document === "undefined") return "";
  return document.cookie.split("; ").find((row) => row.startsWith("csrftoken="))?.split("=")[1] ?? "";
}

async function parseJson<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => ({}))) as T & ErrorPayload;
  if (!response.ok) {
    throw new ApiError(
      payload.error?.message ?? `API request failed with status ${String(response.status)}`,
      response.status,
      payload.error?.code
    );
  }
  return payload;
}

export type MapListingOptions = {
  profileId?: string;
  bbox?: string;
  minScore?: number;
  favorites?: boolean;
  limit?: number;
};

export async function fetchMapListings(
  options: MapListingOptions = {},
  signal?: AbortSignal
): Promise<MapFeatureCollection> {
  const params = new URLSearchParams();
  if (options.profileId) params.set("profile_id", options.profileId);
  if (options.bbox) params.set("bbox", options.bbox);
  if (options.minScore !== undefined) params.set("min_score", String(options.minScore));
  if (options.favorites !== undefined) params.set("favorites", String(options.favorites));
  if (options.limit !== undefined) params.set("limit", String(options.limit));
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(buildApiUrl(apiBaseUrl, `/map/listings/${query}`), {
    credentials: "include",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal
  });
  const payload = await parseJson<unknown>(response);
  if (!isMapFeatureCollection(payload)) {
    throw new ApiError("Map API returned an invalid GeoJSON payload", 502, "invalid_geojson");
  }
  return payload;
}

export async function fetchImportantPlaces(
  profileId: string,
  signal?: AbortSignal
): Promise<ImportantPlace[]> {
  const response = await fetch(
    buildApiUrl(apiBaseUrl, `/search-profiles/${profileId}/important-places/`),
    { credentials: "include", headers: { Accept: "application/json" }, cache: "no-store", signal }
  );
  return parseJson<ImportantPlace[]>(response);
}

export async function previewImportantPlaceGeocode(
  profileId: string,
  address: string
): Promise<GeocodingPreview> {
  const response = await fetch(
    buildApiUrl(apiBaseUrl, `/search-profiles/${profileId}/important-places/geocode/`),
    {
      method: "POST",
      credentials: "include",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken()
      },
      body: JSON.stringify({ address })
    }
  );
  return parseJson<GeocodingPreview>(response);
}

export type ImportantPlaceInput = {
  name: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  max_distance_km?: number;
  importance?: number;
};

export async function createImportantPlace(
  profileId: string,
  payload: ImportantPlaceInput
): Promise<ImportantPlace> {
  const response = await fetch(
    buildApiUrl(apiBaseUrl, `/search-profiles/${profileId}/important-places/`),
    {
      method: "POST",
      credentials: "include",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken()
      },
      body: JSON.stringify(payload)
    }
  );
  return parseJson<ImportantPlace>(response);
}

export async function deleteImportantPlace(profileId: string, placeId: string): Promise<void> {
  const response = await fetch(
    buildApiUrl(apiBaseUrl, `/search-profiles/${profileId}/important-places/${placeId}/`),
    {
      method: "DELETE",
      credentials: "include",
      headers: { Accept: "application/json", "X-CSRFToken": csrfToken() }
    }
  );
  if (!response.ok) await parseJson<unknown>(response);
}

export async function fetchMapContext(
  profileId: string,
  listingIds: string[],
  signal?: AbortSignal
): Promise<MapContextResponse> {
  const params = new URLSearchParams();
  if (listingIds.length > 0) params.set("listing_ids", listingIds.join(","));
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(
    buildApiUrl(apiBaseUrl, `/search-profiles/${profileId}/map-context/${query}`),
    { credentials: "include", headers: { Accept: "application/json" }, cache: "no-store", signal }
  );
  return parseJson<MapContextResponse>(response);
}
