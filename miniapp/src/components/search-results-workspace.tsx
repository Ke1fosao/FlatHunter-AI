"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ClusterListingCard } from "@/components/cluster-listing-card";
import { PageState } from "@/components/page-state";
import {
  ApiError,
  fetchSearchProfiles,
  setListingState,
  type SearchProfile,
} from "@/lib/api";
import {
  fetchClusterFeed,
  setClusterState,
  type ClusterFeedItem,
  type ClusterListing,
} from "@/lib/cluster-api";

type SortMode = "match" | "newest" | "price-asc" | "price-desc";
type ClusterBooleanField = "is_favorite" | "is_hidden" | "is_compared";

function includesText(value: string, query: string): boolean {
  return value.toLocaleLowerCase("uk").includes(query.toLocaleLowerCase("uk"));
}

function updateListingFromCluster(
  current: ClusterListing,
  response: {
    primary?: ClusterListing;
    user_state?: ClusterListing["user_state"];
  },
): ClusterListing {
  const primary = response.primary ?? current;
  return {
    ...current,
    ...primary,
    user_state: response.user_state ?? primary.user_state,
  };
}

export function SearchResultsWorkspace() {
  const [profiles, setProfiles] = useState<SearchProfile[]>([]);
  const [profileId, setProfileId] = useState("");
  const [items, setItems] = useState<ClusterFeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pendingId, setPendingId] = useState("");
  const [minScore, setMinScore] = useState("50");
  const [ordering, setOrdering] = useState<SortMode>("match");
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [rooms, setRooms] = useState("");
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [text, setText] = useState("");

  const selectedProfile = useMemo(
    () => profiles.find((profile) => profile.id === profileId) ?? null,
    [profileId, profiles],
  );

  const loadProfiles = useCallback(async (signal?: AbortSignal) => {
    const result = await fetchSearchProfiles(signal);
    const active = result.filter((profile) => profile.is_active);
    setProfiles(active);
    setProfileId((current) =>
      current.length > 0 ? current : (active.at(0)?.id ?? ""),
    );
    return active;
  }, []);

  const loadFeed = useCallback(
    async (profile: SearchProfile | null, signal?: AbortSignal) => {
      const result = await fetchClusterFeed(profile, Number(minScore), signal);
      setItems(result.filter((item) => !item.listing.user_state.is_hidden));
    },
    [minScore],
  );

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError("");
      try {
        let profile = selectedProfile;
        if (profiles.length === 0) {
          const available = await loadProfiles(signal);
          profile = available.at(0) ?? null;
        }
        await loadFeed(profile, signal);
      } catch (reason) {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) {
          setError(
            reason instanceof ApiError
              ? reason.message
              : "Не вдалося завантажити згруповані квартири.",
          );
        }
      } finally {
        if (!signal?.aborted) {
          setLoading(false);
        }
      }
    }, [loadFeed, loadProfiles, profiles.length, selectedProfile]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => { controller.abort(); };
  }, [load]);

  const visibleItems = useMemo(() => {
    const normalizedText = text.trim();
    const roomNumber = rooms ? Number.parseInt(rooms, 10) : null;
    const minimum = priceMin ? Number.parseInt(priceMin, 10) : null;
    const maximum = priceMax ? Number.parseInt(priceMax, 10) : null;

    const filtered = items.filter(({ listing }) => {
      if (city.trim() && !includesText(listing.city, city.trim())) return false;
      if (district.trim() && !includesText(listing.district, district.trim())) {
        return false;
      }
      if (roomNumber !== null && listing.rooms !== roomNumber) return false;
      if (minimum !== null && listing.price_max_uah < minimum) return false;
      if (maximum !== null && listing.price_min_uah > maximum) return false;
      if (
        normalizedText &&
        ![
          listing.title,
          listing.description,
          listing.street,
          listing.district,
          listing.city,
        ].some((value) => includesText(value, normalizedText))
      ) {
        return false;
      }
      return true;
    });

    return [...filtered].sort((left, right) => {
      if (ordering === "price-asc") {
        return left.listing.price_min_uah - right.listing.price_min_uah;
      }
      if (ordering === "price-desc") {
        return right.listing.price_max_uah - left.listing.price_max_uah;
      }
      if (ordering === "newest") {
        return (
          new Date(right.listing.published_at).getTime() -
          new Date(left.listing.published_at).getTime()
        );
      }
      return (right.match?.score ?? 0) - (left.match?.score ?? 0);
    });
  }, [city, district, items, ordering, priceMax, priceMin, rooms, text]);

  const updateState = async (
    item: ClusterFeedItem,
    field: ClusterBooleanField,
    value: boolean,
  ) => {
    const key = item.listing.cluster_id ?? item.listing.id;
    setPendingId(key);
    setError("");
    try {
      let updated: ClusterListing;
      if (item.listing.cluster_id) {
        const response = await setClusterState(item.listing.cluster_id, {
          [field]: value,
        });
        updated = updateListingFromCluster(item.listing, response);
      } else {
        const action =
          field === "is_favorite"
            ? "favorite"
            : field === "is_compared"
              ? "compare"
              : "hide";
        updated = (await setListingState(
          item.listing.id,
          action,
          value,
        )) as ClusterListing;
      }
      setItems((current) =>
        current
          .map((candidate) =>
            (candidate.listing.cluster_id ?? candidate.listing.id) === key
              ? { ...candidate, listing: updated }
              : candidate,
          )
          .filter((candidate) => !candidate.listing.user_state.is_hidden),
      );
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Не вдалося зберегти дію з квартирою.",
      );
    } finally {
      setPendingId("");
    }
  };

  return (
    <section className="search-results-workspace">
      <div className="route-section__heading">
        <div>
          <span className="route-kicker">УСІ ЗБІГИ</span>
          <h2>Згруповані квартири</h2>
        </div>
        <button type="button" className="route-text-action" onClick={() => void load()}>
          Оновити
        </button>
      </div>

      <div className="search-results-filters">
        <label>
          Пошук
          <select
            value={profileId}
            onChange={(event) => { setProfileId(event.target.value); }}
          >
            {profiles.length === 0 && <option value="">Без активного профілю</option>}
            {profiles.map((profile) => (
              <option value={profile.id} key={profile.id}>
                {profile.name} · {profile.city}
              </option>
            ))}
          </select>
        </label>
        <label>
          Match від
          <select value={minScore} onChange={(event) => { setMinScore(event.target.value); }}>
            <option value="0">0%</option>
            <option value="50">50%</option>
            <option value="70">70%</option>
            <option value="85">85%</option>
          </select>
        </label>
        <label>
          Сортування
          <select
            value={ordering}
            onChange={(event) => { setOrdering(event.target.value as SortMode); }}
          >
            <option value="match">Найкращий Match</option>
            <option value="newest">Спочатку нові</option>
            <option value="price-asc">Спочатку дешевші</option>
            <option value="price-desc">Спочатку дорожчі</option>
          </select>
        </label>
        <label>
          Місто
          <input value={city} onChange={(event) => { setCity(event.target.value); }} />
        </label>
        <label>
          Район
          <input value={district} onChange={(event) => { setDistrict(event.target.value); }} />
        </label>
        <label>
          Кімнати
          <input
            type="number"
            min="1"
            value={rooms}
            onChange={(event) => { setRooms(event.target.value); }}
          />
        </label>
        <label>
          Мінімальна ціна
          <input
            type="number"
            min="0"
            value={priceMin}
            onChange={(event) => { setPriceMin(event.target.value); }}
          />
        </label>
        <label>
          Максимальна ціна
          <input
            type="number"
            min="0"
            value={priceMax}
            onChange={(event) => { setPriceMax(event.target.value); }}
          />
        </label>
        <label className="search-results-filters__text">
          Текст
          <input
            value={text}
            onChange={(event) => { setText(event.target.value); }}
            placeholder="Вулиця, опис або назва"
          />
        </label>
      </div>

      {error && (
        <p className="route-inline-error" role="status">
          {error}
        </p>
      )}
      {loading && <PageState kind="loading" title="Завантажую збіги" />}
      {!loading && visibleItems.length === 0 && (
        <PageState
          kind="empty"
          title="За цими фільтрами нічого немає"
          description="Змініть критерії або оновіть пошук після появи нових оголошень."
        />
      )}
      {!loading && visibleItems.length > 0 && (
        <div className="cluster-route-grid">
          {visibleItems.map((item) => {
            const key = item.listing.cluster_id ?? item.listing.id;
            return (
              <ClusterListingCard
                key={key}
                item={item}
                profileId={profileId || undefined}
                pending={pendingId === key}
                onState={(field, value) => void updateState(item, field, value)}
              />
            );
          })}
        </div>
      )}
    </section>
  );
}
