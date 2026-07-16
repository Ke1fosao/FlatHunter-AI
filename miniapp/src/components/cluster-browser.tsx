"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ClusterSources } from "@/components/cluster-sources";
import {
  ApiError,
  fetchSearchProfiles,
  setListingState,
  TELEGRAM_AUTHENTICATED_EVENT,
  type ListingUserState,
  type SearchProfileSummary
} from "@/lib/api";
import {
  fetchClusterFeed,
  fetchListingCluster,
  formatClusterPriceRange,
  setClusterState,
  sourceLabel,
  type ClusterFeedItem,
  type ClusterListing,
  type ListingClusterDetail
} from "@/lib/cluster-api";

type BooleanClusterField = "is_favorite" | "is_hidden" | "is_compared";
type ClusterPatch = Partial<Pick<ListingUserState, BooleanClusterField | "note">>;

function standaloneDetail(item: ClusterFeedItem): ListingClusterDetail {
  const { listing, match } = item;
  return {
    id: listing.id,
    status: "active",
    primary: listing,
    member_count: 1,
    source_count: 1,
    confidence_min: "100.00",
    confidence_max: "100.00",
    price_min_uah: listing.price_uah,
    price_max_uah: listing.price_uah,
    members: [
      {
        role: "primary",
        confidence: "100.00",
        joined_by: "exact",
        reasons: [],
        listing
      }
    ],
    user_state: listing.user_state,
    match,
    algorithm_version: 1,
    created_at: listing.published_at,
    updated_at: listing.published_at
  };
}

function Card({ item, onOpen, onState }: { item: ClusterFeedItem; onOpen: () => void; onState: (field: BooleanClusterField, value: boolean) => void }) {
  const { listing, match } = item;
  return (
    <article className="cluster-card">
      <button type="button" className="cluster-card__open" onClick={onOpen} aria-label={`Відкрити ${listing.title}`}>
        <div className="cluster-card__visual">
          <strong>{listing.rooms}к</strong>
          {match && <span>{match.score}% Match</span>}
        </div>
        <div className="cluster-card__body">
          <div className="cluster-card__eyebrow">
            <small>{listing.city} · {listing.district || "район не вказано"}</small>
            {listing.member_count > 1 && <b>{sourceLabel(listing.member_count)}</b>}
          </div>
          <h3>{listing.title}</h3>
          <strong>{formatClusterPriceRange(listing.price_min_uah, listing.price_max_uah)}</strong>
          <p>{listing.rooms} кімн. · {listing.total_area ? `${listing.total_area} м²` : "площа не вказана"}</p>
          {match && <p className="cluster-card__summary">{match.summary}</p>}
        </div>
      </button>
      <div className="cluster-card__actions">
        <button type="button" className={listing.user_state.is_favorite ? "is-active" : ""} onClick={() => { onState("is_favorite", !listing.user_state.is_favorite); }}>
          {listing.user_state.is_favorite ? "★ В обраному" : "☆ В обране"}
        </button>
        <button type="button" className={listing.user_state.is_compared ? "is-active" : ""} onClick={() => { onState("is_compared", !listing.user_state.is_compared); }}>
          {listing.user_state.is_compared ? "✓ Порівнюється" : "⇄ Порівняти"}
        </button>
        <button type="button" onClick={() => { onState("is_hidden", true); }}>Сховати</button>
      </div>
    </article>
  );
}

