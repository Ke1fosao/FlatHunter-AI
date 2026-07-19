"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AIAssistantWorkspace } from "@/components/ai-assistant-workspace";
import { PageState } from "@/components/page-state";
import { SearchProfileCard } from "@/components/search-profile-card";
import { SearchResultsWorkspace } from "@/components/search-results-workspace";
import { SearchWizard } from "@/components/search-wizard";
import {
  ApiError,
  fetchDashboard,
  fetchSearchProfiles,
  type DashboardResponse,
  type SearchProfile,
} from "@/lib/api";

export function SearchHome() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [profiles, setProfiles] = useState<SearchProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [wizardOpen, setWizardOpen] = useState(false);
  const [created, setCreated] = useState(false);
  const [resultsVersion, setResultsVersion] = useState(0);

  const activeProfiles = useMemo(
    () => profiles.filter((profile) => profile.is_active),
    [profiles],
  );

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const [dashboardResponse, profileResponse] = await Promise.all([
        fetchDashboard(signal),
        fetchSearchProfiles(signal),
      ]);
      setDashboard(dashboardResponse);
      setProfiles(profileResponse);
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
    return () => controller.abort();
  }, [load]);

  const handleCreated = () => {
    setWizardOpen(false);
    setCreated(true);
    setResultsVersion((value) => value + 1);
    void load();
    window.setTimeout(() => setCreated(false), 3000);
  };

  return (
    <div className="route-page search-route">
      <header className="route-page__header search-route__header">
        <div>
          <span className="route-kicker">ПОШУК ЖИТЛА</span>
          <h1>Ваші квартири в одному місці</h1>
          <p>
            Повна кластеризована стрічка, профілі пошуку, аналітика та AI без
            дублів і втрачених умов.
          </p>
        </div>
        <button
          type="button"
          className="route-primary-action"
          onClick={() => setWizardOpen(true)}
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
          description="Отримую пошукові профілі та статистику."
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
                onClick={() => setWizardOpen(true)}
              >
                Додати новий
              </button>
            </div>
            {activeProfiles.length > 0 ? (
              <div className="search-profile-grid">
                {activeProfiles.map((profile) => (
                  <SearchProfileCard key={profile.id} profile={profile} />
                ))}
              </div>
            ) : (
              <PageState
                kind="empty"
                title="Активних пошуків немає"
                description="Створіть новий пошук або активуйте призупинений у профілі."
                action={
                  <button type="button" onClick={() => setWizardOpen(true)}>
                    Створити пошук
                  </button>
                }
              />
            )}
          </section>

          <section className="route-section search-results-section">
            <SearchResultsWorkspace key={resultsVersion} />
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
          onClose={() => setWizardOpen(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  );
}
