"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AnalysisChips, ListingAnalysisPanel } from "@/components/listing-analysis-panel";
import type { AnalysisSummary } from "@/lib/analysis-api";
import {
  ApiError,
  fetchDashboard,
  fetchListing,
  fetchListings,
  fetchMatches,
  fetchSearchProfiles,
  setListingState,
  TELEGRAM_AUTHENTICATED_EVENT,
  type DashboardResponse,
  type ListingFeedItem,
  type PersonalizedMatch,
  type SearchProfileSummary
} from "@/lib/api";

type AnalyzedListing = ListingFeedItem & { analysis_summary?: AnalysisSummary };

function listingAnalysis(listing: ListingFeedItem): AnalysisSummary | undefined {
  return (listing as AnalyzedListing).analysis_summary;
}

export type WorkspaceTab = "dashboard" | "feed" | "favorites" | "comparison";

type Filters = {
  city: string;
  district: string;
  rooms: string;
  priceMin: string;
  priceMax: string;
  minScore: string;
  ordering: string;
};

const initialFilters: Filters = {
  city: "",
  district: "",
  rooms: "",
  priceMin: "",
  priceMax: "",
  minScore: "50",
  ordering: "-match_score"
};

function formatPrice(value: number): string {
  return `${new Intl.NumberFormat("uk-UA").format(value)} грн`;
}

function ListingVisual({ listing, score }: { listing: ListingFeedItem; score?: number }) {
  const image = listing.images[0];
  return (
    <div className="workspace-card__visual" style={image ? { backgroundImage: `url(${image})` } : undefined}>
      {!image && <strong>{listing.rooms}к</strong>}
      {score !== undefined && <span className="workspace-card__score">{score}%</span>}
      {listing.is_demo && <small>DEMO</small>}
    </div>
  );
}

function ActionButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button type="button" className={active ? "workspace-action is-active" : "workspace-action"} onClick={onClick}>
      {label}
    </button>
  );
}

function ListingCard({
  listing,
  match,
  onOpen,
  onState
}: {
  listing: ListingFeedItem;
  match?: PersonalizedMatch["match"];
  onOpen: () => void;
  onState: (action: "favorite" | "hide" | "compare", value: boolean) => void;
}) {
  return (
    <article className="workspace-card">
      <button type="button" className="workspace-card__open" onClick={onOpen} aria-label={`Відкрити ${listing.title}`}>
        <ListingVisual listing={listing} score={match?.score} />
        <div className="workspace-card__body">
          <small>{listing.city} · {listing.district || "район не вказано"}</small>
          <h3>{listing.title}</h3>
          <strong>{formatPrice(listing.price_uah)}</strong>
          <p>{listing.rooms} кімн. · {listing.total_area ? `${listing.total_area} м²` : "площа не вказана"}</p>
          <AnalysisChips summary={listingAnalysis(listing)} />
          {match && <p className="workspace-card__summary">{match.summary}</p>}
        </div>
      </button>
      <div className="workspace-card__actions">
        <ActionButton active={listing.user_state.is_favorite} label={listing.user_state.is_favorite ? "★ Обране" : "☆ В обране"} onClick={() => { onState("favorite", !listing.user_state.is_favorite); }} />
        <ActionButton active={listing.user_state.is_compared} label={listing.user_state.is_compared ? "✓ Порівнюється" : "⇄ Порівняти"} onClick={() => { onState("compare", !listing.user_state.is_compared); }} />
        <ActionButton active={listing.user_state.is_hidden} label="Сховати" onClick={() => { onState("hide", true); }} />
      </div>
    </article>
  );
}

