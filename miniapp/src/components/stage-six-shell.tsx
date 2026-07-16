"use client";

import { useState } from "react";

import { AppShell } from "@/components/app-shell";
import { ListingFeed } from "@/components/listing-feed";
import { MapWorkspace } from "@/components/map-workspace";
import { SearchWizard } from "@/components/search-wizard";

type StageSixView = "workspace" | "map";

export function StageSixShell() {
  const [view, setView] = useState<StageSixView>("workspace");
  const [open, setOpen] = useState(false);
  const [created, setCreated] = useState(false);

  return (
    <>
      <AppShell />
      <nav className="stage-six-switch" aria-label="Режим перегляду">
        <button
          type="button"
          className={view === "workspace" ? "is-active" : ""}
          onClick={() => { setView("workspace"); }}
        >
          ▦ Кабінет
        </button>
        <button
          type="button"
          className={view === "map" ? "is-active" : ""}
          onClick={() => { setView("map"); }}
        >
          ◉ Карта
        </button>
      </nav>
      {view === "workspace" ? <ListingFeed /> : <MapWorkspace />}
      <button className="stage-six-create" type="button" onClick={() => { setOpen(true); }}>
        ＋ Створити пошук
      </button>
      {created && <div className="stage-six-toast">✅ Пошуковий профіль створено</div>}
      {open && (
        <SearchWizard
          onClose={() => { setOpen(false); }}
          onCreated={() => {
            setOpen(false);
            setCreated(true);
            window.dispatchEvent(new Event("flathunter:authenticated"));
            window.setTimeout(() => { setCreated(false); }, 3000);
          }}
        />
      )}
    </>
  );
}
