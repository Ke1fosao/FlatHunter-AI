"use client";

import { useState } from "react";

import { AppShell } from "@/components/app-shell";
import { ListingFeed } from "@/components/listing-feed";
import { SearchWizard } from "@/components/search-wizard";

export function StageFourShell() {
  const [open, setOpen] = useState(false);
  const [created, setCreated] = useState(false);

  return (
    <>
      <AppShell
        activeNavigation="search"
        onCreateSearch={() => { setOpen(true); }}
        onNavigate={(target) => { void target; }}
      />
      <ListingFeed />
      <button
        className="stage-four-create"
        type="button"
        onClick={() => {
          setOpen(true);
        }}
      >
        ＋ Створити пошук
      </button>
      {created && <div className="stage-four-toast">✅ Пошуковий профіль створено</div>}
      {open && (
        <SearchWizard
          onClose={() => {
            setOpen(false);
          }}
          onCreated={() => {
            setOpen(false);
            setCreated(true);
            window.dispatchEvent(new Event("flathunter:authenticated"));
            window.setTimeout(() => {
              setCreated(false);
            }, 3000);
          }}
        />
      )}
      <style jsx global>{`
        .stage-four-create{position:fixed;right:20px;bottom:calc(92px + env(safe-area-inset-bottom,0px));z-index:30;border:0;border-radius:18px;padding:14px 18px;background:var(--accent);color:var(--accent-text);font-weight:800;box-shadow:0 14px 34px color-mix(in srgb,var(--accent) 35%,transparent)}
        .stage-four-toast{position:fixed;left:50%;bottom:calc(150px + env(safe-area-inset-bottom,0px));z-index:60;transform:translateX(-50%);padding:12px 16px;border-radius:14px;background:#17251c;color:white;box-shadow:var(--shadow);white-space:nowrap}
        @media(max-width:620px){.stage-four-create{right:14px;bottom:calc(86px + env(safe-area-inset-bottom,0px));padding:13px 15px}}
      `}</style>
    </>
  );
}
