"use client";

import { FormEvent, useState } from "react";

import {
  createSearchProfile,
  parseNaturalLanguageSearch,
  type SearchProfileInput
} from "@/lib/api";

const defaultNotification: SearchProfileInput["notification_preference"] = {
  frequency: "instant",
  min_match_score: 75,
  max_risk_score: 70,
  daily_limit: 20,
  quiet_hours_enabled: true,
  quiet_hours_start: "23:00",
  quiet_hours_end: "08:00",
  notify_price_changes: true,
  notify_reactivated: false
};

type Props = {
  onClose: () => void;
  onCreated: () => void;
};

export function SearchWizard({ onClose, onCreated }: Props) {
  const [mode, setMode] = useState<"form" | "natural">("form");
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [naturalText, setNaturalText] = useState("");
  const [confidence, setConfidence] = useState<Record<string, number>>({});
  const [form, setForm] = useState<SearchProfileInput>({
    name: "Мій пошук",
    city: "Львів",
    deal_type: "rent",
    price_min: null,
    price_max: 18000,
    currency: "UAH",
    rooms: [1],
    desired_districts: [],
    excluded_districts: [],
    occupants: 1,
    children: false,
    pets: {},
    property_types: ["apartment"],
    filters: {},
    notification_preference: defaultNotification
  });

  const patch = <K extends keyof SearchProfileInput>(key: K, value: SearchProfileInput[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const parseText = async () => {
    setBusy(true);
    setError("");
    try {
      const parsed = await parseNaturalLanguageSearch(naturalText);
      setForm((current) => ({
        ...current,
        ...parsed.data,
        name: parsed.data.city ? `Оренда · ${parsed.data.city}` : current.name,
        notification_preference: current.notification_preference
      }));
      setConfidence(parsed.confidence);
      setStep(3);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося розібрати запит");
    } finally {
      setBusy(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await createSearchProfile({ ...form, source_text: naturalText });
      onCreated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося створити пошук");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="wizard-backdrop" role="presentation">
      <section className="wizard-sheet" role="dialog" aria-modal="true" aria-labelledby="wizard-title">
        <header className="wizard-header">
          <div>
            <span className="section-kicker">SEARCH SETUP</span>
            <h2 id="wizard-title">Створити пошук</h2>
          </div>
          <button type="button" className="wizard-close" onClick={onClose} aria-label="Закрити">×</button>
        </header>

        <div className="wizard-mode-switch">
          <button type="button" className={mode === "form" ? "is-active" : ""} onClick={() => setMode("form")}>Покроково</button>
          <button type="button" className={mode === "natural" ? "is-active" : ""} onClick={() => setMode("natural")}>Описати словами</button>
        </div>

        {mode === "natural" && step < 3 ? (
          <div className="wizard-natural">
            <label htmlFor="natural-search">Опишіть квартиру своїми словами</label>
            <textarea
              id="natural-search"
              value={naturalText}
              onChange={(event) => setNaturalText(event.target.value)}
              placeholder="Шукаю однокімнатну квартиру у Львові до 18 тисяч, новобудова, не перший поверх, можна з котом, без комісії…"
            />
            <button type="button" className="button button--primary" disabled={busy || naturalText.trim().length < 10} onClick={() => void parseText()}>
              {busy ? "Аналізую…" : "Розібрати запит"}
            </button>
          </div>
        ) : (
          <form onSubmit={(event) => void submit(event)}>
            <div className="wizard-progress"><span style={{ width: `${(step / 3) * 100}%` }} /></div>

            {step === 1 && (
              <div className="wizard-grid">
                <label>Назва пошуку<input value={form.name} onChange={(event) => patch("name", event.target.value)} required /></label>
                <label>Місто<input value={form.city} onChange={(event) => patch("city", event.target.value)} required /></label>
                <label>Тип угоди<select value={form.deal_type} onChange={(event) => patch("deal_type", event.target.value as "rent" | "buy")}><option value="rent">Оренда</option><option value="buy">Купівля</option></select></label>
                <label>Максимальна ціна<input type="number" min="1000" value={form.price_max ?? ""} onChange={(event) => patch("price_max", event.target.value ? Number(event.target.value) : null)} required /></label>
                <label>Кімнати<input value={form.rooms.join(",")} onChange={(event) => patch("rooms", event.target.value.split(",").map(Number).filter(Boolean))} required /></label>
                <label>Хто житиме<input type="number" min="1" max="20" value={form.occupants} onChange={(event) => patch("occupants", Number(event.target.value))} /></label>
              </div>
            )}

            {step === 2 && (
              <div className="wizard-options">
                <button type="button" className={form.pets.cat ? "option-chip is-active" : "option-chip"} onClick={() => patch("pets", { ...form.pets, cat: !form.pets.cat })}>🐈 Можна з котом</button>
                <button type="button" className={form.pets.dog ? "option-chip is-active" : "option-chip"} onClick={() => patch("pets", { ...form.pets, dog: !form.pets.dog })}>🐕 Можна із собакою</button>
                <button type="button" className={form.filters.exclude_first_floor ? "option-chip is-active" : "option-chip"} onClick={() => patch("filters", { ...form.filters, exclude_first_floor: !form.filters.exclude_first_floor })}>Не перший поверх</button>
                <button type="button" className={form.filters.exclude_last_floor ? "option-chip is-active" : "option-chip"} onClick={() => patch("filters", { ...form.filters, exclude_last_floor: !form.filters.exclude_last_floor })}>Не останній поверх</button>
                <button type="button" className={form.filters.commission_allowed === false ? "option-chip is-active" : "option-chip"} onClick={() => patch("filters", { ...form.filters, commission_allowed: form.filters.commission_allowed !== false ? false : true })}>Без комісії</button>
                <button type="button" className={form.children ? "option-chip is-active" : "option-chip"} onClick={() => patch("children", !form.children)}>Можна з дітьми</button>
              </div>
            )}

            {step === 3 && (
              <div className="wizard-review">
                <h3>Перевірте пошук</h3>
                <dl>
                  <div><dt>Місто</dt><dd>{form.city || "Не вказано"}</dd></div>
                  <div><dt>Бюджет</dt><dd>до {form.price_max?.toLocaleString("uk-UA") ?? "—"} грн</dd></div>
                  <div><dt>Кімнати</dt><dd>{form.rooms.join(", ") || "—"}</dd></div>
                  <div><dt>Сповіщення</dt><dd>миттєво, Match від {form.notification_preference.min_match_score}%</dd></div>
                </dl>
                {Object.keys(confidence).length > 0 && <p className="confidence-note">AI-поля підтверджені з рівнем упевненості. Відсутні умови не були вигадані.</p>}
              </div>
            )}

            {error && <p className="wizard-error">{error}</p>}
            <footer className="wizard-footer">
              <button type="button" className="button button--secondary" onClick={() => step === 1 ? onClose() : setStep((value) => value - 1)}>Назад</button>
              {step < 3 ? (
                <button type="button" className="button button--primary" onClick={() => setStep((value) => value + 1)}>Продовжити</button>
              ) : (
                <button type="submit" className="button button--primary" disabled={busy}>{busy ? "Зберігаю…" : "Створити пошук"}</button>
              )}
            </footer>
          </form>
        )}
      </section>
    </div>
  );
}
