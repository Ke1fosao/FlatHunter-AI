"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ListingAnalysisPanel } from "@/components/listing-analysis-panel";
import { PageState } from "@/components/page-state";
import { useListingState } from "@/hooks/use-listing-state";
import type { AnalysisSummary } from "@/lib/analysis-api";
import {
  ApiError,
  fetchListing,
  fetchSearchProfiles,
  generateOwnerQuestionsWithAI,
  summarizeListingWithAI,
  TELEGRAM_AUTHENTICATED_EVENT,
  type AIOwnerQuestionsResponse,
  type AISummaryResponse,
  type ListingFeedItem,
  type SearchProfileSummary,
} from "@/lib/api";

type AnalyzedListing = ListingFeedItem & {
  analysis_summary?: AnalysisSummary;
};

function formatPrice(value: number): string {
  return `${new Intl.NumberFormat("uk-UA").format(value)} грн`;
}

export function ListingDetails({ listingId }: { listingId: string }) {
  const [listing, setListing] = useState<ListingFeedItem | null>(null);
  const [profiles, setProfiles] = useState<SearchProfileSummary[]>([]);
  const [profileId, setProfileId] = useState("");
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState("");
  const [working, setWorking] = useState<"summary" | "questions" | "">("");
  const [summary, setSummary] = useState<AISummaryResponse | null>(null);
  const [questions, setQuestions] = useState<AIOwnerQuestionsResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const { pendingId, error: actionError, updateListingState } = useListingState();

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    setNotFound(false);
    try {
      const [listingResponse, profileResponse] = await Promise.all([
        fetchListing(listingId, signal),
        fetchSearchProfiles(signal).catch(() => [] as SearchProfileSummary[]),
      ]);
      setListing(listingResponse);
      const activeProfiles = profileResponse.filter((profile) => profile.is_active);
      setProfiles(activeProfiles);
      setProfileId((current) => current || activeProfiles[0]?.id || "");
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 404) {
        setNotFound(true);
      } else if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setError(
          reason instanceof ApiError
            ? reason.message
            : "Не вдалося завантажити квартиру.",
        );
      }
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, [listingId]);

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

  const facts = useMemo(() => {
    if (!listing) {
      return [];
    }
    return [
      ["Кімнати", String(listing.rooms)],
      ["Площа", listing.total_area ? `${listing.total_area} м²` : "Не вказано"],
      [
        "Поверх",
        listing.floor === null
          ? "Не вказано"
          : `${String(listing.floor)}/${listing.floors_total === null ? "?" : String(listing.floors_total)}`,
      ],
      ["Тип будинку", listing.building_type || "Не вказано"],
      ["Ремонт", listing.renovation_level || "Не вказано"],
      ["Опалення", listing.heating_type || "Не вказано"],
      [
        "Комісія",
        listing.commission_percent
          ? `${listing.commission_percent}%`
          : "Не вказано",
      ],
      [
        "Тварини",
        listing.pets_allowed === null
          ? "Не вказано"
          : listing.pets_allowed
            ? "Дозволені"
            : "Не дозволені",
      ],
    ];
  }, [listing]);

  const runSummary = async () => {
    setWorking("summary");
    setError("");
    setQuestions(null);
    try {
      setSummary(await summarizeListingWithAI(listingId));
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Не вдалося сформувати AI-резюме.",
      );
    } finally {
      setWorking("");
    }
  };

  const runQuestions = async () => {
    setWorking("questions");
    setError("");
    setSummary(null);
    setCopied(false);
    try {
      setQuestions(
        await generateOwnerQuestionsWithAI(listingId, profileId || undefined),
      );
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Не вдалося сформувати питання власнику.",
      );
    } finally {
      setWorking("");
    }
  };

  if (loading) {
    return (
      <div className="route-page">
        <PageState kind="loading" title="Завантажую квартиру" />
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="route-page">
        <PageState
          kind="empty"
          title="Квартиру не знайдено"
          description="Оголошення могло бути видалене або вже недоступне."
          action={<Link href="/search">Повернутися до пошуку</Link>}
        />
      </div>
    );
  }

  if (!listing) {
    return (
      <div className="route-page">
        <PageState
          kind="error"
          title="Не вдалося відкрити квартиру"
          description={error}
          action={
            <button type="button" onClick={() => void load()}>
              Спробувати ще раз
            </button>
          }
        />
      </div>
    );
  }

  const analysis = (listing as AnalyzedListing).analysis_summary;

  return (
    <article className="route-page listing-details-route">
      {(error || actionError) && (
        <p className="route-inline-error" role="status">
          {actionError || error}
        </p>
      )}

      <section className="listing-details-hero">
        <div className="listing-details-gallery">
          {listing.images.length > 0 ? (
            listing.images.slice(0, 4).map((image, index) => (
              <div
                key={image}
                className={index === 0 ? "is-primary" : undefined}
                style={{ backgroundImage: `url(${image})` }}
                role="img"
                aria-label={`${listing.title}, фото ${String(index + 1)}`}
              />
            ))
          ) : (
            <div className="is-primary listing-details-placeholder">
              <strong>{listing.rooms}к</strong>
              <span>Фото не додано</span>
            </div>
          )}
        </div>

        <div className="listing-details-summary">
          <span className="route-kicker">
            {listing.source_name} · {listing.city}
          </span>
          <h1>{listing.title}</h1>
          <p className="listing-details-location">
            {listing.district || "Район не вказано"}
            {listing.street ? ` · ${listing.street}` : ""}
          </p>
          <strong className="listing-details-price">
            {formatPrice(listing.price_uah)}
          </strong>
          <div className="listing-details-actions">
            <button
              type="button"
              disabled={pendingId === listing.id}
              className={listing.user_state.is_favorite ? "is-active" : undefined}
              onClick={() => {
                void updateListingState(
                  listing,
                  "favorite",
                  !listing.user_state.is_favorite,
                  setListing,
                );
              }}
            >
              {listing.user_state.is_favorite ? "★ В обраному" : "☆ В обране"}
            </button>
            <button
              type="button"
              disabled={pendingId === listing.id}
              className={listing.user_state.is_compared ? "is-active" : undefined}
              onClick={() => {
                void updateListingState(
                  listing,
                  "compare",
                  !listing.user_state.is_compared,
                  setListing,
                );
              }}
            >
              {listing.user_state.is_compared ? "✓ У порівнянні" : "⇄ Порівняти"}
            </button>
          </div>
          <a
            className="listing-details-source"
            href={listing.source_url}
            target="_blank"
            rel="noreferrer"
          >
            Відкрити першоджерело ↗
          </a>
        </div>
      </section>

      <section className="listing-facts-grid" aria-label="Характеристики квартири">
        {facts.map(([label, value]) => (
          <article key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>

      <section className="route-section">
        <div className="route-section__heading">
          <div>
            <span className="route-kicker">ОПИС</span>
            <h2>Про квартиру</h2>
          </div>
        </div>
        <p className="listing-description">
          {listing.description || "Власник не додав розгорнутий опис."}
        </p>
      </section>

      <section className="route-section">
        <div className="route-section__heading">
          <div>
            <span className="route-kicker">АНАЛІТИКА</span>
            <h2>Ринок, ціна та ризики</h2>
          </div>
        </div>
        <ListingAnalysisPanel listingId={listing.id} summary={analysis} />
      </section>

      <section className="route-section listing-ai-section">
        <div className="route-section__heading">
          <div>
            <span className="route-kicker">AI-ПОМІЧНИК</span>
            <h2>Що варто перевірити</h2>
          </div>
        </div>
        {profiles.length > 0 && (
          <label className="listing-ai-profile">
            Пошуковий профіль
            <select
              value={profileId}
              onChange={(event) => {
                setProfileId(event.target.value);
              }}
            >
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.name} · {profile.city}
                </option>
              ))}
            </select>
          </label>
        )}
        <div className="listing-ai-actions">
          <button
            type="button"
            disabled={working.length > 0}
            onClick={() => void runSummary()}
          >
            {working === "summary" ? "Готую резюме…" : "✦ AI-резюме"}
          </button>
          <button
            type="button"
            disabled={working.length > 0}
            onClick={() => void runQuestions()}
          >
            {working === "questions" ? "Готую питання…" : "Питання власнику"}
          </button>
        </div>

        {summary && (
          <article className="listing-ai-output">
            <h3>Короткий висновок</h3>
            <p>{summary.summary}</p>
            {summary.advantages.length > 0 && (
              <div>
                <strong>Переваги</strong>
                <ul>
                  {summary.advantages.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {summary.caveats.length > 0 && (
              <div>
                <strong>Зверніть увагу</strong>
                <ul>
                  {summary.caveats.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </article>
        )}

        {questions && (
          <article className="listing-ai-output">
            <h3>Питання власнику</h3>
            <ol>
              {questions.questions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
            <div className="listing-ai-copy">
              <p>{questions.message}</p>
              <button
                type="button"
                onClick={() => {
                  void navigator.clipboard
                    .writeText(questions.message)
                    .then(() => {
                      setCopied(true);
                    })
                    .catch(() => {
                      setError("Не вдалося скопіювати текст.");
                    });
                }}
              >
                {copied ? "Скопійовано ✓" : "Скопіювати готовий текст"}
              </button>
            </div>
          </article>
        )}
      </section>
    </article>
  );
}
