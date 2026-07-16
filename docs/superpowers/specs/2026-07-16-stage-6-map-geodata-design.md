# Stage 6 — Map and Geodata Design

## Goal

Add a real geospatial layer to FlatHunter AI: PostGIS-backed coordinates, safe geocoding, user-scoped map data, apartment markers, important places, and distance context inside the Telegram Mini App.

## Chosen approach

Use **GeoDjango + PostGIS + Leaflet**.

Alternatives considered:

1. Decimal coordinates with Python distance calculations — simpler, but not true PostGIS and scales poorly.
2. MapLibre/vector tiles — powerful, but unnecessary for the current synthetic dataset and heavier to operate.
3. Google Maps SDK — polished, but requires a paid key and creates vendor lock-in.

Leaflet with configurable tile URLs keeps the demo usable without a mandatory commercial API, while GeoDjango provides proper spatial queries and future-proofs the backend.

## Backend architecture

### Geometry

- Add `django.contrib.gis` to Django apps.
- Use the PostGIS database backend for PostgreSQL URLs.
- Add `location = PointField(srid=4326, geography=True)` to `Listing` and `ImportantPlace`.
- Keep existing decimal latitude/longitude fields during Stage 6 for API compatibility and deterministic demo generation.
- Synchronize decimal coordinates and geometry through focused model/service helpers.

### Geocoding

Create `apps.geodata` with:

- `GeocodingProvider` protocol;
- `DemoGeocodingProvider` as the deterministic default;
- optional `NominatimGeocodingProvider`, disabled unless explicitly configured;
- normalized `GeocodingResult` values;
- backend-only provider selection;
- strict timeout, fixed host, rate limiting, cache, and user-agent for external requests;
- no user-controlled provider URL.

The demo provider recognizes Ukrainian city centres and generates deterministic offsets for synthetic addresses. CI never depends on the internet.

### Spatial services

- Convert coordinates to `Point` consistently as longitude/latitude.
- Validate bounding boxes.
- Query listings inside a bounding box with PostGIS.
- Compute straight-line distances from listings to important places using PostGIS geography distance.
- Return compact GeoJSON features for map rendering.

### API

Add authenticated, user-scoped endpoints:

- `GET /api/v1/map/listings/`
  - accepts `profile_id`, `bbox`, `min_score`, `favorites`, and `limit`;
  - returns a GeoJSON `FeatureCollection`;
  - includes listing summary, user state, and optional deterministic Match Score.
- `GET /api/v1/search-profiles/{id}/important-places/`
- `POST /api/v1/search-profiles/{id}/important-places/`
- `DELETE /api/v1/search-profiles/{id}/important-places/{place_id}/`
- `POST /api/v1/search-profiles/{id}/important-places/geocode/`
  - previews a normalized geocoding result without persisting it.
- `GET /api/v1/search-profiles/{id}/map-context/`
  - returns profile places and nearest-distance context for visible listings.

Ownership is enforced from the authenticated user; clients cannot request another user’s profile or places.

## Mini App architecture

- Add a `map` workspace tab.
- Use Leaflet through a client-only dynamic import so Next.js SSR remains stable.
- Render apartment markers and important-place markers with distinct accessible icons.
- Support marker selection, compact popup data, and opening the existing listing details panel.
- Add a mobile bottom sheet for:
  - active profile selection;
  - map/list synchronization;
  - important-place list;
  - adding a place by address;
  - adding a place by map click;
  - deleting a place;
  - showing straight-line distance constraints.
- Respect Telegram safe areas, dark/light theme variables, and touch targets.
- Tile URL and attribution are configurable through public environment variables.

## Error handling

- Invalid bbox, coordinates, profile IDs, or distance limits return structured `400` errors.
- Unauthorized profile access returns `404` to avoid information disclosure.
- Geocoding timeouts return a stable provider-unavailable response.
- Empty maps show a useful state rather than a blank canvas.
- The UI keeps the previous valid map state when a refresh fails.

## Security and legal constraints

- External geocoding is opt-in and disabled by default.
- Nominatim uses a fixed official host, explicit user-agent, cache, and rate limiting.
- Tile attribution is always displayed.
- No secrets are exposed to the frontend.
- No arbitrary URL fetching is accepted from API clients.
- All map and important-place data is scoped to the authenticated user.

## Testing strategy

Backend tests cover:

- geometry synchronization;
- deterministic demo geocoding;
- provider selection and disabled external provider;
- bbox validation and PostGIS filtering;
- GeoJSON shape;
- profile ownership;
- important-place CRUD;
- geocoding preview;
- distance annotations;
- Match Score integration.

Frontend tests cover:

- API URL construction and map payload parsing;
- map empty/error/auth states;
- profile and important-place interactions;
- marker selection callbacks;
- accessible controls.

CI must pass Ruff, mypy, migrations, pytest, dependency audits, ESLint, TypeScript, frontend tests/build, Docker builds, and Gitleaks.

## Scope boundary

Stage 6 implements straight-line PostGIS distance only. Travel-time routing, isochrones, clustering across duplicate listings, and market/risk analysis belong to later stages.