function Detail({ cluster, onClose, onPatch }: { cluster: ListingClusterDetail; onClose: () => void; onPatch: (values: ClusterPatch) => void }) {
  const listing = cluster.primary;
  const [note, setNote] = useState(cluster.user_state.note);

  useEffect(() => {
    setNote(cluster.user_state.note);
  }, [cluster.id, cluster.user_state.note]);

  return (
    <div className="cluster-detail-backdrop" role="presentation" onMouseDown={onClose}>
      <aside className="cluster-detail" role="dialog" aria-modal="true" aria-label="Деталі квартири та джерел" onMouseDown={(event) => { event.stopPropagation(); }}>
        <button type="button" className="cluster-detail__close" onClick={onClose} aria-label="Закрити">×</button>
        {cluster.member_count > 1 && <span className="cluster-detail__badge">{sourceLabel(cluster.member_count)}</span>}
        <small>{listing.city} · {listing.district || "район не вказано"}</small>
        <h2>{listing.title}</h2>
        <strong className="cluster-detail__price">{formatClusterPriceRange(cluster.price_min_uah ?? listing.price_uah, cluster.price_max_uah ?? listing.price_uah)}</strong>
        <p>{listing.description || "Опис не додано."}</p>
        <div className="cluster-detail__facts">
          <div><span>Кімнати</span><strong>{listing.rooms}</strong></div>
          <div><span>Площа</span><strong>{listing.total_area ? `${listing.total_area} м²` : "—"}</strong></div>
          <div><span>Поверх</span><strong>{listing.floor ? `${String(listing.floor)}/${listing.floors_total ?? "?"}` : "—"}</strong></div>
          <div><span>Match</span><strong>{cluster.match ? `${String(cluster.match.score)}%` : "—"}</strong></div>
        </div>
        <div className="cluster-detail__actions">
          <button type="button" className={cluster.user_state.is_favorite ? "is-active" : ""} onClick={() => { onPatch({ is_favorite: !cluster.user_state.is_favorite }); }}>
            {cluster.user_state.is_favorite ? "★ В обраному" : "☆ Додати в обране"}
          </button>
          <button type="button" className={cluster.user_state.is_compared ? "is-active" : ""} onClick={() => { onPatch({ is_compared: !cluster.user_state.is_compared }); }}>
            {cluster.user_state.is_compared ? "✓ У порівнянні" : "⇄ Порівняти"}
          </button>
          <button type="button" onClick={() => { onPatch({ is_hidden: true }); }}>Сховати квартиру</button>
        </div>
        {listing.cluster_id && (
          <label className="cluster-detail__note">
            Ваша нотатка
            <textarea value={note} maxLength={500} onChange={(event) => { setNote(event.target.value); }} placeholder="Що потрібно уточнити у власника?" />
            <button type="button" onClick={() => { onPatch({ note }); }}>Зберегти нотатку</button>
          </label>
        )}
        <ClusterSources cluster={cluster} />
      </aside>
    </div>
  );
}

