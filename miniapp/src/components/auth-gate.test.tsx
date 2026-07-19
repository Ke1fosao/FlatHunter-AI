import { existsSync } from "node:fs";
import { join } from "node:path";
import type { ComponentType, ReactNode } from "react";

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  context: {
    authStatus: "booting",
    connection: "checking",
    retryAuthentication: vi.fn(),
  },
}));

vi.mock("@/components/miniapp-context", () => ({
  useMiniApp: () => mocks.context,
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

  it("shows a Telegram preview explanation outside Telegram", async () => {
    expect(existsSync(modulePath), "auth-gate.tsx must exist").toBe(true);
    const { AuthGate } = await loadGate();
    mocks.context.authStatus = "preview";
    mocks.context.connection = "ready";

    render(
      <AuthGate>
        <div>Захищений кабінет</div>
      </AuthGate>,
    );

    expect(
      screen.getByRole("heading", { name: "Відкрийте FlatHunter у Telegram" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Захищений кабінет")).not.toBeInTheDocument();
  });

  it("shows a deterministic authentication progress state", async () => {
    expect(existsSync(modulePath), "auth-gate.tsx must exist").toBe(true);
    const { AuthGate } = await loadGate();
    mocks.context.authStatus = "authenticating";

    render(
      <AuthGate>
        <div>Захищений кабінет</div>
      </AuthGate>,
    );

    expect(screen.getByText("Підключаю Telegram-профіль…")).toBeInTheDocument();
  });

  it("shows an offline state before a generic auth error", async () => {
    expect(existsSync(modulePath), "auth-gate.tsx must exist").toBe(true);
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

  it("allows retrying failed Telegram authentication", async () => {
    expect(existsSync(modulePath), "auth-gate.tsx must exist").toBe(true);
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
