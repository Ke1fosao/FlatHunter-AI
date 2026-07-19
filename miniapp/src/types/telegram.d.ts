export {};

declare global {
  type TelegramWebAppUser = {
    id: number;
    first_name: string;
    last_name?: string;
    username?: string;
    language_code?: string;
    is_premium?: boolean;
  };

  type TelegramBackButton = {
    isVisible?: boolean;
    show(): void;
    hide(): void;
    onClick(callback: () => void): void;
    offClick(callback: () => void): void;
  };

  type TelegramWebApp = {
    initData: string;
    initDataUnsafe?: {
      user?: TelegramWebAppUser;
      start_param?: string;
    };
    colorScheme: "light" | "dark";
    themeParams: Record<string, string>;
    isExpanded: boolean;
    ready(): void;
    expand(): void;
    close(): void;
    setHeaderColor?(color: string): void;
    setBackgroundColor?(color: string): void;
    enableClosingConfirmation?(): void;
    BackButton?: TelegramBackButton;
    HapticFeedback?: {
      impactOccurred(style: "light" | "medium" | "heavy" | "rigid" | "soft"): void;
      notificationOccurred(type: "error" | "success" | "warning"): void;
      selectionChanged(): void;
    };
  };

  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp;
    };
  }
}
