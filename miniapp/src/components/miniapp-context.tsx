"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useTelegram, type TelegramContext } from "@/hooks/use-telegram";
import {
  authenticateTelegram,
  fetchBackendHealth,
  TELEGRAM_AUTHENTICATED_EVENT,
  type AuthenticatedUser,
  type HealthResponse,
} from "@/lib/api";
import { triggerSelectionFeedback } from "@/lib/telegram";

const BACKEND_RETRY_DELAY_MS = 3000;

export type MiniAppLocale = "uk" | "en";
export type ConnectionState =
  | "checking"
  | "waking"
  | "ready"
  | "degraded"
  | "offline";
export type AuthStatus =
  | "booting"
  | "preview"
  | "waiting_backend"
  | "authenticating"
  | "authenticated"
  | "error";

type MiniAppContextValue = {
  telegram: TelegramContext;
  user: AuthenticatedUser | null;
  displayName: string;
  locale: MiniAppLocale;
  setLocale: (locale: MiniAppLocale) => void;
  connection: ConnectionState;
  health: HealthResponse | null;
  authStatus: AuthStatus;
  authError: string;
  authErrorCode: string;
  backendWakeAttempt: number;
  authFailed: boolean;
  isAuthenticated: boolean;
  retryAuthentication: () => void;
};

type ApiErrorShape = {
  code?: unknown;
  status?: unknown;
};

const MiniAppContext = createContext<MiniAppContextValue | null>(null);

function resolveDisplayName(
  authenticatedName: string | undefined,
  telegramName: string,
): string {
  const candidates = [authenticatedName, telegramName];
  const resolved = candidates.find(
    (candidate) => candidate !== undefined && candidate.trim().length > 0,
  );
  return resolved?.trim() ?? "Користувач";
}

function apiErrorCode(reason: unknown): string {
  if (reason === null || typeof reason !== "object") {
    return "";
  }
  const value = (reason as ApiErrorShape).code;
  return typeof value === "string" ? value : "";
}

function apiErrorStatus(reason: unknown): number | undefined {
  if (reason === null || typeof reason !== "object") {
    return undefined;
  }
  const value = (reason as ApiErrorShape).status;
  return typeof value === "number" ? value : undefined;
}

function isBackendUnavailable(reason: unknown): boolean {
  const code = apiErrorCode(reason);
  const status = apiErrorStatus(reason);
  return (
    reason instanceof TypeError ||
    code === "backend_unavailable" ||
    code === "backend_waking" ||
    status === 502 ||
    status === 503 ||
    status === 504
  );
}

function errorMessage(reason: unknown): string {
  return reason instanceof Error
    ? reason.message
    : "Не вдалося підтвердити Telegram-профіль.";
}

