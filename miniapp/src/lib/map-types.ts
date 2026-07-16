export type MapUserState = {
  is_favorite: boolean;
  is_hidden: boolean;
  is_compared: boolean;
};

export type MapMatch = {
  score: number;
  eligible: boolean;
  summary: string;
  strengths: string[];
  compromises: string[];
  unknowns: string[];
};

export type MapListingProperties = {
  id: string;
  title: string;
  price_uah: number;
  rooms: number;
  total_area: string | null;
  city: string;
  district: string;
  street: string;
  is_demo: boolean;
  published_at: string;
  user_state: MapUserState;
  match: MapMatch | null;
};

export type MapPointFeature = {
  type: "Feature";
  id: string;
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: MapListingProperties;
};

export type MapFeatureCollection = {
  type: "FeatureCollection";
  features: MapPointFeature[];
  meta: {
    returned: number;
    inspected: number;
    profile_id: string | null;
    tiles_url?: string | null;
    attribution?: string | null;
  };
};

export type ImportantPlace = {
  id: string;
  name: string;
  address: string;
  latitude: string | null;
  longitude: string | null;
  geocoding_provider: string;
  geocoding_confidence: string | null;
  max_distance_km: string | null;
  max_walk_minutes: number | null;
  max_drive_minutes: number | null;
  max_transit_minutes: number | null;
  importance: number;
  created_at: string;
};

export type GeocodingPreview = {
  latitude: number;
  longitude: number;
  display_name: string;
  provider: string;
  confidence: number;
  country_code: string;
};

export type MapContextResponse = {
  profile: { id: string; name: string; city: string };
  places: ImportantPlace[];
  distances: Record<
    string,
    { place_id: string; name: string; distance_km: number | null; max_distance_km: number | null }[]
  >;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isMapFeatureCollection(value: unknown): value is MapFeatureCollection {
  if (!isRecord(value) || value.type !== "FeatureCollection" || !Array.isArray(value.features)) return false;
  return value.features.every((feature) => {
    if (!isRecord(feature) || feature.type !== "Feature") return false;
    const geometry = feature.geometry;
    const properties = feature.properties;
    if (!isRecord(geometry) || geometry.type !== "Point" || !Array.isArray(geometry.coordinates)) return false;
    if (geometry.coordinates.length !== 2 || !geometry.coordinates.every((item) => typeof item === "number")) return false;
    return isRecord(properties) && typeof properties.id === "string" && typeof properties.title === "string";
  });
}
