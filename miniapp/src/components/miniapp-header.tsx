"use client";

import { HomeIcon } from "@/components/icons";
import { useMiniApp } from "@/components/miniapp-context";

export function MiniAppHeader() {
  const { displayName, locale, setLocale, connection } = useMiniApp();

  const connectionLabel =
    connection === "ready"
      ? "Система готова"
      : connection === "offline"
        ? "Офлайн"
        : connection === "waking"
          ? "Запускаю сервер"
          : connection === "checking"
            ? "Перевіряю з’єднання"
            : "Обмежене з’єднання";

  return (
    <header className="miniapp-header">
      <div className="miniapp-brand">
        <span className="miniapp-brand__mark" aria-hidden="true">
          <HomeIcon />
        </span>
        <span>
          <strong>FlatHunter AI</strong>
          <small>{connectionLabel}</small>
        </span>
      </div>

      <div className="miniapp-header__actions">
        <div className="miniapp-language" aria-label="Мова застосунку">
          <button
            type="button"
            className={locale === "uk" ? "is-active" : undefined}
            onClick={() => {
              setLocale("uk");
            }}
          >
            UA
          </button>
          <button
            type="button"
            className={locale === "en" ? "is-active" : undefined}
            onClick={() => {
              setLocale("en");
            }}
          >
            EN
          </button>
        </div>
        <span className="miniapp-avatar" aria-label={displayName}>
          {displayName.slice(0, 1).toUpperCase()}
        </span>
      </div>
    </header>
  );
}
