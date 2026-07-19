"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ListingCard } from "@/components/listing-card";
import { PageState } from "@/components/page-state";
import { useListingState } from "@/hooks/use-listing-state";
import {
  ApiError,
  fetchListings,
  TELEGRAM_AUTHENTICATED_EVENT,
  type ListingFeedItem,
} from "@/lib/api";

type SortMode = "newest" | "price-asc" | "price-desc";

export function FavoritesWorkspace() {
  const [items, setItems] = useState<ListingFeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sort, setSort] = useState<SortMode>("newest");
  const [district, setDistrict] = useState("");
  const { pendingId, error: actionError, updateListingState } = useListingState();

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const response = await fetchListings({ favorites: true }, signal);
      setItems(response.results.filter((item) => !item.user_state.is_hidden));
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setError(
          reason instanceof ApiError
            ? reason.message
            : "Не вдалося завантажити обране.",
        );
      }
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    const reload = () => {
      void load();
    };
    window.addEventListener(TELEGRAM_AUTHENTICATED_EVENT, reload);
    return () => {
      controller.abort();
      window.removeEventListener(TELEGRAM_AUTHENTICATED_EVENT, reload);
    };
  }, [load]);

  const visibleItems = useMemo(() => {
    const filtered = district.trim()
      ? items.filter((item) =>
          item.district.toLowerCase().includes(district.trim().toLowerCase()),
        )
      : items;
    return [...filtered].sort((left, right) => {
      if (sort === "price-asc") {
        return left.price_uah - right.price_uah;
      }
      if (sort === "price-desc") {
        return right.price_uah - left.price_uah;
      }
      return (
        new Date(right.published_at).getTime() -
        new Date(left.published_at).getTime()
      );
    });
  }, [district, items, sort]);

  return (
    <div className="route-page">
      <header className="route-page__header">
        <div>
          <span className="route-kicker">ЗБЕРЕЖЕНІ ВАРІАНТИ</span>
          <h1>Обране</h1>
          <p>Квартири, які ви відклали для детальнішого перегляду.</p>
        </div>
        <span className="route-count">{items.length}</span>
      </header>

      <div className="route-toolbar">
        <label>
          Район
          <input
            value={district}
            placeholder="Наприклад, Франківський"
            onChange={(event) => {
              setDistrict(event.target.value);
            }}
          />
        </label>
        <label>
          Сортування
          <select
            value={sort}
            onChange={(event) => {
              setSort(event.target.value as SortMode);
            }}
          >
            <option value="newest">Спочатку нові</option>
            <option value="price-asc">Спочатку дешевші</option>
            <option value="price-desc">Спочатку дорожчі</option>
          </select>
        </label>
        <button type="button" onClick={() => void load()}>
          Оновити
        </button>
      </div>

      {(error || actionError) && !loading && (
        <p className="route-inline-error" role="status">
          {actionError || error}
        </p>
      )}

      {loading && (
        <PageState kind="loading" title="Завантажую обрані квартири" />
      )}

      {!loading && !error && visibleItems.length === 0 && (
        <PageState
          kind="empty"
          title="В обраному поки порожньо"
          description="Додавайте квартири з пошуку або карти — вони з’являться тут."
          action={<Link href="/search">Перейти до пошуку</Link>}
        />
      )}

      {!loading && visibleItems.length > 0 && (
        <div className="routed-listing-grid">
          {visibleItems.map((listing) => (
            <ListingCard
              key={listing.id}
              listing={listing}
              pending={pendingId === listing.id}
              showHide={false}
              onState={(item, action, value) => {
                void updateListingState(item, action, value, (updated) => {
                  setItems((current) =>
                    current
                      .map((candidate) =>
                        candidate.id === updated.id ? updated : candidate,
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
          ))}
        </div>
      )}
    </div>
  );
}
