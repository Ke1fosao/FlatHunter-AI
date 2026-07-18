"use client";

import { useEffect, useMemo, useState } from "react";

import {
  ArrowIcon,
  CompareIcon,
  HeartIcon,
  HomeIcon,
  MapIcon,
  SearchIcon,
  SparkleIcon,
  UserIcon,
} from "@/components/icons";
import { useTelegram } from "@/hooks/use-telegram";
import {
  authenticateTelegram,
  fetchBackendHealth,
  type AuthenticatedUser,
  type HealthResponse,
} from "@/lib/api";
import { triggerSelectionFeedback } from "@/lib/telegram";
import en from "@/locales/en.json";
import uk from "@/locales/uk.json";

type Locale = "uk" | "en";
type Dictionary = typeof uk;
type ConnectionState = "checking" | "ready" | "degraded" | "offline";

export type AppNavigationTarget =
  | "search"
  | "dashboard"
  | "feed"
  | "map"
  | "favorites"
  | "compare"
  | "profile"
  | "ai";

type AppShellProps = {
  activeNavigation: "search" | "map" | "favorites" | "compare" | "profile";
  onCreateSearch: () => void;
  onNavigate: (target: AppNavigationTarget) => void;
};

const dictionaries: Record<Locale, Dictionary> = { uk, en };

function StatusDot({ status }: { status: ConnectionState }) {
  return (
    <span className={`status-dot status-dot--${status}`} aria-hidden="true" />
  );
}

