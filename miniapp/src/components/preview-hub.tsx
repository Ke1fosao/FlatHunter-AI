"use client";

import { useMemo, useState } from "react";

type PreviewView = "search" | "map" | "favorites" | "compare" | "ai" | "profile";
type ListingFlag = "favorite" | "compared" | "hidden";

type PreviewListing = {
  id: string;
  title: string;
  city: string;
  district: string;
  street: string;
  price: number;
  rooms: number;
  area: number;
  floor: number;
  floorsTotal: number;
  match: number;
  risk: number;
  travelMinutes: number;
  petsAllowed: boolean;
  sources: string[];
  favorite: boolean;
  compared: boolean;
  hidden: boolean;
  note: string;
};

type PreviewProfile = {
  id: string;
  name: string;
  city: string;
  budgetMin: number;
  budgetMax: number;
  rooms: string;
  active: boolean;
  instantNotifications: boolean;
};

type SortMode = "match" | "price-asc" | "price-desc";

const navItems: readonly { id: PreviewView; label: string; icon: string }[] = [
  { id: "search", label: "Пошук", icon: "⌕" },
  { id: "map", label: "Карта", icon: "◉" },
  { id: "favorites", label: "Обране", icon: "♡" },
  { id: "compare", label: "Порівняння", icon: "⇄" },
  { id: "ai", label: "AI", icon: "✦" },
  { id: "profile", label: "Профіль", icon: "◎" },
];

const initialListings: PreviewListing[] = [
  {
    id: "preview-1",
    title: "Світла квартира біля Стрийського парку",
    city: "Львів",
    district: "Франківський",
    street: "вул. Стрийська, 42",
    price: 18500,
    rooms: 2,
    area: 56,
    floor: 5,
    floorsTotal: 9,
    match: 94,
    risk: 18,
    travelMinutes: 16,
    petsAllowed: true,
    sources: ["LUN", "OLX", "DIM.RIA"],
    favorite: false,
    compared: false,
    hidden: false,
    note: "",
  },
  {
    id: "preview-2",
    title: "Квартира з терасою на Під Голоском",
    city: "Львів",
    district: "Шевченківський",
    street: "вул. Під Голоском, 15",
    price: 22000,
    rooms: 2,
    area: 64,
    floor: 7,
    floorsTotal: 10,
    match: 89,
    risk: 27,
    travelMinutes: 21,
    petsAllowed: true,
    sources: ["OLX", "Rieltor.ua"],
    favorite: false,
    compared: false,
    hidden: false,
    note: "",
  },
  {
    id: "preview-3",
    title: "Двокімнатна квартира біля центру",
    city: "Львів",
    district: "Галицький",
    street: "вул. Личаківська, 21",
    price: 24500,
    rooms: 2,
    area: 51,
    floor: 3,
    floorsTotal: 4,
    match: 86,
    risk: 39,
    travelMinutes: 9,
    petsAllowed: false,
    sources: ["DIM.RIA"],
    favorite: false,
    compared: false,
    hidden: false,
    note: "",
  },
  {
    id: "preview-4",
    title: "Затишна квартира в новобудові на Сихові",
    city: "Львів",
    district: "Сихівський",
    street: "просп. Червоної Калини, 68",
    price: 16800,
    rooms: 1,
    area: 43,
    floor: 8,
    floorsTotal: 12,
    match: 81,
    risk: 22,
    travelMinutes: 28,
    petsAllowed: true,
    sources: ["LUN", "OLX"],
    favorite: false,
    compared: false,
    hidden: false,
    note: "",
  },
  {
    id: "preview-5",
    title: "Студія поруч із Львівською політехнікою",
    city: "Львів",
    district: "Франківський",
    street: "вул. Генерала Чупринки, 33",
    price: 14300,
    rooms: 1,
    area: 31,
    floor: 2,
    floorsTotal: 5,
    match: 77,
    risk: 46,
    travelMinutes: 7,
    petsAllowed: false,
    sources: ["OLX"],
    favorite: false,
    compared: false,
    hidden: false,
    note: "",
  },
];

const initialProfiles: PreviewProfile[] = [
  {
    id: "profile-demo-1",
    name: "Львів · 1–2 кімнати",
    city: "Львів",
    budgetMin: 12000,
    budgetMax: 23000,
    rooms: "1–2",
    active: true,
    instantNotifications: true,
  },
];

function formatPrice(value: number): string {
  return `${new Intl.NumberFormat("uk-UA").format(value)} грн`;
}

