"use client";

import { useEffect, useState } from "react";

import { initializeTelegramWebApp } from "@/lib/telegram";

export type TelegramContext = {
  isReady: boolean;
  isTelegram: boolean;
  initData: string;
  firstName: string;
  languageCode: string;
  colorScheme: "light" | "dark";
};

const initialState: TelegramContext = {
  isReady: false,
  isTelegram: false,
  initData: "",
  firstName: "",
  languageCode: "uk",
  colorScheme: "light",
};

export function useTelegram(): TelegramContext {
  const [context, setContext] = useState<TelegramContext>(initialState);

  useEffect(() => {
    const webApp = initializeTelegramWebApp();
    if (!webApp) {
      setContext((current) => ({ ...current, isReady: true }));
      return;
    }

    setContext({
      isReady: true,
      isTelegram: true,
      initData: webApp.initData,
      firstName: webApp.initDataUnsafe?.user?.first_name ?? "",
      languageCode: webApp.initDataUnsafe?.user?.language_code ?? "uk",
      colorScheme: webApp.colorScheme,
    });
  }, []);

  return context;
}
