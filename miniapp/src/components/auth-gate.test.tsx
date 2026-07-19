import { existsSync } from "node:fs";
import { join } from "node:path";
import type { ComponentType, ReactNode } from "react";

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  context: {
    authStatus: "booting",
    authError: "",
    authErrorCode: "",
    backendWakeAttempt: 0,
    connection: "checking",
    retryAuthentication: vi.fn(),
  },
}));

vi.mock("@/components/miniapp-context", () => ({
  useMiniApp: () => mocks.context,
}));

vi.mock("@/components/preview-hub", () => ({
  PreviewHub: () => <div>Повна демо-версія FlatHunter</div>,
}));

type AuthGateModule = {
  AuthGate: ComponentType<{ children: ReactNode }>;
};

const modulePath = join(process.cwd(), "src/components/auth-gate.tsx");
const importPath = "@/components/auth-gate";

async function loadGate(): Promise<AuthGateModule> {
  const imported: unknown = await import(importPath);
  return imported as AuthGateModule;
}

describe("AuthGate", () => {
  beforeEach(() => {
    mocks.context.authStatus = "booting";
    mocks.context.authError = "";
    mocks.context.authErrorCode = "";
    mocks.context.backendWakeAttempt = 0;
    mocks.context.connection = "checking";
    mocks.context.retryAuthentication.mockReset();
  });

  it("renders protected content only after Telegram authentication", async () => {
    expect(existsSync(modulePath), "auth-gate.tsx must exist").toBe(true);
    const { AuthGate } = await loadGate();
    mocks.context.authStatus = "authenticated";
    mocks.context.connection = "ready";

    render(
      <AuthGate>
        <div>Захищений кабінет</div>
      </AuthGate>,
    );

    expect(screen.getByText("Захищений кабінет")).toBeInTheDocument();
  });

  it("renders a complete interactive browser demo outside Telegram", async () => {
    const { AuthGate } = await loadGate();
    mocks.context.authStatus = "preview";
    mocks.context.connection = "ready";

    render(
      <AuthGate>
        <div>Захищений кабінет</div>
      </AuthGate>,
    );

    expect(screen.getByText("Повна демо-версія FlatHunter")).toBeInTheDocument();
    expect(screen.queryByText("Захищений кабінет")).not.toBeInTheDocument();
  });

  it("shows a clear backend wake-up state while the free server starts", async () => {
    const { AuthGate } = await loadGate();
    mocks.context.authStatus = "waiting_backend";
    mocks.context.connection = "waking";
    mocks.context.backendWakeAttempt = 2;

    render(
      <AuthGate>
        <div>Захищений кабінет</div>
      </AuthGate>,
    );

    expect(
      screen.getByRole("heading", { name: "Запускаю сервер FlatHunter…" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/20–60 секунд/)).toBeInTheDocument();
    expect(screen.getByText(/спроба 2/)).toBeInTheDocument();
  });

  it("shows a deterministic authentication progress state", async () => {
    const { AuthGate } = await loadGate();
    mocks.context.authStatus = "authenticating";
    mocks.context.connection = "ready";

    render(
      <AuthGate>
        <div>Захищений кабінет</div>
      </AuthGate>,
    );

    expect(screen.getByText("Перевіряю Telegram-профіль…")).toBeInTheDocument();
  });

  it("shows an offline state before a generic auth error", async () => {
    const { AuthGate } = await loadGate();
    mocks.context.authStatus = "error";
    mocks.context.connection = "offline";

    render(
      <AuthGate>
        <div>Захищений кабінет</div>
      </AuthGate>,
    );

    expect(screen.getByRole("heading", { name: "Немає з’єднання" })).toBeInTheDocument();
  });

  it("replaces raw Telegram signature errors with an actionable explanation", async () => {
    const { AuthGate } = await loadGate();
    mocks.context.authStatus = "error";
    mocks.context.connection = "ready";
    mocks.context.authErrorCode = "invalid_telegram_data";
    mocks.context.authError = "Telegram signature is invalid";

    render(
      <AuthGate>
        <div>Захищений кабінет</div>
      </AuthGate>,
    );

    expect(
      screen.getByRole("heading", { name: "Telegram не підтвердив вхід" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/закрийте Mini App/i)).toBeInTheDocument();
    expect(screen.queryByText("Telegram signature is invalid")).not.toBeInTheDocument();
  });

  it("allows retrying failed Telegram authentication", async () => {
    const { AuthGate } = await loadGate();
    mocks.context.authStatus = "error";
    mocks.context.connection = "ready";

    render(
      <AuthGate>
        <div>Захищений кабінет</div>
      </AuthGate>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Спробувати ще раз" }));
    expect(mocks.context.retryAuthentication).toHaveBeenCalledTimes(1);
  });
});
