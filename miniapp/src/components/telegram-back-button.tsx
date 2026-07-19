"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { getTelegramWebApp, triggerSelectionFeedback } from "@/lib/telegram";

export function TelegramBackButton() {
  const pathname = usePathname();
  const router = useRouter();
  const visible = pathname.startsWith("/listings/");

  useEffect(() => {
    const backButton = getTelegramWebApp()?.BackButton;
    if (!backButton) {
      return;
    }

    if (!visible) {
      backButton.hide();
      return;
    }

    const handleBack = () => {
      triggerSelectionFeedback();
      if (window.history.length > 1) {
        router.back();
      } else {
        router.replace("/search");
      }
    };

    backButton.show();
    backButton.onClick(handleBack);
    return () => {
      backButton.offClick(handleBack);
      backButton.hide();
    };
  }, [router, visible]);

  if (!visible) {
    return null;
  }

  return (
    <button
      type="button"
      className="miniapp-inline-back"
      onClick={() => {
        triggerSelectionFeedback();
        if (window.history.length > 1) {
          router.back();
        } else {
          router.replace("/search");
        }
      }}
    >
      ← Назад
    </button>
  );
}
