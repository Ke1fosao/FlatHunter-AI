"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ImportantPlacePanel } from "@/components/important-place-panel";
import { LeafletMap } from "@/components/leaflet-map";
import {
  ApiError,
  fetchListing,
  fetchSearchProfiles,
  setListingState,
  TELEGRAM_AUTHENTICATED_EVENT,
  type ListingFeedItem,
  type SearchProfileSummary
} from "@/lib/api";
import { fetchImportantPlaces, fetchMapContext, fetchMapListings } from "@/lib/map-api";
import type { ImportantPlace, MapContextResponse, MapFeatureCollection } from "@/lib/map-types";

type DraftPoint = { latitude: number; longitude: number } | null;

function formatPrice(value: number): string {
  return `${new Intl.NumberFormat("uk-UA").format(value)} грн`;
}

function ListingMapSheet({
  listing,
  context,
  onClose,
  onState
}: {
  listing: ListingFeedItem;
  context: MapContextResponse | null;
  onClose: () => void;
  onState: (action: "favorite" | "compare", value: boolean) => void;
}) {
  const distances = context?.distances[listing.id] ?? [];
  return (
    <aside className="map-listing-sheet" role="dialog" aria-modal="false" aria-label="Квартира на карті">
      <button type="button" className="map-listing-sheet__close" onClick={onClose}>×</button>
      <span>{listing.city} · {listing.district || "район не вказано"}</span>
      <h3>{listing.title}</h3>
      <strong>{formatPrice(listing.price_uah)}</strong>
      <p>{listing.rooms} кімн. · {listing.total_area ? `${listing.total_area} м²` : "площа не вказана"}</p>
      {distances.length > 0 && (
        <div className="map-listing-sheet__distances">
          {distances.map((item) => (
            <div key={item.place_id}>
              <span>◆ {item.name}</span>
              <strong>{item.distance_km === null ? "—" : `${item.distance_km.toFixed(2)} км`}</strong>
              {item.max_distance_km !== null && <small>ліміт {item.max_distance_km} км</small>}
            </div>
          ))}
        </div>
      )}
      <div className="map-listing-sheet__actions">
        <button type="button" className={listing.user_state.is_favorite ? "is-active" : ""} onClick={() => { onState("favorite", !listing.user_state.is_favorite); }}>
          {listing.user_state.is_favorite ? "★ В обраному" : "☆ В обране"}
        </button>
        <button type="button" className={listing.user_state.is_compared ? "is-active" : ""} onClick={() => { onState("compare", !listing.user_state.is_compared); }}>
          {listing.user_state.is_compared ? "✓ Порівнюється" : "⇄ Порівняти"}
        </button>
      </div>
      <a href={listing.source_url} target="_blank" rel="noreferrer">Відкрити першоджерело ↗</a>
    </aside>
  );
}

