"use client";

import { PageState } from "@/components/page-state";
import { PreviewHub } from "@/components/preview-hub";
import { useMiniApp } from "@/components/miniapp-context";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const {
    authStatus,
    authError,
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

  if (authStatus === "error") {
    return (
      <PageState
        kind="error"
        title="Не вдалося увійти через Telegram"
        description={
          authError ||
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

  return (
    <PageState
      kind="loading"
      title="Підключаю Telegram-профіль…"
      description="Перевіряю захищені дані та готую ваші пошуки."
    />
  );
}
