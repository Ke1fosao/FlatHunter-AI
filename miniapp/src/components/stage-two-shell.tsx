"use client";

import { useState } from "react";

import { AppShell } from "@/components/app-shell";
import { SearchWizard } from "@/components/search-wizard";

export function StageTwoShell() {
  const [open, setOpen] = useState(false);
  const [created, setCreated] = useState(false);

  return (
    <>
      <AppShell
        activeNavigation="search"
        onCreateSearch={() => { setOpen(true); }}
        onNavigate={(target) => { void target; }}
      />
      <button className="stage-two-create" type="button" onClick={() => { setOpen(true); }}>
        ＋ Створити пошук
      </button>
      {created && <div className="stage-two-toast">✅ Пошуковий профіль створено</div>}
      {open && (
        <SearchWizard
          onClose={() => { setOpen(false); }}
          onCreated={() => {
            setOpen(false);
            setCreated(true);
            window.setTimeout(() => { setCreated(false); }, 3000);
          }}
        />
      )}
      <style jsx global>{`
        .stage-two-create{position:fixed;right:20px;bottom:calc(92px + env(safe-area-inset-bottom,0px));z-index:30;border:0;border-radius:18px;padding:14px 18px;background:var(--accent);color:var(--accent-text);font-weight:800;box-shadow:0 14px 34px color-mix(in srgb,var(--accent) 35%,transparent)}
        .stage-two-toast{position:fixed;left:50%;bottom:calc(150px + env(safe-area-inset-bottom,0px));z-index:60;transform:translateX(-50%);padding:12px 16px;border-radius:14px;background:#17251c;color:white;box-shadow:var(--shadow);white-space:nowrap}
        .wizard-backdrop{position:fixed;inset:0;z-index:80;display:flex;align-items:flex-end;justify-content:center;padding-top:env(safe-area-inset-top,0px);background:rgba(10,22,15,.48);backdrop-filter:blur(10px)}
        .wizard-sheet{width:min(100%,760px);max-height:92dvh;overflow:auto;padding:24px 20px calc(24px + env(safe-area-inset-bottom,0px));border-radius:28px 28px 0 0;background:var(--surface-solid);box-shadow:0 -30px 80px rgba(8,25,15,.28)}
        .wizard-header,.wizard-footer{display:flex;align-items:center;justify-content:space-between;gap:12px}.wizard-header h2{margin:4px 0 0}.wizard-close{width:42px;height:42px;border:1px solid var(--line);border-radius:14px;background:transparent;font-size:26px}.wizard-mode-switch{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:20px 0;padding:5px;border:1px solid var(--line);border-radius:16px;background:var(--bg)}.wizard-mode-switch button{border:0;border-radius:12px;padding:11px;background:transparent;font-weight:750}.wizard-mode-switch button.is-active{background:var(--surface-solid);box-shadow:0 4px 14px rgba(20,45,29,.08)}
        .wizard-progress{height:6px;margin:4px 0 22px;border-radius:99px;background:rgba(25,60,38,.08);overflow:hidden}.wizard-progress span{display:block;height:100%;background:var(--accent)}
        .wizard-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.wizard-grid label,.wizard-natural label{display:grid;gap:7px;color:var(--muted);font-size:12px;font-weight:750}.wizard-grid input,.wizard-grid select,.wizard-natural textarea{width:100%;border:1px solid var(--line);border-radius:14px;padding:13px 14px;background:var(--bg);color:var(--text);font:inherit}.wizard-natural textarea{min-height:170px;resize:vertical;margin-bottom:14px}
        .wizard-options{display:flex;flex-wrap:wrap;gap:10px}.option-chip{border:1px solid var(--line);border-radius:999px;padding:12px 14px;background:var(--bg);font-weight:700}.option-chip.is-active{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 12%,var(--surface-solid));color:var(--accent)}
        .wizard-review dl{display:grid;gap:10px}.wizard-review dl div{display:flex;justify-content:space-between;gap:16px;padding:13px 0;border-bottom:1px solid var(--line)}.wizard-review dt{color:var(--muted)}.wizard-review dd{margin:0;font-weight:800;text-align:right}.confidence-note{padding:12px;border-radius:14px;background:color-mix(in srgb,var(--accent) 10%,transparent);color:var(--muted);font-size:12px}.wizard-error{color:var(--danger);font-size:13px}.wizard-footer{margin-top:24px}.wizard-footer .button{min-width:130px}
        @media(max-width:620px){.wizard-grid{grid-template-columns:1fr}.stage-two-create{right:14px;bottom:calc(86px + env(safe-area-inset-bottom,0px));padding:13px 15px}.wizard-sheet{padding-left:16px;padding-right:16px}}
      `}</style>
    </>
  );
}
