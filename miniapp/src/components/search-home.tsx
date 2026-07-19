"use client";

import { useCallback, useEffect, useState } from "react";

import { AIAssistantWorkspace } from "@/components/ai-assistant-workspace";
import { ListingCard } from "@/components/listing-card";
import { PageState } from "@/components/page-state";
import { SearchProfileCard } from "@/components/search-profile-card";
import { SearchWizard } from "@/components/search-wizard";
import { useListingState } from "@/hooks/use-listing-state";
import {
  ApiError,
  fetchDashboard,
  fetchMatches,
  fetchSearchProfiles,
  TELEGRAM_AUTHENTICATED_EVENT,
  type DashboardResponse,
  type PersonalizedMatch,
  type SearchProfileSummary,
} from "@/lib/api";

export function SearchHome() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [profiles, setProfiles] = useState<SearchProfileSummary[]>([]);
  const [matches, setMatches] = useState<PersonalizedMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [wizardOpen, setWizardOpen] = useState(false);
  const [created, setCreated] = useState(false);
  const { pendingId, error: actionError, updateListingState } = useListingState();

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const [dashboardResponse, profileResponse] = await Promise.all([
        fetchDashboard(signal),
        fetchSearchProfiles(signal),
      ]);
      const activeProfiles = profileResponse.filter((profile) => profile.is_active);
      setDashboard(dashboardResponse);
      setProfiles(profileResponse);

      const primaryProfile = activeProfiles[0];
      if (!primaryProfile) {
        setMatches([]);
      } else {
        const matchResponse = await fetchMatches(
          primaryProfile.id,
          { minScore: 50, ordering: "-match_score" },
          signal,
        );
        setMatches(
          matchResponse.results
            .filter((item) => !item.listing.user_state.is_hidden)
            .slice(0, 6),
        );
      }
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setError(
          reason instanceof ApiError
            ? reason.message
            : "Не вдалося завантажити головну сторінку.",
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

  const replaceListing = (updatedId: string, updated: PersonalizedMatch["listing"]) => {
    setMatches((current) =>
      current
        .map((item) =>
          item.listing.id === updatedId ? { ...item, listing: updated } : item,
        )
        .filter((item) => !item.listing.user_state.is_hidden),
    );
  };

  return (
    <div className="route-page search-route">
      <header className="route-page__header search-route__header">
        <div>
          <span className="route-kicker">ПОШУК ЖИТЛА</span>
          <h1>Ваші квартири в одному місці</h1>
          <p>
            Пошукові профілі, нові збіги та AI-підказки без зайвих екранів.
          </p>
        </div>
        <button
          type="button"
          className="route-primary-action"
          onClick={() => {
            setWizardOpen(true);
          }}
        >
          ＋ Створити пошук
        </button>
      </header>

      {created && (
        <div className="miniapp-toast" role="status">
          ✅ Пошуковий профіль створено
        </div>
      )}

      {loading && (
        <PageState
          kind="loading"
          title="Завантажую ваш простір"
          description="Отримую пошукові профілі та найкращі збіги."
        />
      )}

      {!loading && error && (
        <PageState
          kind="error"
          title="Не вдалося завантажити дані"
          description={error}
          action={
            <button type="button" onClick={() => void load()}>
              Спробувати ще раз
            </button>
          }
        />
      )}

      {!loading && !error && dashboard && (
        <>
          <section className="route-stats" aria-label="Статистика пошуку">
            <article>
              <span>Активні пошуки</span>
              <strong>{dashboard.stats.active_profiles}</strong>
            </article>
            <article>
              <span>Доступні квартири</span>
              <strong>{dashboard.stats.available_listings}</strong>
            </article>
            <article>
              <span>В обраному</span>
              <strong>{dashboard.stats.favorites}</strong>
            </article>
            <article>
              <span>До порівняння</span>
              <strong>{dashboard.stats.compared}</strong>
            </article>
          </section>

          <section className="route-section">
            <div className="route-section__heading">
              <div>
                <span className="route-kicker">ПРОФІЛІ</span>
                <h2>Активні пошуки</h2>
              </div>
              <button
                type="button"
                className="route-text-action"
                onClick={() => {
                  setWizardOpen(true);
                }}
              >
                Додати новий
              </button>
            </div>
            {profiles.length > 0 ? (
              <div className="search-profile-grid">
                {profiles.map((profile) => (
                  <SearchProfileCard key={profile.id} profile={profile} />
                ))}
              </div>
            ) : (
              <PageState
                kind="empty"
                title="Пошуків ще немає"
                description="Створіть перший профіль, і FlatHunter почне підбирати квартири."
                action={
                  <button
                    type="button"
                    onClick={() => {
                      setWizardOpen(true);
                    }}
                  >
                    Створити пошук
                  </button>
                }
              />
            )}
          </section>

          <section className="route-section">
            <div className="route-section__heading">
              <div>
                <span className="route-kicker">НОВІ ЗБІГИ</span>
                <h2>Квартири для вас</h2>
              </div>
            </div>
            {(actionError || error) && (
              <p className="route-inline-error" role="status">
                {actionError || error}
              </p>
            )}
            {matches.length > 0 ? (
              <div className="routed-listing-grid">
                {matches.map((item) => (
                  <ListingCard
                    key={item.listing.id}
                    listing={item.listing}
                    match={item.match}
                    pending={pendingId === item.listing.id}
                    onState={(listing, action, value) => {
                      void updateListingState(
                        listing,
                        action,
                        value,
                        (updated) => {
                          replaceListing(listing.id, updated);
                        },
                      );
                    }}
                  />
                ))}
              </div>
            ) : (
              <PageState
                kind="empty"
                title="Нових збігів поки немає"
                description="Змініть критерії або зачекайте, поки система знайде нові оголошення."
              />
            )}
          </section>

          <section className="route-section search-ai-panel">
            <div className="route-section__heading">
              <div>
                <span className="route-kicker">AI-ПОМІЧНИК</span>
                <h2>Підказки для вибору</h2>
              </div>
            </div>
            <AIAssistantWorkspace />
          </section>
        </>
      )}

      {wizardOpen && (
        <SearchWizard
          onClose={() => {
            setWizardOpen(false);
          }}
          onCreated={() => {
            setWizardOpen(false);
            setCreated(true);
            window.dispatchEvent(new Event(TELEGRAM_AUTHENTICATED_EVENT));
            window.setTimeout(() => {
              setCreated(false);
            }, 3000);
          }}
        />
      )}
    </div>
  );
}
