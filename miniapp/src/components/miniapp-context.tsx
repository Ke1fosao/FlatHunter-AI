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
  type AuthenticatedUser,
  type HealthResponse,
} from "@/lib/api";
import { triggerSelectionFeedback } from "@/lib/telegram";

export type MiniAppLocale = "uk" | "en";
export type ConnectionState = "checking" | "ready" | "degraded" | "offline";

type MiniAppContextValue = {
  telegram: TelegramContext;
  user: AuthenticatedUser | null;
  displayName: string;
  locale: MiniAppLocale;
  setLocale: (locale: MiniAppLocale) => void;
  connection: ConnectionState;
  health: HealthResponse | null;
  authFailed: boolean;
};

const MiniAppContext = createContext<MiniAppContextValue | null>(null);

export function MiniAppProvider({ children }: { children: React.ReactNode }) {
  const telegram = useTelegram();
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [locale, setLocaleState] = useState<MiniAppLocale>("uk");
  const [connection, setConnection] = useState<ConnectionState>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [authFailed, setAuthFailed] = useState(false);

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
    if (!telegram.initData) {
      return;
    }
    const controller = new AbortController();
    authenticateTelegram(telegram.initData, controller.signal)
      .then((response) => {
        setUser(response.user);
        setAuthFailed(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setAuthFailed(true);
        }
      });
    return () => {
      controller.abort();
    };
  }, [telegram.initData]);

  const setLocale = useCallback((nextLocale: MiniAppLocale) => {
    setLocaleState(nextLocale);
    window.localStorage.setItem("flathunter-locale", nextLocale);
    triggerSelectionFeedback();
  }, []);

  const value = useMemo<MiniAppContextValue>(
    () => ({
      telegram,
      user,
      displayName:
        user?.firstName.trim() || telegram.firstName.trim() || "Користувач",
      locale,
      setLocale,
      connection,
      health,
      authFailed,
    }),
    [authFailed, connection, health, locale, setLocale, telegram, user],
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