function DetailPanel({
  listing,
  onClose,
  onState
}: {
  listing: ListingFeedItem;
  onClose: () => void;
  onState: (action: "favorite" | "hide" | "compare", value: boolean) => void;
}) {
  const facts = [
    ["Кімнати", String(listing.rooms)],
    ["Площа", listing.total_area ? `${listing.total_area} м²` : "Не вказано"],
    ["Поверх", listing.floor ? `${String(listing.floor)}/${listing.floors_total === null ? "?" : String(listing.floors_total)}` : "Не вказано"],
    ["Будинок", listing.building_type || "Не вказано"],
    ["Опалення", listing.heating_type || "Не вказано"],
    ["Комісія", listing.commission_percent ? `${listing.commission_percent}%` : "Не вказано"]
  ];
  return (
    <div className="detail-backdrop" role="presentation" onMouseDown={onClose}>
      <aside className="detail-panel" role="dialog" aria-modal="true" aria-label="Деталі оголошення" onMouseDown={(event) => { event.stopPropagation(); }}>
        <button type="button" className="detail-panel__close" onClick={onClose}>×</button>
        <ListingVisual listing={listing} />
        <small>{listing.source_name} · {listing.city}, {listing.district}</small>
        <h2>{listing.title}</h2>
        <strong className="detail-panel__price">{formatPrice(listing.price_uah)}</strong>
        <div className="detail-panel__facts">
          {facts.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}
        </div>
        <p>{listing.description || "Опис не додано."}</p>
        <div className="detail-panel__actions">
          <ActionButton active={listing.user_state.is_favorite} label={listing.user_state.is_favorite ? "★ В обраному" : "☆ Додати в обране"} onClick={() => { onState("favorite", !listing.user_state.is_favorite); }} />
          <ActionButton active={listing.user_state.is_compared} label={listing.user_state.is_compared ? "✓ У порівнянні" : "⇄ Додати до порівняння"} onClick={() => { onState("compare", !listing.user_state.is_compared); }} />
        </div>
        <ListingAnalysisPanel listingId={listing.id} summary={listingAnalysis(listing)} />
        <a className="detail-panel__source" href={listing.source_url} target="_blank" rel="noreferrer">Відкрити першоджерело ↗</a>
      </aside>
    </div>
  );
}

function Dashboard({ data, onNavigate }: { data: DashboardResponse; onNavigate: (tab: WorkspaceTab) => void }) {
  const stats = [
    ["Активні пошуки", data.stats.active_profiles, "feed"],
    ["Доступні квартири", data.stats.available_listings, "feed"],
    ["Обране", data.stats.favorites, "favorites"],
    ["До порівняння", data.stats.compared, "comparison"]
  ] as const;
  return (
    <div className="dashboard-view">
      <div className="dashboard-hero">
        <div><span>FLATHUNTER CONTROL CENTER</span><h2>Ваш пошук житла під контролем</h2><p>Одна панель для найкращих збігів, обраного та швидкого порівняння.</p></div>
        <button type="button" onClick={() => { onNavigate("feed"); }}>Переглянути збіги →</button>
      </div>
      <div className="dashboard-stats">
        {stats.map(([label, value, tab]) => <button type="button" key={label} onClick={() => { onNavigate(tab); }}><span>{label}</span><strong>{value}</strong></button>)}
      </div>
      <div className="dashboard-recent"><h3>Нові оголошення</h3><div>{data.recent.map((item) => <article key={item.id}><strong>{item.title}</strong><span>{formatPrice(item.price_uah)}</span></article>)}</div></div>
    </div>
  );
}

function ComparisonTable({ items, onOpen, onRemove }: { items: ListingFeedItem[]; onOpen: (id: string) => void; onRemove: (item: ListingFeedItem) => void }) {
  if (items.length < 2) return <div className="workspace-state">Додайте щонайменше дві квартири. Максимум — чотири.</div>;
  const rows: [string, (item: ListingFeedItem) => string][] = [
    ["Ціна", (item) => formatPrice(item.price_uah)],
    ["Кімнати", (item) => String(item.rooms)],
    ["Площа", (item) => item.total_area ? `${item.total_area} м²` : "—"],
    ["Поверх", (item) => item.floor ? `${String(item.floor)}/${item.floors_total === null ? "?" : String(item.floors_total)}` : "—"],
    ["Район", (item) => item.district || "—"],
    ["Тварини", (item) => item.pets_allowed === null ? "Не вказано" : item.pets_allowed ? "Так" : "Ні"]
  ];
  return (
    <div className="comparison-scroll"><table className="comparison-table"><thead><tr><th>Параметр</th>{items.map((item) => <th key={item.id}><button type="button" onClick={() => { onOpen(item.id); }}>{item.title}</button><button type="button" className="comparison-remove" onClick={() => { onRemove(item); }}>×</button></th>)}</tr></thead><tbody>{rows.map(([label, read]) => <tr key={label}><th>{label}</th>{items.map((item) => <td key={item.id}>{read(item)}</td>)}</tr>)}</tbody></table></div>
  );
}

