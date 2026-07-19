"use client";

import { useCallback, useEffect, useState } from "react";

import { ClusterNoteEditor } from "@/components/cluster-note-editor";
import { ClusterSources } from "@/components/cluster-sources";
import { PageState } from "@/components/page-state";
import { ApiError, fetchListing, type ListingFeedItem } from "@/lib/api";
import {
  fetchListingCluster,
  setClusterState,
  type ListingClusterDetail,
} from "@/lib/cluster-api";

type ClusteredListing = ListingFeedItem & { cluster_id?: string | null };

type Props = {
  listingId: string;
  clusterId?: string;
  profileId?: string;
};

export function ClusterDetailExtras({ listingId, clusterId, profileId }: Props) {
  const [resolvedClusterId, setResolvedClusterId] = useState(clusterId ?? "");
  const [cluster, setCluster] = useState<ListingClusterDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      let targetClusterId = clusterId;
      if (!targetClusterId) {
        const listing = (await fetchListing(listingId, signal)) as ClusteredListing;
        targetClusterId = listing.cluster_id ?? undefined;
      }
      setResolvedClusterId(targetClusterId ?? "");
      if (!targetClusterId) {
        setCluster(null);
        return;
      }
      setCluster(await fetchListingCluster(targetClusterId, profileId, signal));
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setError(
          reason instanceof ApiError
            ? reason.message
            : "Не вдалося завантажити джерела квартири.",
        );
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [clusterId, listingId, profileId]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => { controller.abort(); };
  }, [load]);

  const updateBooleanState = async (
    field: "is_favorite" | "is_compared" | "is_hidden",
    value: boolean,
  ) => {
    if (!resolvedClusterId) return;
    setBusy(true);
    setError("");
    try {
      setCluster(await setClusterState(resolvedClusterId, { [field]: value }));
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Не вдалося зберегти дію для квартири.",
      );
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <section className="route-section">
        <PageState kind="loading" title="Завантажую джерела оголошення" />
      </section>
    );
  }

  if (!resolvedClusterId) return null;

  if (!cluster) {
    return (
      <section className="route-section">
        <PageState
          kind="error"
          title="Джерела тимчасово недоступні"
          description={error}
          action={
            <button type="button" onClick={() => void load()}>
              Спробувати ще раз
            </button>
          }
        />
      </section>
    );
  }

  return (
    <section className="route-section cluster-detail-extras">
      <div className="route-section__heading">
        <div>
          <span className="route-kicker">КЛАСТЕР КВАРТИРИ</span>
          <h2>Усі публікації та ваша нотатка</h2>
        </div>
      </div>
      {error && <p className="route-inline-error" role="status">{error}</p>}
      <div className="cluster-detail-extras__actions">
        <button
          type="button"
          disabled={busy}
          className={cluster.user_state.is_favorite ? "is-active" : undefined}
          onClick={() => void updateBooleanState("is_favorite", !cluster.user_state.is_favorite)}
        >
          {cluster.user_state.is_favorite ? "★ В обраному" : "☆ В обране"}
        </button>
        <button
          type="button"
          disabled={busy}
          className={cluster.user_state.is_compared ? "is-active" : undefined}
          onClick={() => void updateBooleanState("is_compared", !cluster.user_state.is_compared)}
        >
          {cluster.user_state.is_compared ? "✓ У порівнянні" : "⇄ Порівняти"}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void updateBooleanState("is_hidden", true)}
        >
          Сховати квартиру
        </button>
      </div>
      <ClusterNoteEditor
        clusterId={cluster.id}
        initialNote={cluster.user_state.note}
        onSaved={(note) =>
          { setCluster((current) =>
            current
              ? { ...current, user_state: { ...current.user_state, note } }
              : current,
          ); }
        }
      />
      <ClusterSources cluster={cluster} />
      <style jsx>{`
        .cluster-detail-extras{display:grid;gap:14px}
        .cluster-detail-extras__actions{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
        .cluster-detail-extras__actions button{min-height:44px;border:1px solid var(--line);border-radius:12px;background:var(--bg);color:var(--muted);font-weight:850;cursor:pointer}
        .cluster-detail-extras__actions button.is-active{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 9%,var(--bg));color:var(--accent)}
        @media(max-width:560px){.cluster-detail-extras__actions{grid-template-columns:1fr}}
      `}</style>
    </section>
  );
}