export function AppShell({
  activeNavigation,
  onCreateSearch,
  onNavigate,
}: AppShellProps) {
  const telegram = useTelegram();
  const [locale, setLocale] = useState<Locale>("uk");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [connection, setConnection] = useState<ConnectionState>("checking");
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [authFailed, setAuthFailed] = useState(false);

  const dictionary = dictionaries[locale];

  useEffect(() => {
    const storedLocale = window.localStorage.getItem("flathunter-locale");
    if (storedLocale === "uk" || storedLocale === "en") {
      setLocale(storedLocale);
      return;
    }
    if (telegram.languageCode.startsWith("en")) {
      setLocale("en");
    }
  }, [telegram.languageCode]);

  useEffect(() => {
    const controller = new AbortController();
    const updateOnlineStatus = () => {
      setConnection(navigator.onLine ? "checking" : "offline");
    };

    const boot = async () => {
      if (!navigator.onLine) {
        setConnection("offline");
        return;
      }
      try {
        const response = await fetchBackendHealth(controller.signal);
        setHealth(response);
        setConnection(response.status === "ready" ? "ready" : "degraded");
      } catch {
        setConnection("degraded");
      }
    };

    void boot();
    window.addEventListener("online", updateOnlineStatus);
    window.addEventListener("offline", updateOnlineStatus);
    return () => {
      controller.abort();
      window.removeEventListener("online", updateOnlineStatus);
      window.removeEventListener("offline", updateOnlineStatus);
    };
  }, []);

  useEffect(() => {
    if (!telegram.initData) {
      return;
    }
    const controller = new AbortController();
    authenticateTelegram(telegram.initData, controller.signal)
      .then((response) => {
        setUser(response.user);
        setAuthFailed(false);
      })
      .catch(() => {
        setAuthFailed(true);
      });
    return () => {
      controller.abort();
    };
  }, [telegram.initData]);

  const displayName = user?.firstName ?? telegram.firstName;
  const statusLabel = useMemo(() => {
    if (connection === "ready") return dictionary.status.ready;
    if (connection === "checking") return dictionary.status.checking;
    if (connection === "offline") return dictionary.status.offline;
    return dictionary.status.degraded;
  }, [connection, dictionary]);

  const changeLocale = (nextLocale: Locale) => {
    setLocale(nextLocale);
    window.localStorage.setItem("flathunter-locale", nextLocale);
    triggerSelectionFeedback();
  };

  const navigate = (target: AppNavigationTarget) => {
    triggerSelectionFeedback();
    onNavigate(target);
  };

  const navItems = [
    { id: "search", label: dictionary.navigation.search, icon: SearchIcon },
    { id: "map", label: dictionary.navigation.map, icon: MapIcon },
    {
      id: "favorites",
      label: dictionary.navigation.favorites,
      icon: HeartIcon,
    },
    { id: "compare", label: dictionary.navigation.compare, icon: CompareIcon },
    { id: "profile", label: dictionary.navigation.profile, icon: UserIcon },
  ] as const;

  return (
    <main className="app-shell">
      <div className="ambient ambient--one" />
      <div className="ambient ambient--two" />

      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark">
            <HomeIcon />
          </span>
          <span>
            <strong>{dictionary.brand.name}</strong>
            <small>{dictionary.brand.tagline}</small>
          </span>
        </div>
        <div className="header-actions">
          <div
            className="language-switch"
            aria-label={dictionary.language.label}
          >
            {(["uk", "en"] as const).map((item) => (
              <button
                type="button"
                key={item}
                className={locale === item ? "is-active" : ""}
                onClick={() => {
                  changeLocale(item);
                }}
              >
                {dictionary.language[item]}
              </button>
            ))}
          </div>
          <div
            className="avatar"
            aria-label={
              displayName.length > 0 ? displayName : dictionary.brand.name
            }
          >
            {displayName ? displayName.slice(0, 1).toUpperCase() : "F"}
          </div>
        </div>
      </header>

      <section className="hero-card">
        <div className="hero-content">
          <div className="eyebrow">
            <SparkleIcon />
            {dictionary.hero.eyebrow}
          </div>
          <h1>{dictionary.hero.title}</h1>
          <p>{dictionary.hero.description}</p>
          <div className="hero-actions">
            <button
              className="button button--primary"
              type="button"
              onClick={onCreateSearch}
            >
              {dictionary.hero.primaryAction}
              <ArrowIcon />
            </button>
            <button
              className="button button--secondary"
              type="button"
              onClick={() => {
                navigate("feed");
              }}
            >
              {dictionary.hero.secondaryAction}
            </button>
          </div>
        </div>
        <div className="hero-orbit" aria-hidden="true">
          <div className="orbit-ring orbit-ring--outer" />
          <div className="orbit-ring orbit-ring--inner" />
          <div className="orbit-home">
            <HomeIcon />
          </div>
          <span className="orbit-pin orbit-pin--one">93%</span>
          <span className="orbit-pin orbit-pin--two">16.5k</span>
          <span className="orbit-pin orbit-pin--three">18m</span>
        </div>
      </section>

      <section className="stats-grid" aria-label="Statistics">
        <article>
          <span className="stat-icon">↗</span>
          <strong>42</strong>
          <small>{dictionary.stats.found}</small>
        </article>
        <article>
          <span className="stat-icon">◎</span>
          <strong>7</strong>
          <small>{dictionary.stats.matches}</small>
        </article>
        <article>
          <span className="stat-icon">✦</span>
          <strong>93%</strong>
          <small>{dictionary.stats.best}</small>
        </article>
      </section>

      <div className="content-grid">
        <section className="panel search-panel">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">01</span>
              <h2>{dictionary.search.title}</h2>
            </div>
            <button
              className="text-button"
              type="button"
              onClick={() => {
                navigate("dashboard");
              }}
            >
              {dictionary.search.edit}
            </button>
          </div>
          <div className="search-summary">
            <div className="search-icon">
              <SearchIcon />
            </div>
            <div className="search-copy">
              <strong>{dictionary.search.name}</strong>
              <span>{dictionary.search.criteria}</span>
            </div>
            <span className="active-pill">
              <span />
              {dictionary.search.status}
            </span>
          </div>
          <div className="search-progress">
            <span style={{ width: "72%" }} />
          </div>
          <div className="search-footer">
            <span>{dictionary.search.newItems}</span>
            <span>72% relevance floor</span>
          </div>
        </section>

        <section className="panel system-panel">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">SYS</span>
              <h2>{dictionary.status.title}</h2>
            </div>
            <span className={`system-badge system-badge--${connection}`}>
              <StatusDot status={connection} />
              {statusLabel}
            </span>
          </div>
          <div className="system-list">
            <div>
              <span>{dictionary.status.backend}</span>
              <span>
                <StatusDot status={connection} />
                {statusLabel}
              </span>
            </div>
            <div>
              <span>{dictionary.status.database}</span>
              <span>
                <StatusDot
                  status={
                    health?.checks.database === "ok" ? "ready" : connection
                  }
                />
                {health?.checks.database === "ok"
                  ? dictionary.status.ready
                  : statusLabel}
              </span>
            </div>
            <div>
              <span>{dictionary.status.cache}</span>
              <span>
                <StatusDot
                  status={health?.checks.cache === "ok" ? "ready" : connection}
                />
                {health?.checks.cache === "ok"
                  ? dictionary.status.ready
                  : statusLabel}
              </span>
            </div>
          </div>
          <p
            className={`system-message ${authFailed ? "system-message--error" : ""}`}
          >
            {authFailed
              ? dictionary.status.authError
              : connection === "degraded"
                ? dictionary.status.apiError
                : dictionary.status.previewDescription}
          </p>
          <span className="mode-label">
            {telegram.isTelegram
              ? dictionary.header.telegram
              : dictionary.header.preview}
          </span>
        </section>
      </div>

      <section className="listing-card">
        <div className="listing-visual">
          <div className="listing-gradient" />
          <div className="building building--back">
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
          <div className="building building--front">
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
          <span className="listing-badge">
            <SparkleIcon />
            {dictionary.listing.badge}
          </span>
          <span className="match-score">{dictionary.listing.match}</span>
        </div>
        <div className="listing-content">
          <div className="listing-topline">
            <span>{dictionary.listing.location}</span>
            <button
              type="button"
              aria-label={dictionary.navigation.favorites}
              onClick={() => {
                navigate("favorites");
              }}
            >
              <HeartIcon />
            </button>
          </div>
          <h2>{dictionary.listing.title}</h2>
          <strong className="listing-price">{dictionary.listing.price}</strong>
          <p className="listing-details">{dictionary.listing.details}</p>
          <div className="feature-chips">
            <span>🚋 {dictionary.listing.travel}</span>
            <span>🐈 {dictionary.listing.pet}</span>
            <span className="risk-chip">! {dictionary.listing.risk}</span>
          </div>
          <button
            className="button button--dark"
            type="button"
            onClick={() => {
              navigate("search");
            }}
          >
            {dictionary.listing.open}
            <ArrowIcon />
          </button>
        </div>
      </section>

      <section className="ai-summary">
        <span className="ai-mark">
          <SparkleIcon />
        </span>
        <div>
          <span className="section-kicker">AI DAILY</span>
          <h2>{dictionary.daily.title}</h2>
          <p>{dictionary.daily.text}</p>
          <small>{dictionary.daily.note}</small>
        </div>
      </section>

      <nav className="bottom-navigation" aria-label="Main navigation">
        {navItems.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={activeNavigation === id ? "is-active" : ""}
            onClick={() => {
              navigate(id);
            }}
          >
            <Icon />
            <span>{label}</span>
          </button>
        ))}
      </nav>
    </main>
  );
}
