"use client";

import { PageState } from "@/components/page-state";
import { PreviewHub } from "@/components/preview-hub";
import { useMiniApp } from "@/components/miniapp-context";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const {
    authStatus,
    authError,
    authErrorCode,
    backendWakeAttempt,
    connection,
    retryAuthentication,
  } = useMiniApp();

  if (authStatus === "authenticated") {
    return children;
  }

  if (connection === "offline") {
    return (
      <PageState
        kind="offline"
        title="Немає з’єднання"
        description="Підключіться до інтернету, щоб FlatHunter міг підтвердити Telegram-профіль і завантажити дані."
        action={
          <button type="button" onClick={retryAuthentication}>
            Перевірити ще раз
          </button>
        }
      />
    );
  }

  if (authStatus === "preview") {
    return <PreviewHub />;
  }

  if (authStatus === "waiting_backend") {
    const attemptSuffix =
      backendWakeAttempt > 1 ? ` Поточна спроба ${String(backendWakeAttempt)}.` : "";
    return (
      <PageState
        kind="loading"
        title="Запускаю сервер FlatHunter…"
        description={`Backend на безкоштовному хостингу прокидається після паузи. Зазвичай це займає 20–60 секунд. Авторизація повториться автоматично.${attemptSuffix}`}
        action={
          <button type="button" onClick={retryAuthentication}>
            Перевірити зараз
          </button>
        }
      />
    );
  }

  if (authStatus === "error") {
    const invalidTelegramData = authErrorCode === "invalid_telegram_data";
    return (
      <PageState
        kind="error"
        title={
          invalidTelegramData
            ? "Telegram не підтвердив вхід"
            : "Не вдалося увійти через Telegram"
        }
        description={
          invalidTelegramData
            ? "Закрийте Mini App і відкрийте його заново з кнопки бота. Дані Telegram могли застаріти, а повторний запуск створить новий захищений підпис."
            : authError ||
              "Закрийте Mini App, відкрийте його знову або повторіть авторизацію."
        }
        action={
          <button type="button" onClick={retryAuthentication}>
            Спробувати ще раз
          </button>
        }
      />
    );
  }

  if (authStatus === "authenticating") {
    return (
      <PageState
        kind="loading"
        title="Перевіряю Telegram-профіль…"
        description="Сервер уже працює. Перевіряю захищені дані Telegram і відкриваю ваш кабінет."
      />
    );
  }

  return (
    <PageState
      kind="loading"
      title="Підключаю Telegram-профіль…"
      description="Отримую дані Mini App та перевіряю доступність сервера."
    />
  );
}
