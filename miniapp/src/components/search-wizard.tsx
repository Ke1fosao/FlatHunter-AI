"use client";

import { useEffect, useState } from "react";
import type { SyntheticEvent } from "react";

import {
  createSearchProfile,
  parseNaturalLanguageSearch,
  updateSearchProfile,
  type NotificationPreferenceInput,
  type SearchProfile,
  type SearchProfileInput,
} from "@/lib/api";

const defaultNotification: NotificationPreferenceInput = {
  frequency: "instant",
  min_match_score: 75,
  max_risk_score: 70,
  daily_limit: 20,
  quiet_hours_enabled: true,
  quiet_hours_start: "23:00",
  quiet_hours_end: "08:00",
  notify_price_changes: true,
  notify_reactivated: false,
};

function defaultForm(): SearchProfileInput {
  return {
    name: "Мій пошук",
    city: "Львів",
    deal_type: "rent",
    price_min: null,
    price_max: 18000,
    currency: "UAH",
    rooms: [1],
    desired_districts: [],
    excluded_districts: [],
    move_in_date: null,
    occupants: 1,
    children: false,
    pets: {},
    property_types: ["apartment"],
    filters: {},
    source_text: "",
    notification_preference: defaultNotification,
  };
}

function timeValue(value: string): string {
  return value.slice(0, 5);
}

function inputFromProfile(profile: SearchProfile): SearchProfileInput {
  return {
    name: profile.name,
    city: profile.city,
    deal_type: profile.deal_type,
    price_min: profile.price_min,
    price_max: profile.price_max,
    currency: profile.currency,
    rooms: profile.rooms,
    desired_districts: profile.desired_districts,
    excluded_districts: profile.excluded_districts,
    move_in_date: profile.move_in_date,
    occupants: profile.occupants,
    children: profile.children,
    pets: profile.pets,
    property_types: profile.property_types,
    filters: profile.filters,
    source_text: profile.source_text,
    notification_preference: {
      frequency: profile.notification_preference.frequency,
      min_match_score: profile.notification_preference.min_match_score,
      max_risk_score: profile.notification_preference.max_risk_score,
      daily_limit: profile.notification_preference.daily_limit,
      quiet_hours_enabled:
        profile.notification_preference.quiet_hours_enabled,
      quiet_hours_start: timeValue(
        profile.notification_preference.quiet_hours_start,
      ),
      quiet_hours_end: timeValue(profile.notification_preference.quiet_hours_end),
      notify_price_changes:
        profile.notification_preference.notify_price_changes,
      notify_reactivated: profile.notification_preference.notify_reactivated,
    },
  };
}