export function MapWorkspace() {
  const [profiles, setProfiles] = useState<SearchProfileSummary[]>([]);
  const [profileId, setProfileId] = useState("");
  const [collection, setCollection] = useState<MapFeatureCollection>({
    type: "FeatureCollection",
    features: [],
    meta: { returned: 0, inspected: 0, profile_id: null }
  });
  const [places, setPlaces] = useState<ImportantPlace[]>([]);
  const [detail, setDetail] = useState<ListingFeedItem | null>(null);
  const [context, setContext] = useState<MapContextResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draftPoint, setDraftPoint] = useState<DraftPoint>(null);
  const [minScore, setMinScore] = useState("50");
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const activeProfile = useMemo(
    () => profiles.find((profile) => profile.id === profileId) ?? null,
    [profileId, profiles]
  );

  const loadProfiles = useCallback(async (signal?: AbortSignal) => {
    const result = (await fetchSearchProfiles(signal)).filter((profile) => profile.is_active);
    setProfiles(result);
    setProfileId((current) => current || result[0]?.id || "");
    return result;
  }, []);

  const loadMap = useCallback(async (selectedProfile: string, signal?: AbortSignal) => {
    if (!selectedProfile) {
      setCollection({ type: "FeatureCollection", features: [], meta: { returned: 0, inspected: 0, profile_id: null } });
      setPlaces([]);
      return;
    }
    const [mapData, importantPlaces] = await Promise.all([
      fetchMapListings(
        {
          profileId: selectedProfile,
          minScore: Number(minScore),
          favorites: favoritesOnly ? true : undefined,
          limit: 500
        },
        signal
      ),
      fetchImportantPlaces(selectedProfile, signal)
    ]);
    setCollection(mapData);
    setPlaces(importantPlaces);
  }, [favoritesOnly, minScore]);

  const reload = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setMessage("");
    try {
      let targetProfile = profileId;
      if (!targetProfile) {
        const available = await loadProfiles(signal);
        targetProfile = available[0]?.id ?? "";
      }
      await loadMap(targetProfile, signal);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        setMessage(error instanceof ApiError ? error.message : "Не вдалося завантажити карту.");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [loadMap, loadProfiles, profileId]);

  useEffect(() => {
    const controller = new AbortController();
    void reload(controller.signal);
    const authenticated = () => { void reload(); };
    window.addEventListener(TELEGRAM_AUTHENTICATED_EVENT, authenticated);
    return () => {
      controller.abort();
      window.removeEventListener(TELEGRAM_AUTHENTICATED_EVENT, authenticated);
    };
  }, [reload]);

  useEffect(() => {
    if (profileId) void loadMap(profileId).catch((error: unknown) => {
      setMessage(error instanceof ApiError ? error.message : "Не вдалося оновити карту.");
    });
  }, [loadMap, profileId]);

  const selectListing = useCallback(async (id: string) => {
    setSelectedId(id);
    setMessage("");
    try {
      const [listing, mapContext] = await Promise.all([
        fetchListing(id),
        profileId ? fetchMapContext(profileId, [id]) : Promise.resolve(null)
      ]);
      setDetail(listing);
      setContext(mapContext);
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Не вдалося відкрити квартиру.");
    }
  }, [profileId]);

  const updateState = useCallback(async (action: "favorite" | "compare", value: boolean) => {
    if (!detail) return;
    try {
      const updated = await setListingState(detail.id, action, value);
      setDetail(updated);
      await loadMap(profileId);
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Не вдалося оновити стан квартири.");
    }
  }, [detail, loadMap, profileId]);

  return (
    <main className="map-workspace">
      <header className="map-workspace__toolbar">
        <div>
          <span>POSTGIS MAP</span>
          <h2>Квартири на карті</h2>
          <p>Маркери, Match Score і відстані до важливих місць.</p>
        </div>
        <div className="map-workspace__filters">
          <label>
            Пошук
            <select value={profileId} onChange={(event) => { setProfileId(event.target.value); setDetail(null); setSelectedId(null); }}>
              {profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name} · {profile.city}</option>)}
            </select>
          </label>
          <label>
            Match від
            <select value={minScore} onChange={(event) => { setMinScore(event.target.value); }}>
              <option value="0">0%</option><option value="50">50%</option><option value="70">70%</option><option value="80">80%</option><option value="90">90%</option>
            </select>
          </label>
          <label className="map-workspace__check">
            <input type="checkbox" checked={favoritesOnly} onChange={(event) => { setFavoritesOnly(event.target.checked); }} />
            Лише обране
          </label>
          <button type="button" onClick={() => { void reload(); }}>Оновити</button>
        </div>
      </header>

      {!activeProfile && !loading && <div className="map-workspace__state">Створіть активний пошуковий профіль, щоб відкрити карту.</div>}
      {message && <div className="map-workspace__state is-error" role="status">{message}</div>}

      <div className="map-workspace__grid">
        <section className="map-workspace__map-card">
          {loading && <div className="map-workspace__loading">Завантажую геодані…</div>}
          <LeafletMap
            features={collection.features}
            places={places}
            selectedId={selectedId}
            onSelect={(id) => { void selectListing(id); }}
            onMapClick={setDraftPoint}
          />
          <div className="map-workspace__legend">
            <span><i className="listing" /> Квартира</span>
            <span><i className="favorite" /> Обране</span>
            <span><i className="place" /> Важлива точка</span>
            <strong>{collection.features.length} маркерів</strong>
          </div>
          {detail && (
            <ListingMapSheet
              listing={detail}
              context={context}
              onClose={() => { setDetail(null); setContext(null); setSelectedId(null); }}
              onState={(action, value) => { void updateState(action, value); }}
            />
          )}
        </section>

        {profileId && (
          <ImportantPlacePanel
            profileId={profileId}
            places={places}
            draftPoint={draftPoint}
            onCreated={(place) => { setPlaces((current) => [...current.filter((item) => item.id !== place.id), place]); }}
            onDeleted={(placeId) => { setPlaces((current) => current.filter((item) => item.id !== placeId)); }}
            onClearDraft={() => { setDraftPoint(null); }}
          />
        )}
      </div>
    </main>
  );
}