export function ClusterBrowser() {
  const [profiles, setProfiles] = useState<SearchProfileSummary[]>([]);
  const [profileId, setProfileId] = useState("");
  const [minScore, setMinScore] = useState("50");
  const [items, setItems] = useState<ClusterFeedItem[]>([]);
  const [detail, setDetail] = useState<ListingClusterDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const activeProfile = useMemo(() => profiles.find((profile) => profile.id === profileId) ?? null, [profileId, profiles]);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setMessage("");
    try {
      const available = (await fetchSearchProfiles(signal)).filter((profile) => profile.is_active);
      setProfiles(available);
      const selectedId = profileId || available[0]?.id || "";
      if (!profileId && selectedId) setProfileId(selectedId);
      const selected = available.find((profile) => profile.id === selectedId) ?? null;
      const result = await fetchClusterFeed(selected, Number(minScore), signal);
      setItems(result.filter((item) => !item.listing.user_state.is_hidden));
      if (result.length === 0) setMessage("За обраними умовами квартир поки немає.");
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        setMessage(error instanceof ApiError ? error.message : "Не вдалося завантажити згруповані оголошення.");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [minScore, profileId]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    const reload = () => { void load(); };
    window.addEventListener(TELEGRAM_AUTHENTICATED_EVENT, reload);
    return () => {
      controller.abort();
      window.removeEventListener(TELEGRAM_AUTHENTICATED_EVENT, reload);
    };
  }, [load]);

  const open = useCallback(async (item: ClusterFeedItem) => {
    if (!item.listing.cluster_id) {
      setDetail(standaloneDetail(item));
      return;
    }
    try {
      setDetail(await fetchListingCluster(item.listing.cluster_id, activeProfile?.id));
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Не вдалося відкрити джерела квартири.");
    }
  }, [activeProfile?.id]);

  const update = useCallback(async (listing: ClusterListing, values: ClusterPatch) => {
    try {
      if (listing.cluster_id) {
        const updated = await setClusterState(listing.cluster_id, values);
        const hidden = updated.user_state.is_hidden;
        setDetail(hidden ? null : updated);
        setItems((current) => current
          .map((item) => item.listing.cluster_id === updated.id ? { ...item, listing: updated.primary } : item)
          .filter((item) => !item.listing.user_state.is_hidden));
      } else {
        const entries = Object.entries(values) as [keyof ClusterPatch, ClusterPatch[keyof ClusterPatch]][];
        const booleanEntry = entries.find(([field, value]) => field !== "note" && typeof value === "boolean");
        if (!booleanEntry) return;
        const [field, value] = booleanEntry as [BooleanClusterField, boolean];
        const action = field === "is_favorite" ? "favorite" : field === "is_compared" ? "compare" : "hide";
        const updated = await setListingState(listing.id, action, value) as ClusterListing;
        setItems((current) => current
          .map((item) => item.listing.id === updated.id ? { ...item, listing: updated } : item)
          .filter((item) => !item.listing.user_state.is_hidden));
        setDetail(updated.user_state.is_hidden ? null : standaloneDetail({ listing: updated, match: detail?.match ?? null }));
      }
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Не вдалося зберегти дію.");
    }
  }, [detail?.match]);

  return (
    <section className="cluster-browser">
      <header className="cluster-browser__hero">
        <div><span>STAGE 07 · DUPLICATE CLUSTERS</span><h2>Одна квартира — одна картка</h2><p>Повторні публікації об’єднані, але кожне джерело, ціна й пряме посилання залишаються доступними.</p></div>
        <div className="cluster-browser__filters">
          <label>Пошук<select value={profileId} onChange={(event) => { setProfileId(event.target.value); }}>{profiles.length === 0 && <option value="">Без активного профілю</option>}{profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name} · {profile.city}</option>)}</select></label>
          <label>Match від<select value={minScore} onChange={(event) => { setMinScore(event.target.value); }}><option value="0">0%</option><option value="50">50%</option><option value="70">70%</option><option value="85">85%</option></select></label>
          <button type="button" onClick={() => { void load(); }}>Оновити</button>
        </div>
      </header>
      {loading && <div className="cluster-browser__state">Аналізую згруповані оголошення…</div>}
      {!loading && message && <div className="cluster-browser__state" role="status">{message}</div>}
      {!loading && items.length > 0 && <div className="cluster-browser__grid">{items.map((item) => <Card key={item.listing.cluster_id ?? item.listing.id} item={item} onOpen={() => { void open(item); }} onState={(field, value) => { void update(item.listing, { [field]: value }); }} />)}</div>}
      {detail && <Detail cluster={detail} onClose={() => { setDetail(null); }} onPatch={(values) => { void update(detail.primary, values); }} />}
      <style jsx global>{`
        .cluster-browser{width:min(1180px,calc(100% - 28px));margin:24px auto 130px}.cluster-browser__hero{display:flex;justify-content:space-between;align-items:end;gap:24px;padding:24px;border:1px solid var(--line);border-radius:26px;background:linear-gradient(130deg,color-mix(in srgb,var(--accent) 12%,var(--surface-solid)),var(--surface-solid));box-shadow:var(--shadow)}.cluster-browser__hero span{font-size:10px;font-weight:900;letter-spacing:.13em;color:var(--accent)}.cluster-browser__hero h2{margin:7px 0}.cluster-browser__hero p{max-width:660px;margin:0;color:var(--muted);line-height:1.55}.cluster-browser__filters{display:flex;align-items:end;gap:8px}.cluster-browser__filters label{display:grid;gap:5px;color:var(--muted);font-size:10px;font-weight:900;text-transform:uppercase}.cluster-browser__filters select,.cluster-browser__filters button{min-width:132px;border:1px solid var(--line);border-radius:12px;padding:10px;background:var(--bg);color:var(--text)}.cluster-browser__filters button{min-width:auto;background:var(--accent);color:var(--accent-text);font-weight:900}
        .cluster-browser__grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:16px}.cluster-card{overflow:hidden;border:1px solid var(--line);border-radius:22px;background:var(--surface-solid);box-shadow:0 12px 30px color-mix(in srgb,var(--text) 7%,transparent)}.cluster-card__open{display:grid;grid-template-columns:142px 1fr;width:100%;padding:12px;border:0;background:transparent;color:inherit;text-align:left}.cluster-card__visual{position:relative;display:grid;place-items:center;min-height:154px;border-radius:17px;background:linear-gradient(145deg,color-mix(in srgb,var(--accent) 24%,var(--bg)),var(--surface-solid));color:var(--accent)}.cluster-card__visual>strong{font-size:35px}.cluster-card__visual>span{position:absolute;right:8px;bottom:8px;padding:6px 8px;border-radius:9px;background:var(--accent);color:var(--accent-text);font-size:11px;font-weight:900}.cluster-card__body{padding:3px 4px 3px 14px}.cluster-card__eyebrow{display:flex;justify-content:space-between;align-items:center;gap:8px}.cluster-card__eyebrow small,.cluster-card__body p{color:var(--muted)}.cluster-card__eyebrow b{white-space:nowrap;padding:5px 7px;border-radius:9px;background:color-mix(in srgb,var(--accent) 14%,var(--bg));color:var(--accent);font-size:10px}.cluster-card h3{margin:9px 0}.cluster-card__body>strong{font-size:19px}.cluster-card__body p{margin:8px 0}.cluster-card__summary{font-size:12px}.cluster-card__actions{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;padding:0 12px 12px}.cluster-card__actions button,.cluster-detail__actions button,.cluster-detail__note button{border:1px solid var(--line);border-radius:11px;padding:10px;background:var(--bg);color:var(--muted);font-weight:900}.cluster-card__actions button.is-active,.cluster-detail__actions button.is-active{border-color:var(--accent);color:var(--accent)}.cluster-browser__state{display:grid;place-items:center;min-height:260px;margin-top:16px;border:1px dashed var(--line);border-radius:22px;color:var(--muted)}
        .cluster-detail-backdrop{position:fixed;inset:0;z-index:90;display:flex;justify-content:flex-end;background:rgba(0,0,0,.48);backdrop-filter:blur(5px)}.cluster-detail{position:relative;width:min(600px,100%);height:100%;overflow:auto;padding:24px;background:var(--surface-solid);box-shadow:-24px 0 60px rgba(0,0,0,.2)}.cluster-detail__close{position:absolute;top:18px;right:18px;width:38px;height:38px;border:0;border-radius:50%;background:var(--bg);color:var(--text);font-size:25px}.cluster-detail__badge{display:inline-flex;margin-bottom:14px;padding:6px 9px;border-radius:10px;background:var(--accent);color:var(--accent-text);font-size:11px;font-weight:900}.cluster-detail h2{margin:8px 45px 8px 0}.cluster-detail>p{color:var(--muted);line-height:1.6}.cluster-detail__price{display:block;margin:12px 0;font-size:27px}.cluster-detail__facts{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.cluster-detail__facts div{display:grid;gap:5px;padding:12px;border-radius:13px;background:var(--bg)}.cluster-detail__facts span{font-size:10px;color:var(--muted)}.cluster-detail__actions{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:16px}.cluster-detail__note{display:grid;gap:8px;margin-top:16px;color:var(--muted);font-size:12px;font-weight:900}.cluster-detail__note textarea{min-height:88px;resize:vertical;border:1px solid var(--line);border-radius:13px;padding:12px;background:var(--bg);color:var(--text);font:inherit;font-weight:400}.cluster-detail__note button{justify-self:start;color:var(--accent)}
        @media(max-width:820px){.cluster-browser__hero{align-items:stretch;flex-direction:column}.cluster-browser__filters{flex-wrap:wrap}.cluster-browser__grid{grid-template-columns:1fr}}@media(max-width:520px){.cluster-browser{width:calc(100% - 18px)}.cluster-browser__hero{padding:17px}.cluster-browser__filters{display:grid;grid-template-columns:1fr 1fr;width:100%}.cluster-browser__filters label:first-child{grid-column:1/-1}.cluster-browser__filters select,.cluster-browser__filters button{width:100%;min-width:0}.cluster-card__open{grid-template-columns:102px 1fr}.cluster-card__visual{min-height:138px}.cluster-card__actions{grid-template-columns:1fr 1fr}.cluster-card__actions button:last-child{grid-column:1/-1}.cluster-detail{padding:17px}.cluster-detail__facts{grid-template-columns:1fr 1fr}.cluster-detail__actions{grid-template-columns:1fr}.cluster-detail__actions button:last-child{grid-column:auto}}
      `}</style>
    </section>
  );
}
