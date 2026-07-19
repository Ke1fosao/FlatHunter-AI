"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useMiniApp } from "@/components/miniapp-context";
import { PageState } from "@/components/page-state";
import {
  ApiError,
  fetchSearchProfiles,
  TELEGRAM_AUTHENTICATED_EVENT,
  type SearchProfileSummary,
} from "@/lib/api";

type NotificationSettings = {
  enabled: boolean;
  quietHours: boolean;
  quietStart: string;
  quietEnd: string;
};

const defaultSettings: NotificationSettings = {
  enabled: true,
  quietHours: true,
  quietStart: "23:00",
  quietEnd: "08:00",
};

export function ProfileWorkspace() {
  const {
    telegram,
    user,
    displayName,
    locale,
    setLocale,
    connection,
    health,
    authFailed,
  } = useMiniApp();
  const [profiles, setProfiles] = useState<SearchProfileSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [settings, setSettings] = useState<NotificationSettings>(defaultSettings);
  const [saved, setSaved] = useState(false);

  const loadProfiles = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setMessage("");
    try {
      setProfiles(await fetchSearchProfiles(signal));
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setMessage(
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
  }, []);

  useEffect(() => {
    const raw = window.localStorage.getItem("flathunter-notifications");
    if (raw) {
      try {
        setSettings({ ...defaultSettings, ...(JSON.parse(raw) as NotificationSettings) });
      } catch {
        window.localStorage.removeItem("flathunter-notifications");
      }
    }

    const controller = new AbortController();
    void loadProfiles(controller.signal);
    const reload = () => {
      void loadProfiles();
    };
    window.addEventListener(TELEGRAM_AUTHENTICATED_EVENT, reload);
    return () => {
      controller.abort();
      window.removeEventListener(TELEGRAM_AUTHENTICATED_EVENT, reload);
    };
  }, [loadProfiles]);

  const saveSettings = () => {
    window.localStorage.setItem(
      "flathunter-notifications",
      JSON.stringify(settings),
    );
    setSaved(true);
    window.setTimeout(() => {
      setSaved(false);
    }, 2200);
  };

  return (
    <div className="route-page profile-route" role="region" aria-label="Профіль користувача">
      <header className="profile-identity">
        <div className="profile-identity__avatar" aria-hidden="true">
          {displayName.slice(0, 1).toUpperCase()}
        </div>
        <div>
          <span className="route-kicker">ПРОФІЛЬ</span>
          <h1>{displayName}</h1>
          <p>
            {telegram.isTelegram
              ? user?.username
                ? `@${user.username}`
                : "Підключено через Telegram Mini App"
              : "Preview-режим — відкрийте застосунок у Telegram для авторизації"}
          </p>
        </div>
        <span className={`connection-pill connection-pill--${connection}`}>
          {connection === "ready"
            ? "Онлайн"
            : connection === "offline"
              ? "Офлайн"
              : connection === "checking"
                ? "Перевірка"
                : "Обмежено"}
        </span>
      </header>

      {authFailed && (
        <p className="route-inline-error" role="status">
          Не вдалося підтвердити Telegram-профіль. Закрийте та повторно відкрийте Mini App.
        </p>
      )}

      <section className="route-section">
        <div className="route-section__heading">
          <div>
            <span className="route-kicker">ЗАСТОСУНОК</span>
            <h2>Мова та режим</h2>
          </div>
        </div>
        <div className="profile-settings-grid">
          <article>
            <span>Мова інтерфейсу</span>
            <div className="profile-segmented-control">
              <button
                type="button"
                className={locale === "uk" ? "is-active" : undefined}
                onClick={() => {
                  setLocale("uk");
                }}
              >
                Українська
              </button>
              <button
                type="button"
                className={locale === "en" ? "is-active" : undefined}
                onClick={() => {
                  setLocale("en");
                }}
              >
                English
              </button>
            </div>
          </article>
          <article>
            <span>Режим</span>
            <strong>{telegram.isTelegram ? "Telegram" : "Preview"}</strong>
            <small>Тема: {telegram.colorScheme === "dark" ? "темна" : "світла"}</small>
          </article>
          <article>
            <span>З’єднання</span>
            <strong>{health?.service ?? "FlatHunter API"}</strong>
            <small>
              База: {health?.checks.database === "ok" ? "готова" : "перевіряється"}
            </small>
          </article>
        </div>
      </section>

      <section className="route-section">
        <div className="route-section__heading">
          <div>
            <span className="route-kicker">СПОВІЩЕННЯ</span>
            <h2>Коли повідомляти</h2>
          </div>
        </div>
        <div className="notification-settings">
          <label className="settings-toggle">
            <span>
              <strong>Нові збіги</strong>
              <small>Отримувати повідомлення про відповідні квартири</small>
            </span>
            <input
              type="checkbox"
              checked={settings.enabled}
              onChange={(event) => {
                setSettings((current) => ({
                  ...current,
                  enabled: event.target.checked,
                }));
              }}
            />
          </label>
          <label className="settings-toggle">
            <span>
              <strong>Тихі години</strong>
              <small>Не турбувати вночі</small>
            </span>
            <input
              type="checkbox"
              checked={settings.quietHours}
              onChange={(event) => {
                setSettings((current) => ({
                  ...current,
                  quietHours: event.target.checked,
                }));
              }}
            />
          </label>
          {settings.quietHours && (
            <div className="quiet-hours-grid">
              <label>
                З
                <input
                  type="time"
                  value={settings.quietStart}
                  onChange={(event) => {
                    setSettings((current) => ({
                      ...current,
                      quietStart: event.target.value,
                    }));
                  }}
                />
              </label>
              <label>
                До
                <input
                  type="time"
                  value={settings.quietEnd}
                  onChange={(event) => {
                    setSettings((current) => ({
                      ...current,
                      quietEnd: event.target.value,
                    }));
                  }}
                />
              </label>
            </div>
          )}
          <button type="button" className="route-primary-action" onClick={saveSettings}>
            {saved ? "Збережено ✓" : "Зберегти налаштування"}
          </button>
        </div>
      </section>

      <section className="route-section">
        <div className="route-section__heading">
          <div>
            <span className="route-kicker">ПОШУКОВІ ПРОФІЛІ</span>
            <h2>Ваші пошуки</h2>
          </div>
          <Link href="/search" className="route-text-action">
            Керувати
          </Link>
        </div>
        {loading && <PageState kind="loading" title="Завантажую профілі" />}
        {!loading && message && (
          <PageState kind="error" title="Не вдалося завантажити" description={message} />
        )}
        {!loading && !message && profiles.length === 0 && (
          <PageState
            kind="empty"
            title="Пошуків ще немає"
            action={<Link href="/search">Створити перший пошук</Link>}
          />
        )}
        {!loading && profiles.length > 0 && (
          <div className="profile-search-list">
            {profiles.map((profile) => (
              <article key={profile.id}>
                <div>
                  <strong>{profile.name}</strong>
                  <span>{profile.city}</span>
                </div>
                <span className={profile.is_active ? "is-active" : undefined}>
                  {profile.is_active ? "Активний" : "Пауза"}
                </span>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
