"use client";

import { useEffect, useState } from "react";

import {
  fetchListings,
  TELEGRAM_AUTHENTICATED_EVENT,
  type ListingFeedItem
} from "@/lib/api";

function ListingCard({ item }: { item: ListingFeedItem }) {
  return (
    <article className="demo-listing-card">
      <div className="demo-listing-card__visual">
        <strong>{item.rooms}к</strong>
        {item.is_demo && <span>DEMO</span>}
      </div>
      <div>
        <small>{item.city} · {item.district}</small>
        <h3>{item.title}</h3>
        <strong>{new Intl.NumberFormat("uk-UA").format(item.price_uah)} грн</strong>
        <p>{item.total_area ? `${item.total_area} м²` : "Площа не вказана"}</p>
      </div>
    </article>
  );
}

export function ListingFeed() {
  const [items, setItems] = useState<ListingFeedItem[]>([]);
  const [city, setCity] = useState("");
  const [rooms, setRooms] = useState("");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let controller = new AbortController();

    const load = () => {
      controller.abort();
      controller = new AbortController();
      setLoading(true);
      fetchListings({ city, rooms }, controller.signal)
        .then((response) => {
          setItems(response.results);
          setMessage(
            response.results.length === 0 ? "За цими фільтрами нічого не знайдено." : ""
          );
        })
        .catch(() => {
          if (!controller.signal.aborted) {
            setItems([]);
            setMessage("Відкрий Mini App у Telegram, щоб побачити персональну стрічку.");
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    };

    load();
    window.addEventListener(TELEGRAM_AUTHENTICATED_EVENT, load);
    return () => {
      controller.abort();
      window.removeEventListener(TELEGRAM_AUTHENTICATED_EVENT, load);
    };
  }, [city, rooms]);

  return (
    <section className="demo-feed">
      <header>
        <div><span>STAGE 03</span><h2>Стрічка квартир</h2><p>Нормалізовані synthetic demo-дані з backend API.</p></div>
        <div className="demo-feed__filters">
          <select value={city} onChange={(event) => { setCity(event.target.value); }} aria-label="Місто">
            <option value="">Усі міста</option><option>Львів</option><option>Рівне</option><option>Київ</option>
          </select>
          <select value={rooms} onChange={(event) => { setRooms(event.target.value); }} aria-label="Кімнати">
            <option value="">Усі кімнати</option>{[1, 2, 3, 4].map((value) => <option key={value}>{value}</option>)}
          </select>
        </div>
      </header>
      {loading && <div className="demo-feed__state">Завантаження оголошень…</div>}
      {!loading && message && <div className="demo-feed__state">{message}</div>}
      {!loading && items.length > 0 && <div className="demo-feed__grid">{items.map((item) => <ListingCard key={item.id} item={item} />)}</div>}
      <style jsx global>{`
        .demo-feed{width:min(1180px,calc(100% - 28px));margin:32px auto 130px;padding:24px;border:1px solid var(--line);border-radius:28px;background:var(--surface-solid);box-shadow:var(--shadow)}
        .demo-feed>header{display:flex;justify-content:space-between;gap:18px;align-items:end;margin-bottom:20px}.demo-feed h2{margin:4px 0}.demo-feed header span{font-size:11px;font-weight:900;color:var(--accent);letter-spacing:.12em}.demo-feed header p{margin:0;color:var(--muted)}
        .demo-feed__filters{display:flex;gap:8px}.demo-feed select{border:1px solid var(--line);border-radius:12px;padding:10px 12px;background:var(--bg);color:var(--text)}.demo-feed__grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.demo-listing-card{display:grid;grid-template-columns:120px 1fr;gap:16px;padding:14px;border:1px solid var(--line);border-radius:20px;background:var(--bg)}.demo-listing-card__visual{display:grid;place-items:center;position:relative;min-height:130px;border-radius:16px;background:linear-gradient(145deg,color-mix(in srgb,var(--accent) 20%,var(--bg)),var(--surface-solid));font-size:30px;color:var(--accent)}.demo-listing-card__visual span{position:absolute;top:8px;left:8px;font-size:9px}.demo-listing-card h3{margin:8px 0}.demo-listing-card p,.demo-listing-card small{color:var(--muted)}.demo-feed__state{display:grid;place-items:center;min-height:180px;color:var(--muted)}@media(max-width:760px){.demo-feed>header{align-items:stretch;flex-direction:column}.demo-feed__grid{grid-template-columns:1fr}}@media(max-width:520px){.demo-feed{padding:16px}.demo-listing-card{grid-template-columns:90px 1fr}.demo-feed__filters{display:grid;grid-template-columns:1fr 1fr}}
      `}</style>
    </section>
  );
}