export function ListingFeed({ initialTab = "dashboard" }: { initialTab?: WorkspaceTab }) {
  const [tab, setTab] = useState<WorkspaceTab>(initialTab);
  const [profiles, setProfiles] = useState<SearchProfileSummary[]>([]);
  const [profileId, setProfileId] = useState("");
  const [matches, setMatches] = useState<PersonalizedMatch[]>([]);
  const [listings, setListings] = useState<ListingFeedItem[]>([]);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [detail, setDetail] = useState<ListingFeedItem | null>(null);
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setTab(initialTab);
  }, [initialTab]);

  const loadProfiles = useCallback(async (signal?: AbortSignal) => {
    const result = await fetchSearchProfiles(signal);
    const active = result.filter((profile) => profile.is_active);
    setProfiles(active);
    setProfileId((current) => current || active[0]?.id || "");
  }, []);

  const loadCurrent = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setMessage("");
    try {
      if (tab === "dashboard") {
        setDashboard(await fetchDashboard(signal));
      } else if (tab === "feed") {
        if (!profileId) {
          setMatches([]);
          setMessage("Створіть активний пошуковий профіль, щоб побачити персональні збіги.");
        } else {
          const response = await fetchMatches(profileId, { minScore: Number(filters.minScore), ordering: filters.ordering }, signal);
          setMatches(response.results.filter((item) => !item.listing.user_state.is_hidden));
          setMessage(response.results.length === 0 ? "За цими критеріями збігів немає." : "");
        }
      } else {
        const response = await fetchListings({
          city: filters.city,
          district: filters.district,
          rooms: filters.rooms,
          price_min: filters.priceMin,
          price_max: filters.priceMax,
          favorites: tab === "favorites" ? true : undefined,
          compared: tab === "comparison" ? true : undefined
        }, signal);
        setListings(response.results);
        setMessage(response.results.length === 0 ? (tab === "favorites" ? "В обраному поки порожньо." : "Додайте квартири до порівняння.") : "");
      }
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        setMessage(error instanceof ApiError ? error.message : "Не вдалося завантажити дані Mini App.");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [filters, profileId, tab]);

  useEffect(() => {
    const controller = new AbortController();
    void loadProfiles(controller.signal).then(() => loadCurrent(controller.signal)).catch(() => { setMessage("Відкрий Mini App у Telegram для авторизації."); setLoading(false); });
    const reload = () => { void loadProfiles().then(() => loadCurrent()); };
    window.addEventListener(TELEGRAM_AUTHENTICATED_EVENT, reload);
    return () => { controller.abort(); window.removeEventListener(TELEGRAM_AUTHENTICATED_EVENT, reload); };
  }, [loadCurrent, loadProfiles]);

  const currentItems = useMemo(() => tab === "feed" ? matches.map((item) => item.listing) : listings, [listings, matches, tab]);

  const openDetail = useCallback(async (id: string) => {
    try { setDetail(await fetchListing(id)); } catch { setMessage("Не вдалося відкрити деталі оголошення."); }
  }, []);

  const updateState = useCallback(async (listing: ListingFeedItem, action: "favorite" | "hide" | "compare", value: boolean) => {
    try {
      const updated = await setListingState(listing.id, action, value);
      setDetail((current) => current?.id === updated.id ? updated : current);
      setListings((current) => current.map((item) => item.id === updated.id ? updated : item).filter((item) => !(tab === "favorites" && !item.user_state.is_favorite) && !(tab === "comparison" && !item.user_state.is_compared) && !item.user_state.is_hidden));
      setMatches((current) => current.map((item) => item.listing.id === updated.id ? { ...item, listing: updated } : item).filter((item) => !item.listing.user_state.is_hidden));
      setDashboard(await fetchDashboard());
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Не вдалося зберегти дію.");
    }
  }, [tab]);

  return (
    <section className="workspace">
      <nav className="workspace-tabs" aria-label="Розділи Mini App">
        {(["dashboard", "feed", "favorites", "comparison"] as const).map((value) => <button type="button" key={value} className={tab === value ? "is-active" : ""} onClick={() => { setTab(value); }}>{value === "dashboard" ? "Огляд" : value === "feed" ? "Збіги" : value === "favorites" ? "Обране" : "Порівняння"}</button>)}
      </nav>

      {tab !== "dashboard" && <header className="workspace-header"><div><span>STAGE 05</span><h2>{tab === "feed" ? "Персональна стрічка" : tab === "favorites" ? "Обрані квартири" : "Порівняння варіантів"}</h2><p>Зручний мобільний простір без десятків вкладок і повторних пошуків.</p></div><div className="workspace-filters">{tab === "feed" && <><select value={profileId} onChange={(event) => { setProfileId(event.target.value); }}>{profiles.length === 0 && <option value="">Немає профілів</option>}{profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}</select><select value={filters.minScore} onChange={(event) => { setFilters((current) => ({ ...current, minScore: event.target.value })); }}><option value="0">Усі оцінки</option><option value="50">Match 50+</option><option value="70">Match 70+</option><option value="85">Match 85+</option></select><select value={filters.ordering} onChange={(event) => { setFilters((current) => ({ ...current, ordering: event.target.value })); }}><option value="-match_score">Найкращі</option><option value="price_uah">Дешевші</option><option value="-published_at">Новіші</option></select></>}{tab === "favorites" && <><input placeholder="Місто" value={filters.city} onChange={(event) => { setFilters((current) => ({ ...current, city: event.target.value })); }} /><input placeholder="Район" value={filters.district} onChange={(event) => { setFilters((current) => ({ ...current, district: event.target.value })); }} /></>}</div></header>}

      {loading && <div className="workspace-state">Завантаження персонального простору…</div>}
      {!loading && message && <div className="workspace-state">{message}</div>}
      {!loading && tab === "dashboard" && dashboard && <Dashboard data={dashboard} onNavigate={setTab} />}
      {!loading && tab === "feed" && matches.length > 0 && <div className="workspace-grid">{matches.map((item) => <ListingCard key={item.listing.id} listing={item.listing} match={item.match} onOpen={() => { void openDetail(item.listing.id); }} onState={(action, value) => { void updateState(item.listing, action, value); }} />)}</div>}
      {!loading && tab === "favorites" && currentItems.length > 0 && <div className="workspace-grid">{currentItems.map((item) => <ListingCard key={item.id} listing={item} onOpen={() => { void openDetail(item.id); }} onState={(action, value) => { void updateState(item, action, value); }} />)}</div>}
      {!loading && tab === "comparison" && <ComparisonTable items={currentItems} onOpen={(id) => { void openDetail(id); }} onRemove={(item) => { void updateState(item, "compare", false); }} />}
      {detail && <DetailPanel listing={detail} onClose={() => { setDetail(null); }} onState={(action, value) => { void updateState(detail, action, value); }} />}

      <style jsx global>{`
        .workspace{width:min(1180px,calc(100% - 28px));margin:24px auto 130px}.workspace-tabs{position:sticky;top:12px;z-index:25;display:grid;grid-template-columns:repeat(4,1fr);gap:6px;padding:6px;border:1px solid var(--line);border-radius:18px;background:color-mix(in srgb,var(--surface-solid) 92%,transparent);backdrop-filter:blur(18px);box-shadow:var(--shadow)}.workspace-tabs button{border:0;border-radius:13px;padding:11px;background:transparent;color:var(--muted);font-weight:800}.workspace-tabs button.is-active{background:var(--accent);color:var(--accent-text)}
        .workspace-header{display:flex;justify-content:space-between;gap:18px;align-items:end;margin:22px 0 16px;padding:22px;border:1px solid var(--line);border-radius:24px;background:var(--surface-solid)}.workspace-header span,.dashboard-hero span{font-size:11px;font-weight:900;color:var(--accent);letter-spacing:.13em}.workspace-header h2,.dashboard-hero h2{margin:6px 0}.workspace-header p,.dashboard-hero p{margin:0;color:var(--muted)}.workspace-filters{display:flex;gap:8px;flex-wrap:wrap}.workspace-filters select,.workspace-filters input{min-width:130px;border:1px solid var(--line);border-radius:12px;padding:10px 12px;background:var(--bg);color:var(--text)}
        .workspace-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.workspace-card{overflow:hidden;border:1px solid var(--line);border-radius:22px;background:var(--surface-solid);box-shadow:0 10px 28px color-mix(in srgb,var(--text) 7%,transparent)}.workspace-card__open{display:grid;grid-template-columns:148px 1fr;width:100%;padding:12px;border:0;background:transparent;color:inherit;text-align:left}.workspace-card__visual{position:relative;display:grid;place-items:center;min-height:150px;border-radius:17px;background:linear-gradient(145deg,color-mix(in srgb,var(--accent) 22%,var(--bg)),var(--surface-solid));background-position:center;background-size:cover;color:var(--accent)}.workspace-card__visual>strong{font-size:34px}.workspace-card__visual>small{position:absolute;top:8px;left:8px;padding:4px 6px;border-radius:7px;background:var(--surface-solid);font-size:9px}.workspace-card__score{position:absolute;right:8px;bottom:8px;padding:6px 8px;border-radius:10px;background:var(--accent);color:var(--accent-text);font-size:12px;font-weight:900}.workspace-card__body{padding:4px 4px 4px 14px}.workspace-card__body small,.workspace-card__body p{color:var(--muted)}.workspace-card__body h3{margin:8px 0}.workspace-card__body p{margin:8px 0}.workspace-card__summary{font-size:12px}.workspace-card__actions{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;padding:0 12px 12px}.workspace-action{border:1px solid var(--line);border-radius:11px;padding:9px;background:var(--bg);color:var(--muted);font-size:11px;font-weight:800}.workspace-action.is-active{border-color:var(--accent);color:var(--accent)}.workspace-state{display:grid;place-items:center;min-height:260px;margin-top:18px;border:1px dashed var(--line);border-radius:22px;color:var(--muted)}
        .dashboard-view{display:grid;gap:16px;margin-top:22px}.dashboard-hero{display:flex;justify-content:space-between;align-items:center;gap:20px;padding:30px;border-radius:28px;background:linear-gradient(130deg,color-mix(in srgb,var(--accent) 18%,var(--surface-solid)),var(--surface-solid));border:1px solid var(--line)}.dashboard-hero button{border:0;border-radius:15px;padding:13px 17px;background:var(--accent);color:var(--accent-text);font-weight:900}.dashboard-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.dashboard-stats button{display:flex;flex-direction:column;gap:8px;border:1px solid var(--line);border-radius:19px;padding:18px;background:var(--surface-solid);color:inherit;text-align:left}.dashboard-stats span{color:var(--muted);font-size:12px}.dashboard-stats strong{font-size:28px}.dashboard-recent{padding:20px;border:1px solid var(--line);border-radius:22px;background:var(--surface-solid)}.dashboard-recent h3{margin-top:0}.dashboard-recent>div{display:grid;gap:8px}.dashboard-recent article{display:flex;justify-content:space-between;gap:12px;padding:12px;border-radius:13px;background:var(--bg)}
        .detail-backdrop{position:fixed;inset:0;z-index:80;display:flex;justify-content:flex-end;background:rgba(0,0,0,.45);backdrop-filter:blur(5px)}.detail-panel{position:relative;width:min(520px,100%);height:100%;overflow:auto;padding:20px;background:var(--surface-solid);box-shadow:-24px 0 60px rgba(0,0,0,.18)}.detail-panel>.workspace-card__visual{min-height:260px;margin-bottom:18px}.detail-panel__close{position:absolute;top:28px;right:28px;z-index:2;width:38px;height:38px;border:0;border-radius:50%;background:var(--surface-solid);font-size:25px}.detail-panel h2{margin:8px 0}.detail-panel__price{display:block;font-size:26px;margin-bottom:18px}.detail-panel__facts{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.detail-panel__facts div{display:flex;flex-direction:column;gap:5px;padding:12px;border-radius:13px;background:var(--bg)}.detail-panel__facts span{font-size:11px;color:var(--muted)}.detail-panel__actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:18px 0}.detail-panel__source{display:block;padding:13px;border-radius:13px;background:var(--accent);color:var(--accent-text);text-align:center;font-weight:900;text-decoration:none}
        .comparison-scroll{overflow:auto;margin-top:20px;border:1px solid var(--line);border-radius:20px}.comparison-table{width:100%;min-width:720px;border-collapse:collapse;background:var(--surface-solid)}.comparison-table th,.comparison-table td{padding:14px;border-bottom:1px solid var(--line);text-align:left}.comparison-table thead th{position:relative;vertical-align:top}.comparison-table thead button:first-child{max-width:180px;border:0;background:transparent;color:inherit;font-weight:900;text-align:left}.comparison-remove{position:absolute;top:8px;right:8px;border:0;background:transparent;color:var(--muted);font-size:20px}.comparison-table tbody th{color:var(--muted);font-size:12px}
        @media(max-width:760px){.workspace-grid{grid-template-columns:1fr}.workspace-header,.dashboard-hero{align-items:stretch;flex-direction:column}.dashboard-stats{grid-template-columns:repeat(2,1fr)}}@media(max-width:520px){.workspace{width:min(100% - 18px,1180px)}.workspace-tabs{top:8px}.workspace-tabs button{padding:10px 4px;font-size:11px}.workspace-header{padding:16px}.workspace-filters{display:grid;grid-template-columns:1fr;width:100%}.workspace-filters select,.workspace-filters input{width:100%}.workspace-card__open{grid-template-columns:104px 1fr}.workspace-card__visual{min-height:132px}.workspace-card__actions{grid-template-columns:1fr 1fr}.workspace-card__actions button:last-child{grid-column:1/-1}.dashboard-stats{grid-template-columns:1fr 1fr}.detail-panel{padding:14px}.detail-panel>.workspace-card__visual{min-height:220px}}
      `}</style>
    </section>
  );
}
