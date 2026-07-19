"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ClusterListingCard } from "@/components/cluster-listing-card";
import { PageState } from "@/components/page-state";
import { useListingState } from "@/hooks/use-listing-state";
import { ApiError, fetchListings } from "@/lib/api";
import type { ClusterFeedItem, ClusterListing } from "@/lib/cluster-api";

type SortMode = "newest" | "price-asc" | "price-desc";

function includesText(value: string, query: string): boolean {
  return value.toLocaleLowerCase("uk").includes(query.toLocaleLowerCase("uk"));
}

export function FavoritesWorkspace() {
  const [items, setItems] = useState<ClusterListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sort, setSort] = useState<SortMode>("newest");
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [rooms, setRooms] = useState("");
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [text, setText] = useState("");
  const { pendingId, error: actionError, updateListingState } = useListingState();

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const response = await fetchListings({ favorites: true }, signal);
      setItems(
        response.results.filter(
          (item) => !item.user_state.is_hidden,
        ) as ClusterListing[],
      );
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setError(
          reason instanceof ApiError
            ? reason.message
            : "Не вдалося завантажити обране.",
        );
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => { controller.abort(); };
  }, [load]);

  const visibleItems = useMemo(() => {
    const room = rooms ? Number.parseInt(rooms, 10) : null;
    const minimum = priceMin ? Number.parseInt(priceMin, 10) : null;
    const maximum = priceMax ? Number.parseInt(priceMax, 10) : null;
    const query = text.trim();
    const filtered = items.filter((item) => {
      if (city.trim() && !includesText(item.city, city.trim())) return false;
      if (district.trim() && !includesText(item.district, district.trim())) {
        return false;
      }
      if (room !== null && item.rooms !== room) return false;
      if (minimum !== null && item.price_max_uah < minimum) return false;
      if (maximum !== null && item.price_min_uah > maximum) return false;
      if (
        query &&
        ![item.title, item.description, item.street, item.district].some((value) =>
          includesText(value, query),
        )
      ) {
        return false;
      }
      return true;
    });
    return [...filtered].sort((left, right) => {
      if (sort === "price-asc") {
        return left.price_min_uah - right.price_min_uah;
      }
      if (sort === "price-desc") {
        return right.price_max_uah - left.price_max_uah;
      }
      return (
        new Date(right.published_at).getTime() -
        new Date(left.published_at).getTime()
      );
    });
  }, [city, district, items, priceMax, priceMin, rooms, sort, text]);

  return (
    <div className="route-page">
      <header className="route-page__header">
        <div>
          <span className="route-kicker">ЗБЕРЕЖЕНІ ВАРІАНТИ</span>
          <h1>Обране</h1>
          <p>Кластеризовані квартири, які ви відклали для детального перегляду.</p>
        </div>
        <span className="route-count">{items.length}</span>
      </header>

      <div className="search-results-filters favorites-filters">
        <label>
          Місто
          <input value={city} onChange={(event) => { setCity(event.target.value); }} />
        </label>
        <label>
          Район
          <input
            value={district}
            onChange={(event) => { setDistrict(event.target.value); }}
          />
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
        <label>
          Сортування
          <select
            value={sort}
            onChange={(event) => { setSort(event.target.value as SortMode); }}
          >
            <option value="newest">Спочатку нові</option>
            <option value="price-asc">Спочатку дешевші</option>
            <option value="price-desc">Спочатку дорожчі</option>
          </select>
        </label>
        <label className="search-results-filters__text">
          Текст
          <input
            value={text}
            onChange={(event) => { setText(event.target.value); }}
            placeholder="Назва, вулиця або опис"
          />
        </label>
        <button type="button" className="route-primary-action" onClick={() => void load()}>
          Оновити
        </button>
      </div>

      {(error || actionError) && !loading && (
        <p className="route-inline-error" role="status">
          {actionError || error}
        </p>
      )}
      {loading && <PageState kind="loading" title="Завантажую обрані квартири" />}
      {!loading && !error && visibleItems.length === 0 && (
        <PageState
          kind="empty"
          title="За цими фільтрами нічого немає"
          description="Додавайте квартири з пошуку або карти — вони з’являться тут."
          action={<Link href="/search">Перейти до пошуку</Link>}
        />
      )}
      {!loading && visibleItems.length > 0 && (
        <div className="cluster-route-grid">
          {visibleItems.map((listing) => {
            const item: ClusterFeedItem = { listing, match: null };
            return (
              <ClusterListingCard
                key={listing.cluster_id ?? listing.id}
                item={item}
                pending={pendingId === listing.id}
                showHide={false}
                onState={(field, value) => {
                  const action =
                    field === "is_favorite"
                      ? "favorite"
                      : field === "is_compared"
                        ? "compare"
                        : "hide";
                  void updateListingState(listing, action, value, (updated) => {
                    setItems((current) =>
                      current
                        .map((candidate) =>
                          candidate.id === updated.id
                            ? (updated as ClusterListing)
                            : candidate,
                        )
                        .filter(
                          (candidate) =>
                            candidate.user_state.is_favorite &&
                            !candidate.user_state.is_hidden,
                        ),
                    );
                  });
                }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
