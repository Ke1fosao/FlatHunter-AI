"use client";

import { AuthGate } from "@/components/auth-gate";
import { BottomNavigation } from "@/components/bottom-navigation";
import { MiniAppHeader } from "@/components/miniapp-header";
import { MiniAppProvider } from "@/components/miniapp-context";
import { TelegramBackButton } from "@/components/telegram-back-button";

export function MiniAppShell({ children }: { children: React.ReactNode }) {
  return (
    <MiniAppProvider>
      <div className="miniapp-shell">
        <div className="miniapp-ambient miniapp-ambient--one" />
        <div className="miniapp-ambient miniapp-ambient--two" />
        <MiniAppHeader />
        <TelegramBackButton />
        <main id="miniapp-main" className="miniapp-content">
          <AuthGate>{children}</AuthGate>
        </main>
        <BottomNavigation />
      </div>
    </MiniAppProvider>
  );
}
