"use client";

import { useEffect, useMemo, useState } from "react";

import {
  ApiError,
  compareListingsWithAI,
  fetchListings,
  fetchSearchProfiles,
  generateOwnerQuestionsWithAI,
  summarizeListingWithAI,
  type AIComparisonResponse,
  type AIMeta,
  type AIOwnerQuestionsResponse,
  type AISummaryResponse,
  type ListingFeedItem,
  type SearchProfileSummary
} from "@/lib/api";

type ListingInsight =
  | { kind: "summary"; listingId: string; payload: AISummaryResponse }
  | { kind: "questions"; listingId: string; payload: AIOwnerQuestionsResponse };

function formatPrice(value: number): string {
  return `${new Intl.NumberFormat("uk-UA").format(value)} грн`;
}

function MetaBadge({ meta }: { meta: AIMeta }) {
  return (
    <span className={`ai-meta ai-meta--${meta.status}`}>
      AI · {meta.status} · {meta.provider}
    </span>
  );
}

function ErrorMessage({ message }: { message: string }) {
  if (!message) return null;
  return <div className="ai-workspace__error" role="status">{message}</div>;
}

export function AIAssistantWorkspace() {
  const [profiles, setProfiles] = useState<SearchProfileSummary[]>([]);
  const [profileId, setProfileId] = useState("");
  const [listings, setListings] = useState<ListingFeedItem[]>([]);
  const [comparison, setComparison] = useState<AIComparisonResponse | null>(null);
  const [insight, setInsight] = useState<ListingInsight | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState("");
  const [message, setMessage] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetchSearchProfiles(controller.signal),
      fetchListings({ compared: true }, controller.signal)
    ])
      .then(([profileItems, listingResponse]) => {
        const activeProfiles = profileItems.filter((profile) => profile.is_active);
        setProfiles(activeProfiles);
        setProfileId(activeProfiles[0]?.id ?? "");
        setListings(listingResponse.results.slice(0, 5));
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setMessage(error instanceof ApiError ? error.message : "Не вдалося завантажити AI-простір.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => { controller.abort(); };
  }, []);

  const selectedProfile = useMemo(
    () => profiles.find((profile) => profile.id === profileId) ?? null,
    [profileId, profiles]
  );

  const runComparison = async () => {
    if (listings.length < 2) {
      setMessage("Додайте до порівняння щонайменше дві квартири.");
      return;
    }
    setWorking("comparison");
    setMessage("");
    setInsight(null);
    try {
      setComparison(await compareListingsWithAI(listings.map((item) => item.id), profileId || undefined));
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Не вдалося виконати AI-порівняння.");
    } finally {
      setWorking("");
    }
  };

  const runSummary = async (listingId: string) => {
    setWorking(`summary:${listingId}`);
    setMessage("");
    setComparison(null);
    try {
      const payload = await summarizeListingWithAI(listingId);
      setInsight({ kind: "summary", listingId, payload });
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Не вдалося сформувати AI-резюме.");
    } finally {
      setWorking("");
    }
  };

  const runQuestions = async (listingId: string) => {
    setWorking(`questions:${listingId}`);
    setMessage("");
    setComparison(null);
    setCopied(false);
    try {
      const payload = await generateOwnerQuestionsWithAI(listingId, profileId || undefined);
      setInsight({ kind: "questions", listingId, payload });
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Не вдалося сформувати питання власнику.");
    } finally {
      setWorking("");
    }
  };

  const copyQuestions = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setMessage("Не вдалося скопіювати текст. Виділіть його вручну.");
    }
  };

  return (
    <section className="ai-workspace" aria-label="AI-помічник FlatHunter">
      <header className="ai-workspace__hero">
        <div>
          <span>STAGE 08 · SAFE AI</span>
          <h2>AI-помічник для вибору квартири</h2>
          <p>
            Структуровані резюме, персональні питання власнику та порівняння на основі
            вашого пошукового профілю. AI не змінює факти й не пише власнику автоматично.
          </p>
        </div>
        <div className="ai-workspace__controls">
          <label>
            Пошуковий профіль
            <select value={profileId} onChange={(event) => { setProfileId(event.target.value); }}>
              {profiles.length === 0 && <option value="">Без профілю</option>}
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>{profile.name} · {profile.city}</option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => { void runComparison(); }}
            disabled={loading || working.length > 0 || listings.length < 2}
          >
            {working === "comparison" ? "Аналізую…" : "Порівняти за допомогою AI"}
          </button>
        </div>
      </header>

      <ErrorMessage message={message} />

      {loading && <div className="ai-workspace__state">Завантаження AI-простору…</div>}
      {!loading && listings.length === 0 && (
        <div className="ai-workspace__state">
          Додайте 2–5 квартир до порівняння в кабінеті — вони з’являться тут.
        </div>
      )}

      {!loading && listings.length > 0 && (
        <div className="ai-workspace__listings">
          {listings.map((listing) => (
            <article key={listing.id} className="ai-listing">
              <div>
                <small>{listing.city} · {listing.district || "район не вказано"}</small>
                <h3>{listing.title}</h3>
                <strong>{formatPrice(listing.price_uah)}</strong>
                <p>{listing.rooms} кімн. · {listing.total_area ? `${listing.total_area} м²` : "площа не вказана"}</p>
              </div>
              <div className="ai-listing__actions">
                <button
                  type="button"
                  onClick={() => { void runSummary(listing.id); }}
                  disabled={working.length > 0}
                >
                  {working === `summary:${listing.id}` ? "Готую…" : "AI-резюме"}
                </button>
                <button
                  type="button"
                  onClick={() => { void runQuestions(listing.id); }}
                  disabled={working.length > 0}
                >
                  {working === `questions:${listing.id}` ? "Готую…" : "Питання власнику"}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {comparison && (
        <article className="ai-output ai-output--comparison">
          <div className="ai-output__head">
            <div>
              <span>ПЕРСОНАЛЬНЕ ПОРІВНЯННЯ</span>
              <h3>{selectedProfile ? `За профілем «${selectedProfile.name}»` : "Без пошукового профілю"}</h3>
            </div>
            <MetaBadge meta={comparison.meta} />
          </div>
          <p className="ai-output__lead">{comparison.recommendation}</p>
          <div className="ai-comparison-grid">
            {comparison.listings.map((row) => (
              <section key={row.id} className={row.id === comparison.recommended_listing_id ? "is-recommended" : ""}>
                <h4>{row.title}</h4>
                <dl>
                  <div><dt>Ціна</dt><dd>{row.price}</dd></div>
                  <div><dt>Match Score</dt><dd>{row.match_score === null ? "—" : `${String(row.match_score)}%`}</dd></div>
                  <div><dt>Перший платіж</dt><dd>{row.known_first_payment_uah === null ? "потрібно уточнити" : formatPrice(row.known_first_payment_uah)}</dd></div>
                  <div><dt>Комісія</dt><dd>{row.commission}</dd></div>
                  <div><dt>Тварини</dt><dd>{row.pets}</dd></div>
                </dl>
                {row.advantages.length > 0 && <p className="ai-good">+ {row.advantages.join(" · ")}</p>}
                {row.disadvantages.length > 0 && <p className="ai-warning">! {row.disadvantages.join(" · ")}</p>}
                {row.unknowns.length > 0 && <small>Уточнити: {row.unknowns.join(", ")}</small>}
              </section>
            ))}
          </div>
          <ul>{comparison.tradeoffs.map((item) => <li key={item}>{item}</li>)}</ul>
        </article>
      )}

      {insight?.kind === "summary" && (
        <article className="ai-output">
          <div className="ai-output__head">
            <div><span>AI-РЕЗЮМЕ</span><h3>{listings.find((item) => item.id === insight.listingId)?.title}</h3></div>
            <MetaBadge meta={insight.payload.meta} />
          </div>
          <p className="ai-output__lead">{insight.payload.summary}</p>
          {insight.payload.advantages.length > 0 && <div className="ai-output__group"><strong>Переваги</strong><ul>{insight.payload.advantages.map((item) => <li key={item}>{item}</li>)}</ul></div>}
          {insight.payload.caveats.length > 0 && <div className="ai-output__group"><strong>Зверніть увагу</strong><ul>{insight.payload.caveats.map((item) => <li key={item}>{item}</li>)}</ul></div>}
          {insight.payload.unknowns.length > 0 && <div className="ai-output__group"><strong>Потрібно уточнити</strong><ul>{insight.payload.unknowns.map((item) => <li key={item}>{item}</li>)}</ul></div>}
        </article>
      )}

      {insight?.kind === "questions" && (
        <article className="ai-output">
          <div className="ai-output__head">
            <div><span>ПИТАННЯ ВЛАСНИКУ</span><h3>{listings.find((item) => item.id === insight.listingId)?.title}</h3></div>
            <MetaBadge meta={insight.payload.meta} />
          </div>
          <ol>{insight.payload.questions.map((item) => <li key={item}>{item}</li>)}</ol>
          <div className="ai-copy-block">
            <p>{insight.payload.message}</p>
            <button type="button" onClick={() => { void copyQuestions(insight.payload.message); }}>
              {copied ? "Скопійовано ✓" : "Скопіювати готовий текст"}
            </button>
          </div>
          <small>Повідомлення не надсилається автоматично. Ви самі вирішуєте, коли його використати.</small>
        </article>
      )}

      <style jsx global>{`
        .ai-workspace{width:min(1180px,calc(100% - 28px));margin:22px auto 150px;display:grid;gap:16px}
        .ai-workspace__hero{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;padding:28px;border:1px solid var(--border,var(--line));border-radius:28px;background:linear-gradient(135deg,color-mix(in srgb,var(--accent) 16%,var(--surface)),var(--surface));box-shadow:var(--shadow)}
        .ai-workspace__hero>div:first-child{max-width:680px}.ai-workspace__hero span,.ai-output__head span{color:var(--accent);font-size:10px;font-weight:900;letter-spacing:.15em}.ai-workspace__hero h2{margin:7px 0 8px;font-size:clamp(27px,4vw,44px);line-height:1}.ai-workspace__hero p{margin:0;color:var(--muted);line-height:1.55}
        .ai-workspace__controls{display:grid;gap:10px;min-width:280px}.ai-workspace__controls label{display:grid;gap:5px;color:var(--muted);font-size:12px;font-weight:800}.ai-workspace__controls select,.ai-workspace__controls button{min-height:44px;border-radius:13px;padding:0 13px}.ai-workspace__controls select{border:1px solid var(--border,var(--line));background:var(--surface);color:var(--text)}.ai-workspace__controls button{border:0;background:var(--accent);color:var(--accent-text);font-weight:900;cursor:pointer}.ai-workspace button:disabled{opacity:.55;cursor:not-allowed}
        .ai-workspace__state,.ai-workspace__error{padding:20px;border:1px dashed var(--border,var(--line));border-radius:20px;background:var(--surface);color:var(--muted);text-align:center}.ai-workspace__error{border-style:solid;border-color:color-mix(in srgb,#d64646 50%,var(--border,var(--line)));color:#c43b3b}
        .ai-workspace__listings{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.ai-listing{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:18px;border:1px solid var(--border,var(--line));border-radius:21px;background:var(--surface);box-shadow:0 10px 28px color-mix(in srgb,var(--text) 6%,transparent)}.ai-listing small,.ai-listing p{color:var(--muted)}.ai-listing h3{margin:5px 0}.ai-listing p{margin:6px 0 0;font-size:12px}.ai-listing__actions{display:grid;gap:7px;min-width:145px}.ai-listing__actions button{min-height:38px;border:1px solid var(--border,var(--line));border-radius:11px;background:var(--bg);color:var(--text);font-size:11px;font-weight:850;cursor:pointer}.ai-listing__actions button:first-child{border-color:color-mix(in srgb,var(--accent) 40%,var(--border,var(--line)));color:var(--accent)}
        .ai-output{padding:24px;border:1px solid color-mix(in srgb,var(--accent) 25%,var(--border,var(--line)));border-radius:25px;background:var(--surface);box-shadow:var(--shadow)}.ai-output__head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}.ai-output__head h3{margin:5px 0 0}.ai-output__lead{font-size:17px;line-height:1.55}.ai-meta{flex:0 0 auto;padding:7px 9px;border-radius:999px;background:color-mix(in srgb,var(--accent) 11%,var(--surface));color:var(--accent);font-size:9px;font-weight:900}.ai-meta--fallback{background:color-mix(in srgb,#e59b3a 14%,var(--surface));color:#b16e17}.ai-output__group{margin-top:15px}.ai-output ul,.ai-output ol{padding-left:21px;color:var(--muted);line-height:1.6}
        .ai-comparison-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}.ai-comparison-grid>section{padding:16px;border:1px solid var(--border,var(--line));border-radius:17px;background:var(--bg)}.ai-comparison-grid>section.is-recommended{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}.ai-comparison-grid h4{margin:0 0 12px}.ai-comparison-grid dl{display:grid;gap:7px;margin:0}.ai-comparison-grid dl div{display:flex;justify-content:space-between;gap:8px}.ai-comparison-grid dt{color:var(--muted);font-size:11px}.ai-comparison-grid dd{margin:0;font-size:12px;font-weight:800;text-align:right}.ai-good{color:var(--accent);font-size:11px}.ai-warning{color:#b16e17;font-size:11px}.ai-comparison-grid small{color:var(--muted)}
        .ai-copy-block{display:grid;gap:10px;margin:16px 0;padding:16px;border-radius:16px;background:var(--bg)}.ai-copy-block p{margin:0;line-height:1.55}.ai-copy-block button{justify-self:start;min-height:40px;border:0;border-radius:11px;padding:0 14px;background:var(--accent);color:var(--accent-text);font-weight:850;cursor:pointer}
        @media(max-width:760px){.ai-workspace__hero{align-items:stretch;flex-direction:column;padding:21px}.ai-workspace__controls{min-width:0}.ai-workspace__listings{grid-template-columns:1fr}.ai-output__head{flex-direction:column}.ai-listing{align-items:stretch;flex-direction:column}.ai-listing__actions{grid-template-columns:1fr 1fr;width:100%}}
        @media(max-width:430px){.ai-workspace{width:calc(100% - 18px)}.ai-listing__actions{grid-template-columns:1fr}.ai-output{padding:18px}}
      `}</style>
    </section>
  );
}
