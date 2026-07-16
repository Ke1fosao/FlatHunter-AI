"use client";

import { useEffect, useState } from "react";

import {
  fetchMatches,
  fetchSearchProfiles,
  TELEGRAM_AUTHENTICATED_EVENT,
  type PersonalizedMatch,
  type SearchProfileSummary
} from "@/lib/api";

function MatchCard({ item }: { item: PersonalizedMatch }) {
  const { listing, match } = item;
  return (
    <article className="match-card">
      <div className="match-card__visual">
        <strong>{match.score}</strong>
        <span>Match</span>
        {listing.is_demo && <small>DEMO</small>}
      </div>
      <div className="match-card__body">
        <small>{listing.city} · {listing.district}</small>
        <h3>{listing.title}</h3>
        <strong>{new Intl.NumberFormat("uk-UA").format(listing.price_uah)} грн</strong>
        <p>{match.summary}</p>
        <div className="match-card__chips">
          {match.components.slice(0, 4).map((component) => (
            <span key={component.code} data-status={component.status} title={component.explanation}>
              {component.label}: {component.score}
            </span>
          ))}
        </div>
        {match.strengths[0] && <p className="match-card__explanation">✓ {match.strengths[0]}</p>}
        {match.compromises[0] && <p className="match-card__explanation match-card__explanation--warn">! {match.compromises[0]}</p>}
      </div>
    </article>
  );
}

export function ListingFeed() {
  const [profiles, setProfiles] = useState<SearchProfileSummary[]>([]);
  const [profileId, setProfileId] = useState("");
  const [items, setItems] = useState<PersonalizedMatch[]>([]);
  const [minScore, setMinScore] = useState("0");
  const [ordering, setOrdering] = useState("-match_score");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const loadProfiles = () => {
      setLoading(true);
      fetchSearchProfiles(controller.signal)
        .then((result) => {
          const active = result.filter((profile) => profile.is_active);
          setProfiles(active);
          setProfileId((current) => current || active[0]?.id || "");
          if (active.length === 0) {
            setItems([]);
            setMessage("Створіть активний пошуковий профіль, щоб побачити персональні збіги.");
          }
        })
        .catch(() => {
          if (!controller.signal.aborted) {
            setProfiles([]);
            setItems([]);
            setMessage("Відкрий Mini App у Telegram, щоб побачити персональну стрічку.");
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        });
    };
    loadProfiles();
    window.addEventListener(TELEGRAM_AUTHENTICATED_EVENT, loadProfiles);
    return () => {
      controller.abort();
      window.removeEventListener(TELEGRAM_AUTHENTICATED_EVENT, loadProfiles);
    };
  }, []);

  useEffect(() => {
    if (!profileId) {
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    fetchMatches(profileId, { minScore: Number(minScore), ordering }, controller.signal)
      .then((response) => {
        setItems(response.results);
        setMessage(response.results.length === 0 ? "Немає варіантів із такою мінімальною оцінкою." : "");
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setItems([]);
          setMessage("Не вдалося завантажити персональні збіги.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });
    return () => {
      controller.abort();
    };
  }, [profileId, minScore, ordering]);

  return (
    <section className="match-feed">
      <header>
        <div>
          <span>STAGE 04</span>
          <h2>Персональні збіги</h2>
          <p>Детермінований Match Score із прозорим поясненням кожної оцінки.</p>
        </div>
        <div className="match-feed__filters">
          <select
            value={profileId}
            onChange={(event) => {
              setProfileId(event.target.value);
            }}
            aria-label="Пошуковий профіль"
          >
            {profiles.length === 0 && <option value="">Немає активних профілів</option>}
            {profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}
          </select>
          <select
            value={minScore}
            onChange={(event) => {
              setMinScore(event.target.value);
            }}
            aria-label="Мінімальний Match Score"
          >
            <option value="0">Усі оцінки</option>
            <option value="50">Від 50</option>
            <option value="70">Від 70</option>
            <option value="85">Від 85</option>
          </select>
          <select
            value={ordering}
            onChange={(event) => {
              setOrdering(event.target.value);
            }}
            aria-label="Сортування"
          >
            <option value="-match_score">Найкращі збіги</option>
            <option value="price_uah">Найнижча ціна</option>
            <option value="-published_at">Найновіші</option>
          </select>
        </div>
      </header>
      {loading && <div className="match-feed__state">Розраховуємо відповідність…</div>}
      {!loading && message && <div className="match-feed__state">{message}</div>}
      {!loading && items.length > 0 && <div className="match-feed__grid">{items.map((item) => <MatchCard key={item.listing.id} item={item} />)}</div>}
      <style jsx global>{`
        .match-feed{width:min(1180px,calc(100% - 28px));margin:32px auto 130px;padding:24px;border:1px solid var(--line);border-radius:28px;background:var(--surface-solid);box-shadow:var(--shadow)}
        .match-feed>header{display:flex;justify-content:space-between;gap:18px;align-items:end;margin-bottom:20px}.match-feed h2{margin:4px 0}.match-feed header>div>span{font-size:11px;font-weight:900;color:var(--accent);letter-spacing:.12em}.match-feed header p{margin:0;color:var(--muted)}
        .match-feed__filters{display:flex;gap:8px;flex-wrap:wrap}.match-feed select{border:1px solid var(--line);border-radius:12px;padding:10px 12px;background:var(--bg);color:var(--text)}.match-feed__grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
        .match-card{display:grid;grid-template-columns:120px 1fr;gap:16px;padding:14px;border:1px solid var(--line);border-radius:20px;background:var(--bg)}.match-card__visual{display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;min-height:150px;border-radius:16px;background:linear-gradient(145deg,color-mix(in srgb,var(--accent) 22%,var(--bg)),var(--surface-solid));color:var(--accent)}.match-card__visual strong{font-size:38px}.match-card__visual span{font-size:12px;font-weight:800}.match-card__visual small{position:absolute;top:8px;left:8px;font-size:9px}.match-card h3{margin:8px 0}.match-card p,.match-card small{color:var(--muted)}
        .match-card__chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}.match-card__chips span{font-size:11px;padding:5px 8px;border-radius:999px;background:var(--surface-solid);border:1px solid var(--line)}.match-card__chips span[data-status="strong"]{color:var(--accent)}.match-card__chips span[data-status="miss"]{color:#d45353}.match-card__explanation{font-size:12px;margin:8px 0 0;color:var(--text)!important}.match-card__explanation--warn{color:#b97917!important}.match-feed__state{display:grid;place-items:center;min-height:180px;color:var(--muted)}
        @media(max-width:760px){.match-feed>header{align-items:stretch;flex-direction:column}.match-feed__grid{grid-template-columns:1fr}}@media(max-width:520px){.match-feed{padding:16px}.match-card{grid-template-columns:88px 1fr}.match-feed__filters{display:grid;grid-template-columns:1fr}.match-feed select{width:100%}}
      `}</style>
    </section>
  );
}
