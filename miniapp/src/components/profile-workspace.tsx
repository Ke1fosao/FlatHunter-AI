"use client";

import type { AppNavigationTarget } from "@/components/app-shell";
import { useTelegram } from "@/hooks/use-telegram";

type ProfileWorkspaceProps = {
  onCreateSearch: () => void;
  onNavigate: (target: AppNavigationTarget) => void;
};

export function ProfileWorkspace({ onCreateSearch, onNavigate }: ProfileWorkspaceProps) {
  const telegram = useTelegram();
  const displayName = telegram.firstName.trim() || "Користувач FlatHunter";

  return (
    <section className="profile-workspace" role="region" aria-label="Профіль користувача">
      <div className="profile-workspace__card">
        <div className="profile-workspace__avatar" aria-hidden="true">
          {displayName.slice(0, 1).toUpperCase()}
        </div>
        <div>
          <span>ПРОФІЛЬ</span>
          <h2>{displayName}</h2>
          <p>
            {telegram.isTelegram
              ? "Профіль підключено до Telegram Mini App."
              : "Відкрийте застосунок у Telegram для захищеної авторизації."}
          </p>
        </div>
      </div>

      <div className="profile-workspace__grid">
        <article>
          <span>Мова Telegram</span>
          <strong>{telegram.languageCode.toUpperCase()}</strong>
        </article>
        <article>
          <span>Тема</span>
          <strong>{telegram.colorScheme === "dark" ? "Темна" : "Світла"}</strong>
        </article>
        <article>
          <span>Режим</span>
          <strong>{telegram.isTelegram ? "Telegram" : "Preview"}</strong>
        </article>
      </div>

      <div className="profile-workspace__actions">
        <button type="button" className="button button--primary" onClick={onCreateSearch}>
          ＋ Новий пошук
        </button>
        <button type="button" className="button button--secondary" onClick={() => { onNavigate("favorites"); }}>
          Відкрити обране
        </button>
        <button type="button" className="button button--secondary" onClick={() => { onNavigate("ai"); }}>
          Відкрити AI
        </button>
      </div>

      <style jsx>{`
        .profile-workspace{width:min(900px,calc(100% - 28px));margin:24px auto 140px}.profile-workspace__card{display:flex;align-items:center;gap:18px;padding:26px;border:1px solid var(--line);border-radius:28px;background:var(--surface-solid);box-shadow:var(--shadow)}.profile-workspace__avatar{display:grid;place-items:center;flex:0 0 72px;width:72px;height:72px;border-radius:24px;background:linear-gradient(145deg,var(--accent),color-mix(in srgb,var(--accent) 65%,#071a10));color:var(--accent-text);font-size:30px;font-weight:900}.profile-workspace__card span{color:var(--accent);font-size:10px;font-weight:900;letter-spacing:.14em}.profile-workspace__card h2{margin:5px 0 7px;font-size:28px}.profile-workspace__card p{margin:0;color:var(--muted)}.profile-workspace__grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px}.profile-workspace__grid article{display:grid;gap:8px;padding:18px;border:1px solid var(--line);border-radius:20px;background:var(--surface-solid)}.profile-workspace__grid span{color:var(--muted);font-size:12px}.profile-workspace__grid strong{font-size:18px}.profile-workspace__actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px;padding:18px;border:1px solid var(--line);border-radius:22px;background:var(--surface-solid)}@media(max-width:620px){.profile-workspace__card{align-items:flex-start;padding:20px}.profile-workspace__avatar{flex-basis:56px;width:56px;height:56px;border-radius:18px;font-size:24px}.profile-workspace__grid{grid-template-columns:1fr}.profile-workspace__actions{display:grid}.profile-workspace__actions button{width:100%}}
      `}</style>
    </section>
  );
}
