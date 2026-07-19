import type { ComponentType, ReactNode } from "react";

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  telegram: {
    isReady: true,
    isTelegram: true,
    initData: "query_id=valid",
    firstName: "Дмитро",
    languageCode: "uk",
    colorScheme: "light" as const,
  },
  authenticateTelegram: vi.fn(),
  fetchBackendHealth: vi.fn(),
}));

vi.mock("@/hooks/use-telegram", () => ({
  useTelegram: () => mocks.telegram,
}));

vi.mock("@/lib/api", () => ({
  TELEGRAM_AUTHENTICATED_EVENT: "flathunter:authenticated",
  authenticateTelegram: mocks.authenticateTelegram,
  fetchBackendHealth: mocks.fetchBackendHealth,
}));

vi.mock("@/lib/telegram", () => ({
  triggerSelectionFeedback: vi.fn(),
}));

type AuthStatus =
  | "booting"
  | "preview"
  | "waiting_backend"
  | "authenticating"
  | "authenticated"
  | "error";

type ContextValue = {
  authStatus: AuthStatus;
  isAuthenticated: boolean;
  user: { firstName: string } | null;
  retryAuthentication: () => void;
};

type ContextModule = {
  MiniAppProvider: ComponentType<{ children: ReactNode }>;
  useMiniApp: () => ContextValue;
};

const contextImportPath = "@/components/miniapp-context";

async function loadContext(): Promise<ContextModule> {
  const imported: unknown = await import(contextImportPath);
  return imported as ContextModule;
}

const backendHealth = {
  status: "ready" as const,
  service: "flathunter-backend",
  checks: { database: "ok", cache: "ok" },
};

const authenticatedResponse = {
  user: {
    id: "user-1",
    telegramId: 123,
    firstName: "Дмитро",
    lastName: "",
    username: "Ke1fosao",
    locale: "uk",
    role: "user",
  },
  csrfToken: "csrf-token",
};

describe("MiniAppProvider authentication", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mocks.telegram.isReady = true;
    mocks.telegram.isTelegram = true;
    mocks.telegram.initData = "query_id=valid";
    mocks.authenticateTelegram.mockReset();
    mocks.fetchBackendHealth.mockReset();
    mocks.fetchBackendHealth.mockResolvedValue(backendHealth);
    Object.defineProperty(window.navigator, "onLine", {
      configurable: true,
      value: true,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("stays in booting until Telegram initialization is resolved", async () => {
    const { MiniAppProvider, useMiniApp } = await loadContext();
    mocks.telegram.isReady = false;

    function Probe() {
      return <span>{useMiniApp().authStatus}</span>;
    }

    render(
      <MiniAppProvider>
        <Probe />
      </MiniAppProvider>,
    );

    expect(screen.getByText("booting")).toBeInTheDocument();
    expect(mocks.authenticateTelegram).not.toHaveBeenCalled();
  });

  it("uses preview mode outside Telegram without protected authentication", async () => {
    const { MiniAppProvider, useMiniApp } = await loadContext();
    mocks.telegram.isTelegram = false;
    mocks.telegram.initData = "";

    function Probe() {
      return <span>{useMiniApp().authStatus}</span>;
    }

    render(
      <MiniAppProvider>
        <Probe />
      </MiniAppProvider>,
    );

    expect(await screen.findByText("preview")).toBeInTheDocument();
    expect(mocks.authenticateTelegram).not.toHaveBeenCalled();
  });

  it("waits for backend readiness before authenticating Telegram", async () => {
    const { MiniAppProvider, useMiniApp } = await loadContext();
    let resolveHealth: ((value: typeof backendHealth) => void) | undefined;
    mocks.fetchBackendHealth.mockReturnValue(
      new Promise((resolve) => {
        resolveHealth = resolve;
      }),
    );
    mocks.authenticateTelegram.mockResolvedValue(authenticatedResponse);

    function Probe() {
      return <span>{useMiniApp().authStatus}</span>;
    }

    render(
      <MiniAppProvider>
        <Probe />
      </MiniAppProvider>,
    );

    expect(await screen.findByText("waiting_backend")).toBeInTheDocument();
    expect(mocks.authenticateTelegram).not.toHaveBeenCalled();

    act(() => {
      if (resolveHealth === undefined) {
        throw new Error("Health resolver was not initialized");
      }
      resolveHealth(backendHealth);
    });

    expect(await screen.findByText("authenticated")).toBeInTheDocument();
    expect(mocks.authenticateTelegram).toHaveBeenCalledTimes(1);
  });

  it("retries a sleeping backend automatically and authenticates after recovery", async () => {
    vi.useFakeTimers();
    const { MiniAppProvider, useMiniApp } = await loadContext();
    const backendUnavailable = Object.assign(new Error("Backend unavailable"), {
      code: "backend_unavailable",
      status: 502,
    });
    mocks.fetchBackendHealth
      .mockRejectedValueOnce(backendUnavailable)
      .mockResolvedValueOnce(backendHealth);
    mocks.authenticateTelegram.mockResolvedValue(authenticatedResponse);

    function Probe() {
      return <span>{useMiniApp().authStatus}</span>;
    }

    render(
      <MiniAppProvider>
        <Probe />
      </MiniAppProvider>,
    );

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText("waiting_backend")).toBeInTheDocument();
    expect(mocks.authenticateTelegram).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.getByText("authenticated")).toBeInTheDocument();
    expect(mocks.fetchBackendHealth).toHaveBeenCalledTimes(2);
    expect(mocks.authenticateTelegram).toHaveBeenCalledTimes(1);
  });

  it("publishes authenticated state before the authenticated event", async () => {
    const { MiniAppProvider, useMiniApp } = await loadContext();
    mocks.authenticateTelegram.mockResolvedValue(authenticatedResponse);
    let statusWhenEvent = "";
    const onAuthenticated = () => {
      statusWhenEvent = screen.getByTestId("auth-status").textContent;
    };
    window.addEventListener("flathunter:authenticated", onAuthenticated);

    function Probe() {
      const context = useMiniApp();
      return (
        <div>
          <span data-testid="auth-status">{context.authStatus}</span>
          <span>{context.user?.firstName ?? "none"}</span>
        </div>
      );
    }

    render(
      <MiniAppProvider>
        <Probe />
      </MiniAppProvider>,
    );

    expect(await screen.findByText("authenticated")).toBeInTheDocument();
    expect(screen.getByText("Дмитро")).toBeInTheDocument();
    await waitFor(() => {
      expect(statusWhenEvent).toBe("authenticated");
    });
    window.removeEventListener("flathunter:authenticated", onAuthenticated);
  });

  it("supports retrying a failed authentication", async () => {
    const { MiniAppProvider, useMiniApp } = await loadContext();
    mocks.authenticateTelegram
      .mockRejectedValueOnce(new Error("invalid initData"))
      .mockResolvedValueOnce(authenticatedResponse);

    function Probe() {
      const context = useMiniApp();
      return (
        <div>
          <span>{context.authStatus}</span>
          <button type="button" onClick={context.retryAuthentication}>
            Retry auth
          </button>
        </div>
      );
    }

    render(
      <MiniAppProvider>
        <Probe />
      </MiniAppProvider>,
    );

    expect(await screen.findByText("error")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry auth" }));
    expect(await screen.findByText("authenticated")).toBeInTheDocument();
    expect(mocks.authenticateTelegram).toHaveBeenCalledTimes(2);
  });
});
