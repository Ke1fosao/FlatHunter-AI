"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  fetchMarketAnalysis,
  fetchPriceHistory,
  fetchRiskAnalysis,
  refreshListingAnalysis,
  type AnalysisSummary,
  type MarketAnalysisResponse,
  type PriceHistoryResponse,
  type RiskAnalysisResponse
} from "@/lib/analysis-api";
import { ApiError } from "@/lib/api";

function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${new Intl.NumberFormat("uk-UA").format(value)} грн`;
}

function statusLabel(status: string): string {
  if (status === "ready") return "Готово";
  if (status === "insufficient_data") return "Недостатньо даних";
  if (status === "stale") return "Потребує оновлення";
  if (status === "failed") return "Помилка аналізу";
  if (status === "disabled") return "Аналіз вимкнено";
  return "Очікує аналізу";
}

function riskLabel(level: string | undefined): string {
  if (level === "low") return "Низький ризик";
  if (level === "review") return "Є моменти для перевірки";
  if (level === "elevated") return "Підвищений ризик";
  return "Недостатньо даних";
}

function riskIcon(level: string | undefined): string {
  if (level === "low") return "✓";
  if (level === "review") return "!";
  if (level === "elevated") return "⚠";
  return "?";
}

export function AnalysisChips({ summary }: { summary?: AnalysisSummary }) {
  if (!summary) return null;
  const market = summary.market;
  const risk = summary.risk;
  const change = summary.latest_price_change;
  return (
    <div className="analysis-chips" aria-label="Коротка аналітика квартири">
      {change && (
        <span className={`analysis-chip analysis-chip--${change.direction}`}>
          {change.direction === "decrease" ? "↓" : "↑"} {Math.abs(Number(change.change_percent)).toFixed(1)}% ціна
        </span>
      )}
      {market.status === "ready" && ["medium", "high"].includes(market.confidence_label ?? "") && (
        <span className="analysis-chip">
          Ринок: {Number(market.deviation_percent ?? 0) < 0 ? "нижче" : "вище"} на {Math.abs(Number(market.deviation_percent ?? 0)).toFixed(0)}%
        </span>
      )}
      {risk.status === "ready" && (
        <span className={`analysis-chip analysis-chip--risk-${risk.level ?? "unknown"}`}>
          {riskIcon(risk.level)} {riskLabel(risk.level)} · {String(risk.score ?? 0)}/100
        </span>
      )}
    </div>
  );
}

function PriceChart({ history }: { history: PriceHistoryResponse }) {
  const points = useMemo(() => {
    const chronological = [...history.events].reverse();
    const values = chronological.length > 0
      ? [chronological[0].previous_price_uah, ...chronological.map((event) => event.new_price_uah)]
      : [history.current_price_uah];
    const minimum = Math.min(...values);
    const maximum = Math.max(...values);
    const spread = Math.max(maximum - minimum, 1);
    return values.map((value, index) => ({
      value,
      x: values.length === 1 ? 50 : (index / (values.length - 1)) * 100,
      y: 90 - ((value - minimum) / spread) * 75
    }));
  }, [history]);
  const line = points.map((point) => `${point.x},${point.y}`).join(" ");
  return (
    <div className="analysis-chart">
      <svg viewBox="0 0 100 100" role="img" aria-labelledby="price-chart-title price-chart-description">
        <title id="price-chart-title">Історія ціни квартири</title>
        <desc id="price-chart-description">Графік показує послідовність зафіксованих нормалізованих цін.</desc>
        <polyline points={line} fill="none" vectorEffect="non-scaling-stroke" />
        {points.map((point, index) => <circle key={`${String(point.value)}-${String(index)}`} cx={point.x} cy={point.y} r="2.4" />)}
      </svg>
      <ol className="analysis-chart__alternative" aria-label="Текстова історія ціни">
        {history.events.length === 0 && <li>Зміни ціни ще не зафіксовані. Поточна ціна: {formatPrice(history.current_price_uah)}.</li>}
        {[...history.events].reverse().map((event) => (
          <li key={event.id}>
            {new Date(event.changed_at).toLocaleDateString("uk-UA")}: {formatPrice(event.previous_price_uah)} → {formatPrice(event.new_price_uah)} ({Number(event.change_percent) > 0 ? "+" : ""}{Number(event.change_percent).toFixed(1)}%).
          </li>
        ))}
      </ol>
    </div>
  );
}

export function ListingAnalysisPanel({ listingId, summary }: { listingId: string; summary?: AnalysisSummary }) {
  const [market, setMarket] = useState<MarketAnalysisResponse | null>(null);
  const [risk, setRisk] = useState<RiskAnalysisResponse | null>(null);
  const [history, setHistory] = useState<PriceHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setMessage("");
    try {
      const [marketResponse, riskResponse, historyResponse] = await Promise.all([
        fetchMarketAnalysis(listingId, signal),
        fetchRiskAnalysis(listingId, signal),
        fetchPriceHistory(listingId, signal)
      ]);
      setMarket(marketResponse);
      setRisk(riskResponse);
      setHistory(historyResponse);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        setMessage(error instanceof ApiError ? error.message : "Не вдалося завантажити аналітику квартири.");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [listingId]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => { controller.abort(); };
  }, [load]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setMessage("");
    try {
      await refreshListingAnalysis(listingId, `manual-${listingId}-${String(Date.now())}`);
      await load();
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Не вдалося оновити аналітику.");
    } finally {
      setRefreshing(false);
    }
  }, [listingId, load]);

  const marketAssessment = market?.assessment;
  const riskAssessment = risk?.assessment;
  return (
    <section className="listing-analysis" aria-labelledby={`analysis-title-${listingId}`}>
      <header className="listing-analysis__header">
        <div>
          <span>STAGE 09 · АНАЛІТИКА</span>
          <h3 id={`analysis-title-${listingId}`}>Аналітика квартири</h3>
        </div>
        <button type="button" onClick={() => { void refresh(); }} disabled={loading || refreshing}>
          {refreshing ? "Оновлюю…" : "Оновити"}
        </button>
      </header>
      <AnalysisChips summary={summary} />
      {loading && <div className="listing-analysis__state" role="status">Розраховую ринкову оцінку й Risk Score…</div>}
      {!loading && message && <div className="listing-analysis__state listing-analysis__state--error" role="alert">{message}</div>}
      {!loading && !message && marketAssessment && riskAssessment && history && (
        <>
          <div className="listing-analysis__grid">
            <article>
              <small>Ринкова оцінка · {statusLabel(marketAssessment.is_stale ? "stale" : marketAssessment.status)}</small>
              {marketAssessment.status === "ready" && !marketAssessment.is_stale ? (
                <>
                  <strong>{formatPrice(marketAssessment.q1_price_uah)}–{formatPrice(marketAssessment.q3_price_uah)}</strong>
                  <p>Медіана: {formatPrice(marketAssessment.median_price_uah)} · аналогів: {String(marketAssessment.comparable_count)}</p>
                  <p>Відхилення: {marketAssessment.deviation_percent === null ? "—" : `${Number(marketAssessment.deviation_percent) > 0 ? "+" : ""}${Number(marketAssessment.deviation_percent).toFixed(1)}%`} · впевненість: {marketAssessment.confidence_label}</p>
                </>
              ) : <p>{marketAssessment.explanation || statusLabel(marketAssessment.status)}</p>}
            </article>
            <article className={`listing-analysis__risk listing-analysis__risk--${riskAssessment.level}`}>
              <small>{riskIcon(riskAssessment.level)} Risk Score · {statusLabel(riskAssessment.is_stale ? "stale" : riskAssessment.status)}</small>
              <strong>{riskAssessment.status === "ready" ? `${String(riskAssessment.score)}/100` : "—"}</strong>
              <p>{riskAssessment.summary}</p>
            </article>
          </div>
          <PriceChart history={history} />
          {riskAssessment.signals.length > 0 && (
            <div className="listing-analysis__signals">
              <h4>Що варто перевірити</h4>
              <ul>{riskAssessment.signals.map((signal) => <li key={signal.code}><strong>{signal.label}</strong><span>{signal.recommendation}</span></li>)}</ul>
            </div>
          )}
          <p className="listing-analysis__advice">{riskAssessment.safety_advice}</p>
          <p className="listing-analysis__disclaimer">{risk?.disclaimer ?? "Допоміжна оцінка, не юридичний висновок."}</p>
        </>
      )}
    </section>
  );
}