function csvStrings(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function csvNumbers(value: string): number[] {
  return [...new Set(
    value
      .split(",")
      .map((item) => Number.parseInt(item.trim(), 10))
      .filter((item) => Number.isInteger(item) && item > 0),
  )];
}

type Props = {
  onClose: () => void;
  onCreated?: () => void;
  onSaved?: () => void;
  profile?: SearchProfile;
};

export function SearchWizard({
  onClose,
  onCreated,
  onSaved,
  profile,
}: Props) {
  const editing = profile !== undefined;
  const [mode, setMode] = useState<"form" | "natural">("form");
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [naturalText, setNaturalText] = useState(profile?.source_text ?? "");
  const [confidence, setConfidence] = useState<Record<string, number>>({});
  const [form, setForm] = useState<SearchProfileInput>(() =>
    profile ? inputFromProfile(profile) : defaultForm(),
  );

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [onClose]);

  const patch = <K extends keyof SearchProfileInput>(
    key: K,
    value: SearchProfileInput[K],
  ) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const patchNotification = <K extends keyof NotificationPreferenceInput>(
    key: K,
    value: NotificationPreferenceInput[K],
  ) => {
    setForm((current) => ({
      ...current,
      notification_preference: {
        ...current.notification_preference,
        [key]: value,
      },
    }));
  };

  const filterEnabled = (key: string): boolean => form.filters[key] === true;

  const toggleFilter = (key: string) => {
    patch("filters", {
      ...form.filters,
      [key]: !filterEnabled(key),
    });
  };

  const parseText = async () => {
    setBusy(true);
    setError("");
    try {
      const parsed = await parseNaturalLanguageSearch(naturalText);
      setForm((current) => ({
        ...current,
        ...parsed.data,
        name: parsed.data.city
          ? `${parsed.data.deal_type === "buy" ? "Купівля" : "Оренда"} · ${parsed.data.city}`
          : current.name,
        source_text: naturalText,
        notification_preference: current.notification_preference,
      }));
      setConfidence(parsed.confidence);
      setStep(3);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Не вдалося розібрати запит",
      );
    } finally {
      setBusy(false);
    }
  };

  const submit = async (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    const payload: SearchProfileInput = {
      ...form,
      source_text: naturalText || form.source_text,
    };
    try {
      if (profile) {
        await updateSearchProfile(profile.id, payload);
        onSaved?.();
      } else {
        await createSearchProfile(payload);
        onCreated?.();
        onSaved?.();
      }
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : editing
            ? "Не вдалося зберегти зміни"
            : "Не вдалося створити пошук",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="wizard-backdrop"
      role="presentation"
      data-testid="wizard-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        className="wizard-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="wizard-title"
        onClick={(event) => {
          event.stopPropagation();
        }}
      >
        <header className="wizard-header">
          <div>
            <span className="section-kicker">SEARCH SETUP</span>
            <h2 id="wizard-title">
              {editing ? "Редагувати пошук" : "Створити пошук"}
            </h2>
          </div>
          <button
            type="button"
            className="wizard-close"
            onClick={onClose}
            aria-label="Закрити"
          >
            ×
          </button>
        </header>

        <div className="wizard-body">
          {!editing && (
            <div className="wizard-mode-switch">
              <button
                type="button"
                className={mode === "form" ? "is-active" : ""}
                onClick={() => { setMode("form"); }}
              >
                Покроково
              </button>
              <button
                type="button"
                className={mode === "natural" ? "is-active" : ""}
                onClick={() => { setMode("natural"); }}
              >
                Описати словами
              </button>
            </div>
          )}

          {mode === "natural" && step < 3 && !editing ? (
            <div className="wizard-natural">
              <label htmlFor="natural-search">
                Опишіть квартиру своїми словами
              </label>
              <textarea
                id="natural-search"
                value={naturalText}
                onChange={(event) => { setNaturalText(event.target.value); }}
                placeholder="Шукаю однокімнатну квартиру у Львові до 18 тисяч, новобудова, не перший поверх, можна з котом, без комісії…"
              />
              <button
                type="button"
                className="button button--primary"
                disabled={busy || naturalText.trim().length < 10}
                onClick={() => void parseText()}
              >
                {busy ? "Аналізую…" : "Розібрати запит"}
              </button>
              {error && <p className="wizard-error">{error}</p>}
            </div>
          ) : (
            <form onSubmit={(event) => void submit(event)}>
              <div className="wizard-progress" aria-hidden="true">
                <span style={{ width: `${String((step / 3) * 100)}%` }} />
              </div>

              <div className="wizard-content">
                {step === 1 && (
                  <div className="wizard-grid">
                    <label>
                      Назва пошуку
                      <input
                        value={form.name}
                        onChange={(event) => { patch("name", event.target.value); }}
                        required
                      />
                    </label>
                    <label>
                      Місто
                      <input
                        value={form.city}
                        onChange={(event) => { patch("city", event.target.value); }}
                        required
                      />
                    </label>
                    <label>
                      Тип угоди
                      <select
                        value={form.deal_type}
                        onChange={(event) =>
                          { patch(
                            "deal_type",
                            event.target.value as "rent" | "buy",
                          ); }
                        }
                      >
                        <option value="rent">Оренда</option>
                        <option value="buy">Купівля</option>
                      </select>
                    </label>
                    <label>
                      Мінімальна ціна
                      <input
                        type="number"
                        min="0"
                        value={form.price_min ?? ""}
                        onChange={(event) =>
                          { patch(
                            "price_min",
                            event.target.value ? Number(event.target.value) : null,
                          ); }
                        }
                      />
                    </label>
                    <label>
                      Максимальна ціна
                      <input
                        type="number"
                        min="0"
                        value={form.price_max ?? ""}
                        onChange={(event) =>
                          { patch(
                            "price_max",
                            event.target.value ? Number(event.target.value) : null,
                          ); }
                        }
                        required
                      />
                    </label>
                    <label>
                      Кімнати
                      <input
                        value={form.rooms.join(",")}
                        onChange={(event) =>
                          { patch("rooms", csvNumbers(event.target.value)); }
                        }
                        placeholder="1,2"
                        required
                      />
                    </label>
                    <label>
                      Бажані райони
                      <input
                        value={form.desired_districts.join(", ")}
                        onChange={(event) =>
                          { patch("desired_districts", csvStrings(event.target.value)); }
                        }
                        placeholder="Франківський, Личаківський"
                      />
                    </label>
                    <label>
                      Виключені райони
                      <input
                        value={form.excluded_districts.join(", ")}
                        onChange={(event) =>
                          { patch("excluded_districts", csvStrings(event.target.value)); }
                        }
                        placeholder="Залізничний"
                      />
                    </label>
                    <label>
                      Дата заселення
                      <input
                        type="date"
                        value={form.move_in_date ?? ""}
                        onChange={(event) =>
                          { patch("move_in_date", event.target.value || null); }
                        }
                      />
                    </label>
                    <label>
                      Хто житиме
                      <input
                        type="number"
                        min="1"
                        max="20"
                        value={form.occupants}
                        onChange={(event) =>
                          { patch("occupants", Number(event.target.value)); }
                        }
                      />
                    </label>
                    <label>
                      Типи житла
                      <input
                        value={form.property_types.join(", ")}
                        onChange={(event) =>
                          { patch("property_types", csvStrings(event.target.value)); }
                        }
                        placeholder="apartment, house"
                      />
                    </label>
                  </div>
                )}

                {step === 2 && (
                  <div className="wizard-options">
                    <button
                      type="button"
                      className={form.pets.cat ? "option-chip is-active" : "option-chip"}
                      onClick={() =>
                        { patch("pets", { ...form.pets, cat: !form.pets.cat }); }
                      }
                    >
                      🐈 Можна з котом
                    </button>
                    <button
                      type="button"
                      className={form.pets.dog ? "option-chip is-active" : "option-chip"}
                      onClick={() =>
                        { patch("pets", { ...form.pets, dog: !form.pets.dog }); }
                      }
                    >
                      🐕 Можна із собакою
                    </button>
                    <button
                      type="button"
                      className={
                        filterEnabled("exclude_first_floor")
                          ? "option-chip is-active"
                          : "option-chip"
                      }
                      onClick={() => { toggleFilter("exclude_first_floor"); }}
                    >
                      Не перший поверх
                    </button>
                    <button
                      type="button"
                      className={
                        filterEnabled("exclude_last_floor")
                          ? "option-chip is-active"
                          : "option-chip"
                      }
                      onClick={() => { toggleFilter("exclude_last_floor"); }}
                    >
                      Не останній поверх
                    </button>
                    <button
                      type="button"
                      className={
                        form.filters.commission_allowed === false
                          ? "option-chip is-active"
                          : "option-chip"
                      }
                      onClick={() =>
                        { patch("filters", {
                          ...form.filters,
                          commission_allowed:
                            form.filters.commission_allowed !== false,
                        }); }
                      }
                    >
                      Без комісії
                    </button>
                    <button
                      type="button"
                      className={form.children ? "option-chip is-active" : "option-chip"}
                      onClick={() => { patch("children", !form.children); }}
                    >
                      Можна з дітьми
                    </button>
                    <label className="wizard-note-field">
                      Оригінальний опис пошуку
                      <textarea
                        value={naturalText}
                        onChange={(event) => { setNaturalText(event.target.value); }}
                        placeholder="Додаткові умови, які важливо не втратити"
                      />
                    </label>
                  </div>
                )}

                {step === 3 && (
                  <div className="wizard-review">
                    <h3>Сповіщення та перевірка</h3>
                    <div className="wizard-grid">
                      <label>
                        Частота
                        <select
                          value={form.notification_preference.frequency}
                          onChange={(event) =>
                            { patchNotification(
                              "frequency",
                              event.target.value as NotificationPreferenceInput["frequency"],
                            ); }
                          }
                        >
                          <option value="instant">Миттєво</option>
                          <option value="15m">Кожні 15 хвилин</option>
                          <option value="hourly">Щогодини</option>
                          <option value="twice_daily">Двічі на день</option>
                          <option value="daily">Щодня</option>
                        </select>
                      </label>
                      <label>
                        Мінімальний Match Score
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={form.notification_preference.min_match_score}
                          onChange={(event) =>
                            { patchNotification(
                              "min_match_score",
                              Number(event.target.value),
                            ); }
                          }
                        />
                      </label>
                      <label>
                        Максимальний Risk Score
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={form.notification_preference.max_risk_score}
                          onChange={(event) =>
                            { patchNotification(
                              "max_risk_score",
                              Number(event.target.value),
                            ); }
                          }
                        />
                      </label>
                      <label>
                        Денний ліміт
                        <input
                          type="number"
                          min="1"
                          max="100"
                          value={form.notification_preference.daily_limit}
                          onChange={(event) =>
                            { patchNotification("daily_limit", Number(event.target.value)); }
                          }
                        />
                      </label>
                      <label>
                        Тихі години з
                        <input
                          type="time"
                          value={form.notification_preference.quiet_hours_start}
                          disabled={!form.notification_preference.quiet_hours_enabled}
                          onChange={(event) =>
                            { patchNotification("quiet_hours_start", event.target.value); }
                          }
                        />
                      </label>
                      <label>
                        Тихі години до
                        <input
                          type="time"
                          value={form.notification_preference.quiet_hours_end}
                          disabled={!form.notification_preference.quiet_hours_enabled}
                          onChange={(event) =>
                            { patchNotification("quiet_hours_end", event.target.value); }
                          }
                        />
                      </label>
                    </div>
                    <div className="wizard-options">
                      <button
                        type="button"
                        className={
                          form.notification_preference.quiet_hours_enabled
                            ? "option-chip is-active"
                            : "option-chip"
                        }
                        onClick={() =>
                          { patchNotification(
                            "quiet_hours_enabled",
                            !form.notification_preference.quiet_hours_enabled,
                          ); }
                        }
                      >
                        Тихі години
                      </button>
                      <button
                        type="button"
                        className={
                          form.notification_preference.notify_price_changes
                            ? "option-chip is-active"
                            : "option-chip"
                        }
                        onClick={() =>
                          { patchNotification(
                            "notify_price_changes",
                            !form.notification_preference.notify_price_changes,
                          ); }
                        }
                      >
                        Зміни ціни
                      </button>
                      <button
                        type="button"
                        className={
                          form.notification_preference.notify_reactivated
                            ? "option-chip is-active"
                            : "option-chip"
                        }
                        onClick={() =>
                          { patchNotification(
                            "notify_reactivated",
                            !form.notification_preference.notify_reactivated,
                          ); }
                        }
                      >
                        Повторна активація
                      </button>
                    </div>
                    <dl>
                      <div>
                        <dt>Місто</dt>
                        <dd>{form.city || "Не вказано"}</dd>
                      </div>
                      <div>
                        <dt>Бюджет</dt>
                        <dd>
                          {form.price_min?.toLocaleString("uk-UA") ?? "0"}–
                          {form.price_max?.toLocaleString("uk-UA") ?? "∞"} грн
                        </dd>
                      </div>
                      <div>
                        <dt>Кімнати</dt>
                        <dd>{form.rooms.join(", ") || "—"}</dd>
                      </div>
                      <div>
                        <dt>Сповіщення</dt>
                        <dd>
                          {form.notification_preference.frequency}, Match від{" "}
                          {form.notification_preference.min_match_score}%
                        </dd>
                      </div>
                    </dl>
                    {Object.keys(confidence).length > 0 && (
                      <p className="confidence-note">
                        AI-поля підтверджені з рівнем упевненості. Відсутні умови не були вигадані.
                      </p>
                    )}
                  </div>
                )}

                {error && <p className="wizard-error">{error}</p>}
              </div>

              <footer className="wizard-footer">
                <button
                  type="button"
                  className="button button--secondary"
                  onClick={() => {
                    if (step === 1) onClose();
                    else setStep((value) => value - 1);
                  }}
                >
                  Назад
                </button>
                {step < 3 ? (
                  <button
                    type="button"
                    className="button button--primary"
                    onClick={() => { setStep((value) => value + 1); }}
                  >
                    Продовжити
                  </button>
                ) : (
                  <button
                    type="submit"
                    className="button button--primary"
                    disabled={busy}
                  >
                    {busy
                      ? "Зберігаю…"
                      : editing
                        ? "Зберегти зміни"
                        : "Створити пошук"}
                  </button>
                )}
              </footer>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}
