export function getTelegramWebApp(): TelegramWebApp | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }
  return window.Telegram?.WebApp;
}

export function initializeTelegramWebApp(): TelegramWebApp | undefined {
  const webApp = getTelegramWebApp();
  if (!webApp) {
    return undefined;
  }

  webApp.ready();
  if (!webApp.isExpanded) {
    webApp.expand();
  }
  webApp.enableClosingConfirmation?.();
  return webApp;
}

export function triggerSelectionFeedback(): void {
  getTelegramWebApp()?.HapticFeedback?.selectionChanged();
}