export function MiniAppProvider({ children }: { children: React.ReactNode }) {
  const telegram = useTelegram();
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [locale, setLocaleState] = useState<MiniAppLocale>("uk");
  const [connection, setConnection] = useState<ConnectionState>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [authStatus, setAuthStatus] = useState<AuthStatus>("booting");
  const [authError, setAuthError] = useState("");
  const [authErrorCode, setAuthErrorCode] = useState("");
  const [authRetryKey, setAuthRetryKey] = useState(0);
  const [healthRetryKey, setHealthRetryKey] = useState(0);
  const [backendWakeAttempt, setBackendWakeAttempt] = useState(0);

  useEffect(() => {
    const stored = window.localStorage.getItem("flathunter-locale");
    if (stored === "uk" || stored === "en") {
      setLocaleState(stored);
      return;
    }
    if (telegram.languageCode.toLowerCase().startsWith("en")) {
      setLocaleState("en");
    }
  }, [telegram.languageCode]);

  useEffect(() => {
    const controller = new AbortController();
    let retryTimer: number | undefined;

    const scheduleRetry = () => {
      retryTimer = window.setTimeout(() => {
        setHealthRetryKey((current) => current + 1);
      }, BACKEND_RETRY_DELAY_MS);
    };

    const checkHealth = async () => {
      if (!navigator.onLine) {
        setConnection("offline");
        return;
      }
      setConnection((current) => (current === "waking" ? "waking" : "checking"));
      try {
        const response = await fetchBackendHealth(controller.signal);
        setHealth(response);
        setBackendWakeAttempt(0);
        setConnection(response.status === "ready" ? "ready" : "degraded");
      } catch (reason: unknown) {
        if (controller.signal.aborted) {
          return;
        }
        if (isBackendUnavailable(reason)) {
          setConnection("waking");
          setBackendWakeAttempt((current) => current + 1);
          scheduleRetry();
          return;
        }
        setConnection("degraded");
      }
    };

    const handleOnline = () => {
      setHealthRetryKey((current) => current + 1);
    };
    const handleOffline = () => {
      setConnection("offline");
    };

    void checkHealth();
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      controller.abort();
      if (retryTimer !== undefined) {
        window.clearTimeout(retryTimer);
      }
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [healthRetryKey]);

  useEffect(() => {
    if (!telegram.isReady) {
      setAuthStatus("booting");
      setUser(null);
      return;
    }
    if (!telegram.isTelegram || telegram.initData.length === 0) {
      setAuthStatus("preview");
      setAuthError("");
      setAuthErrorCode("");
      setUser(null);
      return;
    }
    if (
      connection === "checking" ||
      connection === "waking" ||
      connection === "offline"
    ) {
      setAuthStatus("waiting_backend");
      setAuthError("");
      setAuthErrorCode("");
      setUser(null);
      return;
    }

    const controller = new AbortController();
    setAuthStatus("authenticating");
    setAuthError("");
    setAuthErrorCode("");
    authenticateTelegram(telegram.initData, controller.signal)
      .then((response) => {
        if (controller.signal.aborted) {
          return;
        }
        setUser(response.user);
        setAuthStatus("authenticated");
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setUser(null);
        if (isBackendUnavailable(reason)) {
          setConnection("waking");
          setBackendWakeAttempt((current) => Math.max(current, 1));
          setAuthStatus("waiting_backend");
          setAuthError("");
          setAuthErrorCode(apiErrorCode(reason));
          setHealthRetryKey((current) => current + 1);
          return;
        }
        setAuthError(errorMessage(reason));
        setAuthErrorCode(apiErrorCode(reason));
        setAuthStatus("error");
      });

    return () => {
      controller.abort();
    };
  }, [
    authRetryKey,
    connection,
    telegram.initData,
    telegram.isReady,
    telegram.isTelegram,
  ]);

  useEffect(() => {
    if (authStatus === "authenticated" && user !== null) {
      window.dispatchEvent(new Event(TELEGRAM_AUTHENTICATED_EVENT));
    }
  }, [authStatus, user]);

  const retryAuthentication = useCallback(() => {
    setAuthError("");
    setAuthErrorCode("");
    if (connection === "waking" || connection === "offline") {
      setBackendWakeAttempt(0);
      setConnection(navigator.onLine ? "checking" : "offline");
      setHealthRetryKey((current) => current + 1);
    }
    setAuthRetryKey((current) => current + 1);
  }, [connection]);

  const setLocale = useCallback((nextLocale: MiniAppLocale) => {
    setLocaleState(nextLocale);
    window.localStorage.setItem("flathunter-locale", nextLocale);
    triggerSelectionFeedback();
  }, []);

  const value = useMemo<MiniAppContextValue>(
    () => ({
      telegram,
      user,
      displayName: resolveDisplayName(user?.firstName, telegram.firstName),
      locale,
      setLocale,
      connection,
      health,
      authStatus,
      authError,
      authErrorCode,
      backendWakeAttempt,
      authFailed: authStatus === "error",
      isAuthenticated: authStatus === "authenticated",
      retryAuthentication,
    }),
    [
      authError,
      authErrorCode,
      authStatus,
      backendWakeAttempt,
      connection,
      health,
      locale,
      retryAuthentication,
      setLocale,
      telegram,
      user,
    ],
  );

  return (
    <MiniAppContext.Provider value={value}>{children}</MiniAppContext.Provider>
  );
}

export function useMiniApp(): MiniAppContextValue {
  const value = useContext(MiniAppContext);
  if (!value) {
    throw new Error("useMiniApp must be used inside MiniAppProvider");
  }
  return value;
}
