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

export type MiniAppLocale = "uk" | "en";
export type ConnectionState = "checking" | "ready" | "degraded" | "offline";
export type AuthStatus =
  | "booting"
  | "preview"
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
  authFailed: boolean;
  isAuthenticated: boolean;
  retryAuthentication: () => void;
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

export function MiniAppProvider({ children }: { children: React.ReactNode }) {
  const telegram = useTelegram();
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [locale, setLocaleState] = useState<MiniAppLocale>("uk");
  const [connection, setConnection] = useState<ConnectionState>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [authStatus, setAuthStatus] = useState<AuthStatus>("booting");
  const [authError, setAuthError] = useState("");
  const [authRetryKey, setAuthRetryKey] = useState(0);

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

    const checkHealth = async () => {
      if (!navigator.onLine) {
        setConnection("offline");
        return;
      }
      setConnection("checking");
      try {
        const response = await fetchBackendHealth(controller.signal);
        setHealth(response);
        setConnection(response.status === "ready" ? "ready" : "degraded");
      } catch {
        if (!controller.signal.aborted) {
          setConnection(navigator.onLine ? "degraded" : "offline");
        }
      }
    };

    const handleOnline = () => {
      void checkHealth();
    };
    const handleOffline = () => {
      setConnection("offline");
    };

    void checkHealth();
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      controller.abort();
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  useEffect(() => {
    if (!telegram.isReady) {
      setAuthStatus("booting");
      setUser(null);
      return;
    }
    if (!telegram.isTelegram || telegram.initData.length === 0) {
      setAuthStatus("preview");
      setAuthError("");
      setUser(null);
      return;
    }

    const controller = new AbortController();
    setAuthStatus("authenticating");
    setAuthError("");
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
        setAuthError(
          reason instanceof Error
            ? reason.message
            : "Не вдалося підтвердити Telegram-профіль.",
        );
        setAuthStatus("error");
      });

    return () => {
      controller.abort();
    };
  }, [authRetryKey, telegram.initData, telegram.isReady, telegram.isTelegram]);

  useEffect(() => {
    if (authStatus === "authenticated" && user !== null) {
      window.dispatchEvent(new Event(TELEGRAM_AUTHENTICATED_EVENT));
    }
  }, [authStatus, user]);

  const retryAuthentication = useCallback(() => {
    setAuthRetryKey((current) => current + 1);
  }, []);

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
      authFailed: authStatus === "error",
      isAuthenticated: authStatus === "authenticated",
      retryAuthentication,
    }),
    [
      authError,
      authStatus,
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
