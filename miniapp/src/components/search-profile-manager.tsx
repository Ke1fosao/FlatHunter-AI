"use client";

import { useCallback, useEffect, useState } from "react";

import { PageState } from "@/components/page-state";
import { SearchWizard } from "@/components/search-wizard";
import {
  activateSearchProfile,
  ApiError,
  deleteSearchProfile,
  fetchSearchProfiles,
  pauseSearchProfile,
  type SearchProfile,
} from "@/lib/api";

function formatMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }
  return new Intl.NumberFormat("uk-UA")
    .format(value)
    .replaceAll("\u00A0", " ")
    .replaceAll("\u202F", " ");
}

function priceRange(profile: SearchProfile): string {
  const minimum = profile.price_min ?? 0;
  const maximum = profile.price_max;
  return `${formatMoney(minimum)}–${maximum === null || maximum === undefined ? "∞" : formatMoney(maximum)} грн`;
}

type Props = {
  compact?: boolean;
  onChanged?: (profiles: SearchProfile[]) => void;
};

export function SearchProfileManager({ compact = false, onChanged }: Props) {
  const [profiles, setProfiles] = useState<SearchProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [workingId, setWorkingId] = useState("");
  const [editingProfile, setEditingProfile] = useState<SearchProfile | null>(null);
  const [creating, setCreating] = useState(false);
  const [deleteCandidate, setDeleteCandidate] = useState<SearchProfile | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const result = await fetchSearchProfiles(signal);
      setProfiles(result);
      onChanged?.(result);
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setError(
          reason instanceof ApiError
            ? reason.message
            : "Не вдалося завантажити пошукові профілі.",
        );
      }
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, [onChanged]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const runAction = async (
    profile: SearchProfile,
    action: "pause" | "activate" | "delete",
  ) => {
    setWorkingId(profile.id);
    setError("");
    try {
      if (action === "pause") {
        await pauseSearchProfile(profile.id);
      } else if (action === "activate") {
        await activateSearchProfile(profile.id);
      } else {
        await deleteSearchProfile(profile.id);
        setDeleteCandidate(null);
      }
      await load();
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Не вдалося виконати дію з пошуком.",
      );
    } finally {
      setWorkingId("");
    }
  };

  return (
    <div className={compact ? "search-manager is-compact" : "search-manager"}>
      <div className="search-manager__heading">
        <div>
          <span className="route-kicker">ПОШУКОВІ ПРОФІЛІ</span>
          <h2>Керування пошуками</h2>
        </div>
        <button
          type="button"
          className="route-primary-action"
          onClick={() => setCreating(true)}
        >
          ＋ Новий пошук
        </button>
      </div>

      {error && (
        <p className="route-inline-error" role="status">
          {error}
        </p>
      )}

      {loading && <PageState kind="loading" title="Завантажую пошуки" />}

      {!loading && profiles.length === 0 && (
        <PageState
          kind="empty"
          title="Пошуків ще немає"
          description="Створіть профіль — FlatHunter почне відбирати квартири, рахувати Match Score і надсилати сповіщення."
          action={
            <button type="button" onClick={() => setCreating(true)}>
              Створити перший пошук
            </button>
          }
        />
      )}

      {!loading && profiles.length > 0 && (
        <div className="search-manager__list">
          {profiles.map((profile) => (
            <article className="search-manager__card" key={profile.id}>
              <div className="search-manager__card-main">
                <div>
                  <span>{profile.city}</span>
                  <h3>{profile.name}</h3>
                  <p>
                    {priceRange(profile)} · {profile.rooms.join(", ") || "будь-які"} кімн.
                  </p>
                </div>
                <span className={profile.is_active ? "is-active" : "is-paused"}>
                  {profile.is_active ? "Активний" : "Пауза"}
                </span>
              </div>

              <div className="search-manager__meta">
                <span>
                  Match від {profile.notification_preference.min_match_score}%
                </span>
                <span>
                  Risk до {profile.notification_preference.max_risk_score}
                </span>
                <span>{profile.notification_preference.daily_limit}/день</span>
                <span>{profile.notification_preference.frequency}</span>
              </div>

              <div className="search-manager__actions">
                <button
                  type="button"
                  onClick={() => setEditingProfile(profile)}
                >
                  Редагувати
                </button>
                <button
                  type="button"
                  disabled={workingId === profile.id}
                  onClick={() =>
                    void runAction(
                      profile,
                      profile.is_active ? "pause" : "activate",
                    )
                  }
                >
                  {profile.is_active ? "Призупинити" : "Активувати"}
                </button>
                <button
                  type="button"
                  className="is-danger"
                  onClick={() => setDeleteCandidate(profile)}
                >
                  Видалити
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {(creating || editingProfile !== null) && (
        <SearchWizard
          profile={editingProfile ?? undefined}
          onClose={() => {
            setCreating(false);
            setEditingProfile(null);
          }}
          onCreated={() => {
            setCreating(false);
            void load();
          }}
          onSaved={() => {
            setCreating(false);
            setEditingProfile(null);
            void load();
          }}
        />
      )}

      {deleteCandidate && (
        <div
          className="wizard-backdrop search-delete-backdrop"
          role="presentation"
          onClick={(event) => {
            if (event.currentTarget === event.target) {
              setDeleteCandidate(null);
            }
          }}
        >
          <section
            className="search-delete-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-search-title"
          >
            <span className="route-kicker">НЕЗВОРОТНА ДІЯ</span>
            <h2 id="delete-search-title">Видалити «{deleteCandidate.name}»?</h2>
            <p>
              Пошук, важливі місця та його налаштування сповіщень буде видалено.
            </p>
            <div>
              <button type="button" onClick={() => setDeleteCandidate(null)}>
                Скасувати
              </button>
              <button
                type="button"
                className="is-danger"
                disabled={workingId === deleteCandidate.id}
                onClick={() => void runAction(deleteCandidate, "delete")}
              >
                Так, видалити пошук
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