function PreviewListingCard({
  listing,
  onOpen,
  onToggle,
}: {
  listing: PreviewListing;
  onOpen: () => void;
  onToggle: (flag: ListingFlag) => void;
}) {
  return (
    <article className="preview-listing-card">
      <button
        type="button"
        className="preview-listing-card__main"
        onClick={onOpen}
        aria-label={`Відкрити ${listing.title}`}
      >
        <div className="preview-listing-card__visual">
          <strong>{listing.rooms}к</strong>
          <span>{listing.match}% Match</span>
          <small>{listing.sources.length} джерела</small>
        </div>
        <div className="preview-listing-card__body">
          <small>
            {listing.city} · {listing.district}
          </small>
          <h3>{listing.title}</h3>
          <strong>{formatPrice(listing.price)}</strong>
          <p>
            {listing.area} м² · {listing.floor}/{listing.floorsTotal} поверх ·{" "}
            {listing.travelMinutes} хв до важливої точки
          </p>
          <div className="preview-listing-card__chips">
            <span>Risk {listing.risk}/100</span>
            <span>{listing.petsAllowed ? "Тварини дозволені" : "Без тварин"}</span>
          </div>
        </div>
      </button>
      <div className="preview-listing-card__actions">
        <button
          type="button"
          className={listing.favorite ? "is-active" : undefined}
          onClick={() => {
            onToggle("favorite");
          }}
        >
          {listing.favorite ? "В обраному" : "В обране"}
        </button>
        <button
          type="button"
          className={listing.compared ? "is-active" : undefined}
          onClick={() => {
            onToggle("compared");
          }}
        >
          {listing.compared ? "У порівнянні" : "Порівняти"}
        </button>
        <button
          type="button"
          onClick={() => {
            onToggle("hidden");
          }}
        >
          Сховати
        </button>
      </div>
    </article>
  );
}

function EmptyPreview({ title, description }: { title: string; description: string }) {
  return (
    <div className="preview-empty">
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  );
}

