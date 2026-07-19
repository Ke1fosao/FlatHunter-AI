"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";

import { PageState } from "@/components/page-state";
import { useListingState } from "@/hooks/use-listing-state";
import type { AnalysisSummary } from "@/lib/analysis-api";
import {
  ApiError,
  compareListingsWithAI,
  fetchListings,
  TELEGRAM_AUTHENTICATED_EVENT,
  type AIComparisonResponse,
  type ListingFeedItem,
} from "@/lib/api";

type AnalyzedListing = ListingFeedItem & {
  analysis_summary?: AnalysisSummary;
};

function formatPrice(value: number): string {
  return `${new Intl.NumberFormat("uk-UA").format(value)} грн`;
}

function pricePerSquareMetre(listing: ListingFeedItem): string {
  const area = Number.parseFloat(listing.total_area ?? "");
  if (!Number.isFinite(area) || area <= 0) {
    return "—";
  }
  return `${new Intl.NumberFormat("uk-UA", { maximumFractionDigits: 0 }).format(
    listing.price_uah / area,
  )} грн/м²`;
}

export function ComparisonWorkspace() {
  const [items, setItems] = useState<ListingFeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  const [aiResult, setAiResult] = useState<AIComparisonResponse | null>(null);
  const { pendingId, error: actionError, updateListingState } = useListingState();

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const response = await fetchListings({ compared: true }, signal);
      setItems(
        response.results
          .filter((item) => !item.user_state.is_hidden)
          .slice(0, 5),
      );
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setError(
          reason instanceof ApiError
            ? reason.message
            : "Не вдалося завантажити порівняння.",
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

  const rows = useMemo(
    () => [
      {
        label: "Ціна",
        value: (listing: ListingFeedItem) => formatPrice(listing.price_uah),
      },
      {
        label: "Площа",
        value: (listing: ListingFeedItem) =>
          listing.total_area ? `${listing.total_area} м²` : "—",
      },
      {
        label: "Ціна за м²",
        value: pricePerSquareMetre,
      },
      {
        label: "Поверх",
        value: (listing: ListingFeedItem) =>
          listing.floor === null
            ? "—"
            : `${String(listing.floor)}/${listing.floors_total === null ? "?" : String(listing.floors_total)}`,
      },
      {
        label: "Ринкова оцінка",
        value: (listing: ListingFeedItem) => {
          const summary = (listing as AnalyzedListing).analysis_summary;
          if (summary?.market.status !== "ready") {
            return "Недостатньо даних";
          }
          return summary.market.deviation_percent
            ? `${summary.market.deviation_percent}% від медіани`
            : "Близько до ринку";
        },
      },
      {
        label: "Risk Score",
        value: (listing: ListingFeedItem) => {
          const summary = (listing as AnalyzedListing).analysis_summary;
          return summary?.risk.score === undefined
            ? "—"
            : `${String(summary.risk.score)}/100`;
        },
      },
    ],
    [],
  );

  const runAiComparison = async () => {
    if (items.length < 2) {
      return;
    }
    setWorking(true);
    setError("");
    try {
      setAiResult(await compareListingsWithAI(items.map((item) => item.id)));
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Не вдалося виконати AI-порівняння.",
      );
    } finally {
      setWorking(false);
    }
  };

  return (
    <div className="route-page compare-route">
      <header className="route-page__header">
        <div>
          <span className="route-kicker">ВИБІР БЕЗ ХАОСУ</span>
          <h1>Порівняння квартир</h1>
          <p>Ціна, характеристики, ринок і ризики в одному структурованому вигляді.</p>
        </div>
        <button
          type="button"
          className="route-primary-action"
          disabled={items.length < 2 || working}
          onClick={() => void runAiComparison()}
        >
          {working ? "AI аналізує…" : "✦ AI-порівняння"}
        </button>
      </header>

      {(error || actionError) && !loading && (
        <p className="route-inline-error" role="status">
          {actionError || error}
        </p>
      )}

      {loading && <PageState kind="loading" title="Завантажую порівняння" />}

      {!loading && items.length < 2 && (
        <PageState
          kind="empty"
          title="Потрібно щонайменше дві квартири"
          description="Додавайте варіанти до порівняння у пошуку, на карті або в деталях квартири."
          action={<Link href="/search">Перейти до пошуку</Link>}
        />
      )}

      {!loading && items.length >= 2 && (
        <div
          className="comparison-cards"
          role="region"
          aria-label="Порівняння квартир"
          style={{ "--comparison-count": String(items.length) } as CSSProperties}
        >
          <div className="comparison-cards__head">
            <span>Параметр</span>
            {items.map((listing) => (
              <div key={listing.id}>
                <Link href={`/listings/${listing.id}`}>{listing.title}</Link>
                <button
                  type="button"
                  disabled={pendingId === listing.id}
                  aria-label={`Прибрати ${listing.title} з порівняння`}
                  onClick={() => {
                    void updateListingState(
                      listing,
                      "compare",
                      false,
                      (updated) => {
                        setItems((current) =>
                          current
                            .map((item) =>
                              item.id === updated.id ? updated : item,
                            )
                            .filter((item) => item.user_state.is_compared),
                        );
                        setAiResult(null);
                      },
                    );
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          {rows.map((row) => (
            <div className="comparison-cards__row" key={row.label}>
              <strong>{row.label}</strong>
              {items.map((listing) => (
                <span key={listing.id}>{row.value(listing)}</span>
              ))}
            </div>
          ))}
        </div>
      )}

      {aiResult && (
        <section className="route-section comparison-ai-result">
          <div className="route-section__heading">
            <div>
              <span className="route-kicker">AI-ВИСНОВОК</span>
              <h2>Що виглядає найкраще</h2>
            </div>
          </div>
          <p className="comparison-ai-result__lead">{aiResult.recommendation}</p>
          {aiResult.tradeoffs.length > 0 && (
            <ul>
              {aiResult.tradeoffs.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
          {aiResult.unknowns.length > 0 && (
            <p>
              <strong>Потрібно уточнити:</strong> {aiResult.unknowns.join(", ")}
            </p>
          )}
        </section>
      )}
    </div>
  );
}
