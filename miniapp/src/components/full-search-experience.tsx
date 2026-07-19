"use client";

import Link from "next/link";
import { useState } from "react";

import { AIAssistantWorkspace } from "@/components/ai-assistant-workspace";
import { ClusterBrowser } from "@/components/cluster-browser";
import { ListingFeed } from "@/components/listing-feed";
import { SearchHome } from "@/components/search-home";

type SearchView = "overview" | "clusters" | "cabinet" | "ai";

const localViews: readonly { id: SearchView; label: string; description: string }[] = [
  { id: "overview", label: "Огляд", description: "Профілі, статистика та кластеризована стрічка" },
  { id: "clusters", label: "Оголошення", description: "Усі квартири без дублів та з Risk Score" },
  { id: "cabinet", label: "Кабінет", description: "Збіги, обране, фільтри та порівняння" },
  { id: "ai", label: "AI", description: "Резюме, питання власнику та підказки" },
];

const routedViews = [
  { href: "/map", label: "Карта", icon: "◉" },
  { href: "/favorites", label: "Обране", icon: "♡" },
  { href: "/compare", label: "Порівняння", icon: "⇄" },
  { href: "/profile", label: "Профіль", icon: "◎" },
] as const;

export function FullSearchExperience() {
  const [view, setView] = useState<SearchView>("overview");

  return (
    <div className="full-search-experience">
      <section className="full-search-launcher" aria-label="Всі інструменти FlatHunter">
        <div className="full-search-launcher__copy">
          <span>ПОВНИЙ ФУНКЦІОНАЛ</span>
          <h1>Усі можливості FlatHunter тепер підключені до сайту</h1>
          <p>
            Перемикайтеся між повним пошуком, кластеризованими оголошеннями,
            кабінетом та AI. Карта, обране, порівняння й профіль відкриваються
            окремими маршрутами та зберігають той самий стан у backend.
          </p>
        </div>

        <div className="full-search-launcher__modes" role="tablist" aria-label="Робочий простір">
          {localViews.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={view === item.id}
              className={view === item.id ? "is-active" : undefined}
              onClick={() => {
                setView(item.id);
              }}
            >
              <strong>{item.label}</strong>
              <small>{item.description}</small>
            </button>
          ))}
        </div>

        <nav className="full-search-launcher__routes" aria-label="Інші розділи">
          {routedViews.map((item) => (
            <Link key={item.href} href={item.href}>
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>
      </section>

      <section className={`full-search-view full-search-view--${view}`}>
        {view === "overview" && <SearchHome />}
        {view === "clusters" && <ClusterBrowser />}
        {view === "cabinet" && <ListingFeed initialTab="dashboard" />}
        {view === "ai" && (
          <div className="full-search-ai">
            <header>
              <span>AI-ПОМІЧНИК</span>
              <h2>Повний AI-простір для перевірки квартири</h2>
              <p>
                Формуйте критерії природною мовою, отримуйте резюме оголошень,
                питання власнику та пояснення ризиків.
              </p>
            </header>
            <AIAssistantWorkspace />
          </div>
        )}
      </section>

      <style jsx global>{`
        .full-search-experience {
          min-width: 0;
        }
        .full-search-launcher {
          width: min(1180px, calc(100% - 28px));
          margin: 18px auto 8px;
          padding: 22px;
          display: grid;
          gap: 16px;
          border: 1px solid var(--line);
          border-radius: 26px;
          background:
            radial-gradient(circle at 90% 10%, color-mix(in srgb, var(--accent) 18%, transparent), transparent 34%),
            linear-gradient(145deg, color-mix(in srgb, var(--accent) 8%, var(--surface-solid)), var(--surface-solid));
          box-shadow: var(--shadow);
        }
        .full-search-launcher__copy span,
        .full-search-ai > header span {
          font-size: 10px;
          font-weight: 900;
          letter-spacing: 0.14em;
          color: var(--accent);
        }
        .full-search-launcher__copy h1 {
          margin: 7px 0 8px;
          max-width: 820px;
          font-size: clamp(24px, 4vw, 42px);
          line-height: 1.04;
        }
        .full-search-launcher__copy p,
        .full-search-ai > header p {
          max-width: 850px;
          margin: 0;
          color: var(--muted);
          line-height: 1.6;
        }
        .full-search-launcher__modes {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 9px;
        }
        .full-search-launcher__modes button {
          min-height: 74px;
          padding: 13px 14px;
          display: grid;
          gap: 4px;
          text-align: left;
          border: 1px solid var(--line);
          border-radius: 17px;
          background: color-mix(in srgb, var(--surface-solid) 92%, transparent);
          color: var(--text);
          cursor: pointer;
          transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
        }
        .full-search-launcher__modes button:hover {
          transform: translateY(-2px);
        }
        .full-search-launcher__modes button.is-active {
          border-color: var(--accent);
          background: color-mix(in srgb, var(--accent) 13%, var(--surface-solid));
        }
        .full-search-launcher__modes strong {
          font-size: 14px;
        }
        .full-search-launcher__modes small {
          color: var(--muted);
          line-height: 1.35;
        }
        .full-search-launcher__routes {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 9px;
        }
        .full-search-launcher__routes a {
          min-height: 46px;
          padding: 0 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          border: 1px solid var(--line);
          border-radius: 14px;
          background: var(--bg);
          color: var(--text);
          font-weight: 850;
          text-decoration: none;
        }
        .full-search-launcher__routes a:hover {
          border-color: var(--accent);
          color: var(--accent);
        }
        .full-search-view {
          min-width: 0;
        }
        .full-search-view--clusters .cluster-browser,
        .full-search-view--cabinet .listing-workspace {
          margin-top: 16px;
        }
        .full-search-ai {
          width: min(1180px, calc(100% - 28px));
          margin: 18px auto 120px;
          padding: 22px;
          display: grid;
          gap: 18px;
          border: 1px solid var(--line);
          border-radius: 24px;
          background: var(--surface-solid);
          box-shadow: var(--shadow);
        }
        .full-search-ai > header h2 {
          margin: 6px 0 7px;
        }
        @media (max-width: 760px) {
          .full-search-launcher__modes,
          .full-search-launcher__routes {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .full-search-launcher {
            padding: 17px;
            border-radius: 21px;
          }
        }
        @media (max-width: 430px) {
          .full-search-launcher__modes {
            grid-template-columns: 1fr;
          }
          .full-search-launcher__routes a {
            font-size: 12px;
          }
        }
      `}</style>
    </div>
  );
}
