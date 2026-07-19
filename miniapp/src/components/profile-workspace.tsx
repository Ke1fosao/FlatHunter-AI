"use client";

import { useMiniApp } from "@/components/miniapp-context";
import { SearchProfileManager } from "@/components/search-profile-manager";

export function ProfileWorkspace() {
  const {
    telegram,
    user,
    displayName,
    locale,
    setLocale,
    connection,
    health,
  } = useMiniApp();

  return (
    <div
      className="route-page profile-route"
      role="region"
      aria-label="Профіль користувача"
    >
      <header className="profile-identity">
        <div className="profile-identity__avatar" aria-hidden="true">
          {displayName.slice(0, 1).toUpperCase()}
        </div>
        <div>
          <span className="route-kicker">ПРОФІЛЬ</span>
          <h1>{displayName}</h1>
          <p>
            {user?.username
              ? `@${user.username}`
              : "Підключено через Telegram Mini App"}
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

      <section className="route-section">
        <div className="route-section__heading">
          <div>
            <span className="route-kicker">ЗАСТОСУНОК</span>
            <h2>Мова та підключення</h2>
          </div>
        </div>
        <div className="profile-settings-grid">
          <article>
            <span>Мова інтерфейсу</span>
            <div className="profile-segmented-control">
              <button
                type="button"
                className={locale === "uk" ? "is-active" : undefined}
                onClick={() => { setLocale("uk"); }}
              >
                Українська
              </button>
              <button
                type="button"
                className={locale === "en" ? "is-active" : undefined}
                onClick={() => { setLocale("en"); }}
              >
                English
              </button>
            </div>
          </article>
          <article>
            <span>Режим</span>
            <strong>{telegram.isTelegram ? "Telegram" : "Preview"}</strong>
            <small>
              Тема: {telegram.colorScheme === "dark" ? "темна" : "світла"}
            </small>
          </article>
          <article>
            <span>Backend</span>
            <strong>{health?.service ?? "FlatHunter API"}</strong>
            <small>
              База: {health?.checks.database === "ok" ? "готова" : "перевіряється"}
            </small>
          </article>
        </div>
      </section>

      <section className="route-section profile-search-manager-section">
        <SearchProfileManager />
      </section>

      <section className="route-section notification-truth-note">
        <div className="route-section__heading">
          <div>
            <span className="route-kicker">СПОВІЩЕННЯ</span>
            <h2>Налаштування для кожного пошуку</h2>
          </div>
        </div>
        <p>
          Частота, Match Score, максимальний Risk Score, денний ліміт, тихі
          години, зміни ціни та повторна активація зберігаються окремо для
          кожного пошукового профілю. Натисніть «Редагувати» біля потрібного
          пошуку, щоб змінити їх у backend.
        </p>
      </section>
    </div>
  );
}