export function PreviewHub() {
  const [view, setView] = useState<PreviewView>("search");
  const [listings, setListings] = useState<PreviewListing[]>(initialListings);
  const [profiles, setProfiles] = useState<PreviewProfile[]>(initialProfiles);
  const [selectedId, setSelectedId] = useState<string>("");
  const [aiListingId, setAiListingId] = useState(initialListings[0]?.id ?? "");
  const [aiText, setAiText] = useState("");
  const [wizardOpen, setWizardOpen] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [draftCity, setDraftCity] = useState("Львів");
  const [district, setDistrict] = useState("");
  const [rooms, setRooms] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [minScore, setMinScore] = useState("0");
  const [sort, setSort] = useState<SortMode>("match");
  const [locale, setLocale] = useState<"uk" | "en">("uk");
  const [quietHours, setQuietHours] = useState(true);
  const [message, setMessage] = useState("");

  const availableListings = useMemo(
    () => listings.filter((listing) => !listing.hidden),
    [listings],
  );

  const searchListings = useMemo(() => {
    const scoreFloor = Number(minScore) || 0;
    const ceiling = Number(maxPrice) || Number.POSITIVE_INFINITY;
    const filtered = availableListings.filter((listing) => {
      const districtMatches =
        district.trim().length === 0 ||
        listing.district.toLowerCase().includes(district.trim().toLowerCase());
      const roomsMatch = rooms.length === 0 || String(listing.rooms) === rooms;
      return districtMatches && roomsMatch && listing.price <= ceiling && listing.match >= scoreFloor;
    });
    return [...filtered].sort((left, right) => {
      if (sort === "price-asc") return left.price - right.price;
      if (sort === "price-desc") return right.price - left.price;
      return right.match - left.match;
    });
  }, [availableListings, district, maxPrice, minScore, rooms, sort]);

  const selectedListing = listings.find((listing) => listing.id === selectedId) ?? null;
  const aiListing = listings.find((listing) => listing.id === aiListingId) ?? availableListings.at(0) ?? null;
  const favoriteListings = availableListings.filter((listing) => listing.favorite);
  const comparedListings = availableListings.filter((listing) => listing.compared).slice(0, 4);

  const toggleListing = (id: string, flag: ListingFlag) => {
    const target = listings.find((listing) => listing.id === id);
    if (!target) return;
    if (flag === "compared" && !target.compared && comparedListings.length >= 4) {
      setMessage("Можна порівнювати максимум чотири квартири.");
      return;
    }
    setListings((current) =>
      current.map((listing) =>
        listing.id === id ? { ...listing, [flag]: !listing[flag] } : listing,
      ),
    );
    setMessage(
      flag === "favorite"
        ? target.favorite
          ? "Квартиру прибрано з обраного."
          : "Квартиру додано в обране."
        : flag === "compared"
          ? target.compared
            ? "Квартиру прибрано з порівняння."
            : "Квартиру додано до порівняння."
          : "Квартиру приховано зі стрічки.",
    );
  };

  const saveProfile = () => {
    const name = draftName.trim();
    if (name.length === 0) {
      setMessage("Вкажіть назву пошуку.");
      return;
    }
    setProfiles((current) => [
      ...current,
      {
        id: `profile-preview-${String(current.length + 1)}`,
        name,
        city: draftCity.trim() || "Львів",
        budgetMin: 12000,
        budgetMax: 24000,
        rooms: "1–2",
        active: true,
        instantNotifications: true,
      },
    ]);
    setDraftName("");
    setDraftCity("Львів");
    setWizardOpen(false);
    setMessage("Пошуковий профіль збережено в демо-режимі.");
  };

  const setNote = (id: string, note: string) => {
    setListings((current) =>
      current.map((listing) => (listing.id === id ? { ...listing, note } : listing)),
    );
  };

  const renderListings = (items: PreviewListing[]) => {
    if (items.length === 0) {
      return (
        <EmptyPreview
          title="Тут поки порожньо"
          description="Змініть фільтри або додайте квартири з пошукової стрічки."
        />
      );
    }
    return (
      <div className="preview-listing-grid">
        {items.map((listing) => (
          <PreviewListingCard
            key={listing.id}
            listing={listing}
            onOpen={() => {
              setSelectedId(listing.id);
            }}
            onToggle={(flag) => {
              toggleListing(listing.id, flag);
            }}
          />
        ))}
      </div>
    );
  };

  return (
    <section className="preview-hub">
      <div className="preview-hub__banner" role="status">
        <strong>Браузерний демо-режим</strong>
        <span>
          Тут усе працює локально. У Telegram ті самі дії синхронізуються з вашим backend-профілем.
        </span>
      </div>

      <header className="preview-hub__hero">
        <div>
          <span>FLATHUNTER AI · FULL WEBSITE</span>
          <h1>Повна демо-версія FlatHunter</h1>
          <p>
            Пошуки, кластеризовані квартири, карта, обране, порівняння, AI,
            нотатки та налаштування сповіщень доступні прямо на сайті — без
            порожнього екрану.
          </p>
        </div>
        <button
          type="button"
          className="preview-hub__primary"
          onClick={() => {
            setWizardOpen(true);
          }}
        >
          Створити пошук
        </button>
      </header>

      <nav className="preview-hub__nav" aria-label="Демо-навігація">
        {navItems.map((item) => (
          <button
            key={item.id}
            type="button"
            className={view === item.id ? "is-active" : undefined}
            onClick={() => {
              setView(item.id);
              setMessage("");
            }}
          >
            <span aria-hidden="true">{item.icon}</span>
            {item.label}
            {item.id === "favorites" && favoriteListings.length > 0 && (
              <small>{favoriteListings.length}</small>
            )}
            {item.id === "compare" && comparedListings.length > 0 && (
              <small>{comparedListings.length}</small>
            )}
          </button>
        ))}
      </nav>

      {message.length > 0 && (
        <p className="preview-hub__message" role="status">
          {message}
        </p>
      )}

      {view === "search" && (
        <div className="preview-hub__workspace">
          <section className="preview-profile-strip">
            <div className="preview-section-heading">
              <div>
                <span>ПОШУКОВІ ПРОФІЛІ</span>
                <h2>Активні пошуки</h2>
              </div>
              <button
                type="button"
                onClick={() => {
                  setWizardOpen(true);
                }}
              >
                Додати
              </button>
            </div>
            <div className="preview-profile-grid">
              {profiles.map((profile) => (
                <article key={profile.id}>
                  <div>
                    <small>{profile.city}</small>
                    <strong>{profile.name}</strong>
                    <span>
                      {formatPrice(profile.budgetMin)} – {formatPrice(profile.budgetMax)} · {profile.rooms} кімн.
                    </span>
                  </div>
                  <button
                    type="button"
                    className={profile.active ? "is-active" : undefined}
                    onClick={() => {
                      setProfiles((current) =>
                        current.map((item) =>
                          item.id === profile.id ? { ...item, active: !item.active } : item,
                        ),
                      );
                    }}
                  >
                    {profile.active ? "Активний" : "Призупинено"}
                  </button>
                </article>
              ))}
            </div>
          </section>

          <section className="preview-filter-panel">
            <label>
              Район
              <input
                value={district}
                placeholder="Наприклад, Франківський"
                onChange={(event) => {
                  setDistrict(event.target.value);
                }}
              />
            </label>
            <label>
              Кімнати
              <select
                value={rooms}
                onChange={(event) => {
                  setRooms(event.target.value);
                }}
              >
                <option value="">Усі</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
              </select>
            </label>
            <label>
              Ціна до
              <input
                inputMode="numeric"
                value={maxPrice}
                placeholder="25000"
                onChange={(event) => {
                  setMaxPrice(event.target.value);
                }}
              />
            </label>
            <label>
              Match від
              <select
                value={minScore}
                onChange={(event) => {
                  setMinScore(event.target.value);
                }}
              >
                <option value="0">0%</option>
                <option value="70">70%</option>
                <option value="80">80%</option>
                <option value="90">90%</option>
              </select>
            </label>
            <label>
              Сортування
              <select
                value={sort}
                onChange={(event) => {
                  setSort(event.target.value as SortMode);
                }}
              >
                <option value="match">Найкращий Match</option>
                <option value="price-asc">Спочатку дешевші</option>
                <option value="price-desc">Спочатку дорожчі</option>
              </select>
            </label>
          </section>

          <div className="preview-section-heading">
            <div>
              <span>ОДНА КВАРТИРА · ОДНА КАРТКА</span>
              <h2>Знайдені квартири</h2>
            </div>
            <strong>{searchListings.length}</strong>
          </div>
          {renderListings(searchListings)}
        </div>
      )}

      {view === "map" && (
        <div className="preview-hub__workspace">
          <div className="preview-section-heading">
            <div>
              <span>КАРТА</span>
              <h2>Квартири та важливі місця</h2>
            </div>
          </div>
          <div className="preview-map">
            <div className="preview-map__roads" />
            <span className="preview-map__place preview-map__place--one">◆ Університет</span>
            <span className="preview-map__place preview-map__place--two">◆ Центр</span>
            {availableListings.map((listing, index) => (
              <button
                key={listing.id}
                type="button"
                className={listing.favorite ? "is-favorite" : undefined}
                style={{
                  left: `${String(12 + (index * 17) % 72)}%`,
                  top: `${String(18 + (index * 23) % 58)}%`,
                }}
                aria-label={`Відкрити ${listing.title}`}
                onClick={() => {
                  setSelectedId(listing.id);
                }}
              >
                {Math.round(listing.price / 1000)}k
              </button>
            ))}
          </div>
          {renderListings(availableListings.slice(0, 3))}
        </div>
      )}

      {view === "favorites" && (
        <div className="preview-hub__workspace">
          <div className="preview-section-heading">
            <div>
              <span>ЗБЕРЕЖЕНІ ВАРІАНТИ</span>
              <h2>Обране</h2>
            </div>
            <strong>{favoriteListings.length}</strong>
          </div>
          {renderListings(favoriteListings)}
        </div>
      )}

      {view === "compare" && (
        <div className="preview-hub__workspace">
          <div className="preview-section-heading">
            <div>
              <span>ВИБІР БЕЗ ХАОСУ</span>
              <h2>Порівняння квартир</h2>
            </div>
            <strong>{comparedListings.length}/4</strong>
          </div>
          {comparedListings.length < 2 ? (
            <EmptyPreview
              title="Додайте щонайменше дві квартири"
              description="Поверніться до пошуку та натисніть «Порівняти» на потрібних картках."
            />
          ) : (
            <div className="preview-compare-scroll">
              <table className="preview-compare-table">
                <thead>
                  <tr>
                    <th>Параметр</th>
                    {comparedListings.map((listing) => (
                      <th key={listing.id}>{listing.title}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th>Ціна</th>
                    {comparedListings.map((listing) => (
                      <td key={listing.id}>{formatPrice(listing.price)}</td>
                    ))}
                  </tr>
                  <tr>
                    <th>Match</th>
                    {comparedListings.map((listing) => (
                      <td key={listing.id}>{listing.match}%</td>
                    ))}
                  </tr>
                  <tr>
                    <th>Risk Score</th>
                    {comparedListings.map((listing) => (
                      <td key={listing.id}>{listing.risk}/100</td>
                    ))}
                  </tr>
                  <tr>
                    <th>Площа</th>
                    {comparedListings.map((listing) => (
                      <td key={listing.id}>{listing.area} м²</td>
                    ))}
                  </tr>
                  <tr>
                    <th>Джерела</th>
                    {comparedListings.map((listing) => (
                      <td key={listing.id}>{listing.sources.length}</td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {view === "ai" && (
        <div className="preview-hub__workspace preview-ai">
          <div className="preview-section-heading">
            <div>
              <span>AI-ПОМІЧНИК</span>
              <h2>Перевірка квартири перед дзвінком</h2>
            </div>
          </div>
          <label>
            Квартира для AI
            <select
              value={aiListing?.id ?? ""}
              onChange={(event) => {
                setAiListingId(event.target.value);
                setAiText("");
              }}
            >
              {availableListings.map((listing) => (
                <option key={listing.id} value={listing.id}>
                  {listing.title}
                </option>
              ))}
            </select>
          </label>
          <div className="preview-ai__actions">
            <button
              type="button"
              disabled={!aiListing}
              onClick={() => {
                if (!aiListing) return;
                setAiText(
                  `Match ${String(aiListing.match)}%. Ціна ${formatPrice(aiListing.price)} виглядає конкурентною для району ${aiListing.district}. Risk Score ${String(aiListing.risk)}/100. Перевірте право власності, комунальні платежі та причину здачі.`,
                );
              }}
            >
              Згенерувати резюме
            </button>
            <button
              type="button"
              disabled={!aiListing}
              onClick={() => {
                if (!aiListing) return;
                setAiText(
                  "1. Хто є власником квартири? 2. Які комунальні платежі взимку? 3. Чи дозволена реєстрація та тварини? 4. Чи фіксується ціна в договорі? 5. Яка причина попереднього виїзду орендарів?",
                );
              }}
            >
              Питання власнику
            </button>
          </div>
          {aiText.length > 0 && (
            <article className="preview-ai__result">
              <strong>AI-висновок</strong>
              <p>{aiText}</p>
            </article>
          )}
        </div>
      )}

      {view === "profile" && (
        <div className="preview-hub__workspace">
          <div className="preview-section-heading">
            <div>
              <span>ПРОФІЛЬ ТА СПОВІЩЕННЯ</span>
              <h2>Налаштування</h2>
            </div>
          </div>
          <div className="preview-settings-grid">
            <article>
              <span>Мова інтерфейсу</span>
              <div>
                <button
                  type="button"
                  className={locale === "uk" ? "is-active" : undefined}
                  onClick={() => {
                    setLocale("uk");
                  }}
                >
                  Українська
                </button>
                <button
                  type="button"
                  className={locale === "en" ? "is-active" : undefined}
                  onClick={() => {
                    setLocale("en");
                  }}
                >
                  English
                </button>
              </div>
            </article>
            <article>
              <span>Тихі години</span>
              <strong>{quietHours ? "23:00–08:00" : "Вимкнено"}</strong>
              <button
                type="button"
                onClick={() => {
                  setQuietHours((current) => !current);
                }}
              >
                {quietHours ? "Вимкнути" : "Увімкнути"}
              </button>
            </article>
            <article>
              <span>Синхронізація</span>
              <strong>Browser preview</strong>
              <small>У Telegram дані зберігаються в Django та доступні на всіх пристроях.</small>
            </article>
          </div>
          <div className="preview-profile-grid preview-profile-grid--manager">
            {profiles.map((profile) => (
              <article key={profile.id}>
                <div>
                  <small>{profile.city}</small>
                  <strong>{profile.name}</strong>
                  <span>{profile.instantNotifications ? "Миттєві сповіщення" : "Дайджест"}</span>
                </div>
                <div className="preview-profile-actions">
                  <button
                    type="button"
                    onClick={() => {
                      setProfiles((current) =>
                        current.map((item) =>
                          item.id === profile.id
                            ? { ...item, instantNotifications: !item.instantNotifications }
                            : item,
                        ),
                      );
                    }}
                  >
                    Змінити частоту
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setProfiles((current) => current.filter((item) => item.id !== profile.id));
                    }}
                  >
                    Видалити
                  </button>
                </div>
              </article>
            ))}
          </div>
        </div>
      )}

      {selectedListing && (
        <div
          className="preview-detail-backdrop"
          role="presentation"
          onMouseDown={() => {
            setSelectedId("");
          }}
        >
          <aside
            className="preview-detail"
            role="dialog"
            aria-modal="true"
            aria-label="Деталі квартири"
            onMouseDown={(event) => {
              event.stopPropagation();
            }}
          >
            <button
              type="button"
              className="preview-detail__close"
              aria-label="Закрити"
              onClick={() => {
                setSelectedId("");
              }}
            >
              ×
            </button>
            <small>
              {selectedListing.city} · {selectedListing.district}
            </small>
            <h2>{selectedListing.title}</h2>
            <strong className="preview-detail__price">{formatPrice(selectedListing.price)}</strong>
            <div className="preview-detail__facts">
              <div><span>Match</span><strong>{selectedListing.match}%</strong></div>
              <div><span>Risk</span><strong>{selectedListing.risk}/100</strong></div>
              <div><span>Площа</span><strong>{selectedListing.area} м²</strong></div>
              <div><span>Поверх</span><strong>{selectedListing.floor}/{selectedListing.floorsTotal}</strong></div>
            </div>
            <p>{selectedListing.street}</p>
            <div className="preview-detail__sources">
              <span>Джерела оголошення</span>
              {selectedListing.sources.map((source) => (
                <strong key={source}>{source}</strong>
              ))}
            </div>
            <label>
              Ваша нотатка
              <textarea
                value={selectedListing.note}
                placeholder="Що потрібно уточнити у власника?"
                onChange={(event) => {
                  setNote(selectedListing.id, event.target.value);
                }}
              />
            </label>
            <div className="preview-detail__actions">
              <button
                type="button"
                onClick={() => {
                  toggleListing(selectedListing.id, "favorite");
                }}
              >
                {selectedListing.favorite ? "Прибрати з обраного" : "Додати в обране"}
              </button>
              <button
                type="button"
                onClick={() => {
                  toggleListing(selectedListing.id, "compared");
                }}
              >
                {selectedListing.compared ? "Прибрати з порівняння" : "Додати до порівняння"}
              </button>
            </div>
          </aside>
        </div>
      )}

      {wizardOpen && (
        <div className="preview-detail-backdrop" role="presentation">
          <form
            className="preview-wizard"
            role="dialog"
            aria-modal="true"
            aria-label="Створення пошуку"
            onSubmit={(event) => {
              event.preventDefault();
              saveProfile();
            }}
          >
            <button
              type="button"
              className="preview-detail__close"
              aria-label="Закрити"
              onClick={() => {
                setWizardOpen(false);
              }}
            >
              ×
            </button>
            <span>НОВИЙ ПОШУК</span>
            <h2>Що саме шукаємо?</h2>
            <label>
              Назва пошуку
              <input
                autoFocus
                value={draftName}
                placeholder="Наприклад, квартира біля центру"
                onChange={(event) => {
                  setDraftName(event.target.value);
                }}
              />
            </label>
            <label>
              Місто
              <input
                value={draftCity}
                onChange={(event) => {
                  setDraftCity(event.target.value);
                }}
              />
            </label>
            <div className="preview-wizard__summary">
              <span>Бюджет</span><strong>12 000–24 000 грн</strong>
              <span>Кімнати</span><strong>1–2</strong>
              <span>Сповіщення</span><strong>Миттєво</strong>
            </div>
            <button type="submit" className="preview-hub__primary">
              Зберегти пошук
            </button>
          </form>
        </div>
      )}

      <style jsx global>{`
        .preview-hub {
          width: min(1180px, calc(100% - 28px));
          margin: 18px auto 120px;
          display: grid;
          gap: 16px;
        }
        .preview-hub__banner {
          padding: 11px 14px;
          display: flex;
          align-items: center;
          gap: 10px;
          border: 1px solid color-mix(in srgb, var(--accent) 38%, var(--line));
          border-radius: 14px;
          background: color-mix(in srgb, var(--accent) 10%, var(--surface-solid));
          color: var(--muted);
          font-size: 12px;
        }
        .preview-hub__banner strong {
          color: var(--accent);
          white-space: nowrap;
        }
        .preview-hub__hero {
          padding: 26px;
          display: flex;
          align-items: end;
          justify-content: space-between;
          gap: 24px;
          border: 1px solid var(--line);
          border-radius: 28px;
          background:
            radial-gradient(circle at 85% 10%, color-mix(in srgb, var(--accent) 24%, transparent), transparent 35%),
            linear-gradient(135deg, color-mix(in srgb, var(--accent) 9%, var(--surface-solid)), var(--surface-solid));
          box-shadow: var(--shadow);
        }
        .preview-hub__hero span,
        .preview-section-heading span,
        .preview-wizard > span {
          font-size: 10px;
          font-weight: 900;
          letter-spacing: 0.14em;
          color: var(--accent);
        }
        .preview-hub__hero h1 {
          margin: 8px 0;
          max-width: 760px;
          font-size: clamp(27px, 5vw, 48px);
          line-height: 1.02;
        }
        .preview-hub__hero p {
          max-width: 760px;
          margin: 0;
          color: var(--muted);
          line-height: 1.6;
        }
        .preview-hub__primary {
          min-height: 48px;
          padding: 0 18px;
          border: 0;
          border-radius: 15px;
          background: var(--accent);
          color: var(--accent-text);
          font-weight: 900;
          cursor: pointer;
          white-space: nowrap;
        }
        .preview-hub__nav {
          display: grid;
          grid-template-columns: repeat(6, minmax(0, 1fr));
          gap: 8px;
        }
        .preview-hub__nav button {
          min-height: 52px;
          padding: 0 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 7px;
          position: relative;
          border: 1px solid var(--line);
          border-radius: 15px;
          background: var(--surface-solid);
          color: var(--muted);
          font-weight: 850;
          cursor: pointer;
        }
        .preview-hub__nav button.is-active {
          border-color: var(--accent);
          background: color-mix(in srgb, var(--accent) 12%, var(--surface-solid));
          color: var(--accent);
        }
        .preview-hub__nav small {
          min-width: 18px;
          height: 18px;
          display: inline-grid;
          place-items: center;
          border-radius: 999px;
          background: var(--accent);
          color: var(--accent-text);
          font-size: 9px;
        }
        .preview-hub__message {
          margin: 0;
          padding: 11px 14px;
          border: 1px solid var(--line);
          border-radius: 13px;
          background: var(--surface-solid);
          color: var(--muted);
        }
        .preview-hub__workspace {
          display: grid;
          gap: 16px;
        }
        .preview-profile-strip,
        .preview-filter-panel,
        .preview-ai,
        .preview-settings-grid > article {
          border: 1px solid var(--line);
          border-radius: 22px;
          background: var(--surface-solid);
          box-shadow: var(--shadow);
        }
        .preview-profile-strip,
        .preview-ai {
          padding: 20px;
        }
        .preview-section-heading {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
        }
        .preview-section-heading h2 {
          margin: 5px 0 0;
        }
        .preview-section-heading > strong {
          min-width: 40px;
          height: 40px;
          display: grid;
          place-items: center;
          border-radius: 13px;
          background: color-mix(in srgb, var(--accent) 12%, var(--surface-solid));
          color: var(--accent);
        }
        .preview-section-heading button,
        .preview-profile-grid article > button,
        .preview-profile-actions button {
          min-height: 38px;
          padding: 0 12px;
          border: 1px solid var(--line);
          border-radius: 11px;
          background: var(--bg);
          color: var(--text);
          font-weight: 800;
          cursor: pointer;
        }
        .preview-profile-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
          margin-top: 14px;
        }
        .preview-profile-grid article {
          padding: 14px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          border: 1px solid var(--line);
          border-radius: 16px;
          background: var(--bg);
        }
        .preview-profile-grid article > div:first-child {
          display: grid;
          gap: 4px;
        }
        .preview-profile-grid small,
        .preview-profile-grid span {
          color: var(--muted);
        }
        .preview-profile-grid article > button.is-active {
          border-color: var(--accent);
          color: var(--accent);
        }
        .preview-filter-panel {
          padding: 14px;
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 10px;
        }
        .preview-filter-panel label,
        .preview-ai label,
        .preview-detail label,
        .preview-wizard label {
          display: grid;
          gap: 6px;
          color: var(--muted);
          font-size: 12px;
          font-weight: 800;
        }
        .preview-filter-panel input,
        .preview-filter-panel select,
        .preview-ai select,
        .preview-detail textarea,
        .preview-wizard input {
          min-height: 42px;
          width: 100%;
          padding: 0 12px;
          border: 1px solid var(--line);
          border-radius: 12px;
          background: var(--bg);
          color: var(--text);
          font: inherit;
        }
        .preview-detail textarea {
          min-height: 96px;
          padding: 10px 12px;
          resize: vertical;
        }
        .preview-listing-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
        }
        .preview-listing-card {
          overflow: hidden;
          border: 1px solid var(--line);
          border-radius: 21px;
          background: var(--surface-solid);
          box-shadow: var(--shadow);
        }
        .preview-listing-card__main {
          width: 100%;
          padding: 0;
          display: grid;
          grid-template-columns: 150px minmax(0, 1fr);
          text-align: left;
          border: 0;
          background: transparent;
          color: inherit;
          cursor: pointer;
        }
        .preview-listing-card__visual {
          min-height: 190px;
          padding: 16px;
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          justify-content: space-between;
          background:
            linear-gradient(160deg, color-mix(in srgb, var(--accent) 58%, #101820), #19241f 64%, #0d1110);
          color: white;
        }
        .preview-listing-card__visual strong {
          font-size: 34px;
        }
        .preview-listing-card__visual span,
        .preview-listing-card__visual small {
          padding: 5px 8px;
          border-radius: 9px;
          background: rgba(0, 0, 0, 0.34);
          font-weight: 850;
        }
        .preview-listing-card__body {
          padding: 16px;
          display: grid;
          align-content: center;
          gap: 7px;
        }
        .preview-listing-card__body small,
        .preview-listing-card__body p {
          color: var(--muted);
        }
        .preview-listing-card__body h3,
        .preview-listing-card__body p {
          margin: 0;
        }
        .preview-listing-card__chips {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
        .preview-listing-card__chips span {
          padding: 5px 7px;
          border-radius: 8px;
          background: var(--bg);
          color: var(--muted);
          font-size: 10px;
          font-weight: 800;
        }
        .preview-listing-card__actions {
          padding: 10px;
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 7px;
          border-top: 1px solid var(--line);
        }
        .preview-listing-card__actions button,
        .preview-detail__actions button,
        .preview-ai__actions button,
        .preview-settings-grid button {
          min-height: 39px;
          padding: 0 10px;
          border: 1px solid var(--line);
          border-radius: 11px;
          background: var(--bg);
          color: var(--muted);
          font-weight: 800;
          cursor: pointer;
        }
        .preview-listing-card__actions button.is-active,
        .preview-settings-grid button.is-active {
          border-color: var(--accent);
          background: color-mix(in srgb, var(--accent) 10%, var(--bg));
          color: var(--accent);
        }
        .preview-empty {
          padding: 42px 20px;
          display: grid;
          place-items: center;
          text-align: center;
          border: 1px dashed var(--line);
          border-radius: 22px;
          background: var(--surface-solid);
        }
        .preview-empty strong {
          font-size: 18px;
        }
        .preview-empty p {
          max-width: 500px;
          margin: 6px 0 0;
          color: var(--muted);
        }
        .preview-map {
          min-height: 420px;
          position: relative;
          overflow: hidden;
          border: 1px solid var(--line);
          border-radius: 24px;
          background:
            linear-gradient(35deg, transparent 46%, color-mix(in srgb, var(--line) 65%, transparent) 47%, color-mix(in srgb, var(--line) 65%, transparent) 50%, transparent 51%),
            linear-gradient(145deg, transparent 43%, color-mix(in srgb, var(--line) 55%, transparent) 44%, color-mix(in srgb, var(--line) 55%, transparent) 48%, transparent 49%),
            color-mix(in srgb, var(--accent) 5%, var(--surface-solid));
        }
        .preview-map button {
          width: 52px;
          height: 52px;
          position: absolute;
          z-index: 2;
          transform: translate(-50%, -50%);
          border: 4px solid var(--surface-solid);
          border-radius: 50% 50% 50% 12%;
          background: var(--accent);
          color: var(--accent-text);
          font-weight: 900;
          cursor: pointer;
          rotate: -45deg;
        }
        .preview-map button::first-line {
          rotate: 45deg;
        }
        .preview-map button.is-favorite {
          box-shadow: 0 0 0 5px color-mix(in srgb, var(--accent) 25%, transparent);
        }
        .preview-map__place {
          position: absolute;
          z-index: 1;
          padding: 7px 9px;
          border: 1px solid var(--line);
          border-radius: 10px;
          background: var(--surface-solid);
          color: var(--muted);
          font-size: 11px;
          font-weight: 850;
        }
        .preview-map__place--one { left: 14%; bottom: 16%; }
        .preview-map__place--two { right: 12%; top: 13%; }
        .preview-compare-scroll {
          overflow-x: auto;
          border: 1px solid var(--line);
          border-radius: 20px;
          background: var(--surface-solid);
        }
        .preview-compare-table {
          width: 100%;
          min-width: 720px;
          border-collapse: collapse;
        }
        .preview-compare-table th,
        .preview-compare-table td {
          padding: 14px;
          text-align: left;
          border-bottom: 1px solid var(--line);
        }
        .preview-compare-table th:first-child {
          color: var(--muted);
        }
        .preview-ai__actions,
        .preview-detail__actions {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 9px;
        }
        .preview-ai__result {
          padding: 16px;
          border: 1px solid color-mix(in srgb, var(--accent) 35%, var(--line));
          border-radius: 16px;
          background: color-mix(in srgb, var(--accent) 8%, var(--bg));
        }
        .preview-ai__result p {
          margin: 7px 0 0;
          color: var(--muted);
          line-height: 1.65;
        }
        .preview-settings-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 10px;
        }
        .preview-settings-grid > article {
          padding: 17px;
          display: grid;
          gap: 10px;
        }
        .preview-settings-grid > article > span,
        .preview-settings-grid small {
          color: var(--muted);
        }
        .preview-settings-grid article > div {
          display: flex;
          gap: 7px;
        }
        .preview-profile-grid--manager {
          grid-template-columns: 1fr;
        }
        .preview-profile-actions {
          display: flex;
          gap: 7px;
        }
        .preview-detail-backdrop {
          position: fixed;
          inset: 0;
          z-index: 1000;
          padding: 18px;
          display: grid;
          place-items: center;
          background: rgba(4, 7, 6, 0.72);
          backdrop-filter: blur(10px);
        }
        .preview-detail,
        .preview-wizard {
          width: min(620px, 100%);
          max-height: calc(100dvh - 36px);
          overflow: auto;
          position: relative;
          padding: 24px;
          display: grid;
          gap: 15px;
          border: 1px solid var(--line);
          border-radius: 24px;
          background: var(--surface-solid);
          box-shadow: 0 28px 90px rgba(0, 0, 0, 0.4);
        }
        .preview-detail h2,
        .preview-wizard h2 {
          margin: 0;
        }
        .preview-detail__close {
          width: 38px;
          height: 38px;
          position: absolute;
          top: 12px;
          right: 12px;
          border: 1px solid var(--line);
          border-radius: 12px;
          background: var(--bg);
          color: var(--text);
          font-size: 22px;
          cursor: pointer;
        }
        .preview-detail__price {
          color: var(--accent);
          font-size: 24px;
        }
        .preview-detail__facts {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 8px;
        }
        .preview-detail__facts div {
          padding: 11px;
          display: grid;
          gap: 4px;
          border: 1px solid var(--line);
          border-radius: 13px;
          background: var(--bg);
        }
        .preview-detail__facts span,
        .preview-detail > p {
          color: var(--muted);
        }
        .preview-detail__sources {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 7px;
        }
        .preview-detail__sources span {
          width: 100%;
          color: var(--muted);
        }
        .preview-detail__sources strong {
          padding: 6px 9px;
          border-radius: 9px;
          background: var(--bg);
        }
        .preview-wizard__summary {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 8px 16px;
          padding: 14px;
          border: 1px solid var(--line);
          border-radius: 14px;
          background: var(--bg);
        }
        .preview-wizard__summary span {
          color: var(--muted);
        }
        @media (max-width: 850px) {
          .preview-hub__nav {
            grid-template-columns: repeat(3, minmax(0, 1fr));
          }
          .preview-filter-panel {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .preview-listing-grid,
          .preview-profile-grid,
          .preview-settings-grid {
            grid-template-columns: 1fr;
          }
        }
        @media (max-width: 620px) {
          .preview-hub__hero {
            padding: 20px;
            align-items: stretch;
            flex-direction: column;
          }
          .preview-hub__banner {
            align-items: flex-start;
            flex-direction: column;
          }
          .preview-listing-card__main {
            grid-template-columns: 1fr;
          }
          .preview-listing-card__visual {
            min-height: 150px;
          }
          .preview-listing-card__actions,
          .preview-detail__actions,
          .preview-ai__actions {
            grid-template-columns: 1fr;
          }
          .preview-detail__facts {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .preview-map {
            min-height: 360px;
          }
        }
        @media (max-width: 420px) {
          .preview-hub__nav {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .preview-filter-panel {
            grid-template-columns: 1fr;
          }
          .preview-profile-grid article {
            align-items: stretch;
            flex-direction: column;
          }
        }
      `}</style>
    </section>
  );
}
