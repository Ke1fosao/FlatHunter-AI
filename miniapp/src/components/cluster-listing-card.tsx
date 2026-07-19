import type { Route } from "next";
import Link from "next/link";

import { AnalysisChips } from "@/components/listing-analysis-panel";
import type { AnalysisSummary } from "@/lib/analysis-api";
import {
  formatClusterPriceRange,
  sourceLabel,
  type ClusterFeedItem,
  type ClusterListing,
} from "@/lib/cluster-api";

type ClusterBooleanField = "is_favorite" | "is_hidden" | "is_compared";
type AnalyzedClusterListing = ClusterListing & {
  analysis_summary?: AnalysisSummary;
};

type Props = {
  item: ClusterFeedItem;
  profileId?: string;
  pending?: boolean;
  showHide?: boolean;
  onState: (field: ClusterBooleanField, value: boolean) => void;
};

function analysisSummary(listing: ClusterListing): AnalysisSummary | undefined {
  return (listing as AnalyzedClusterListing).analysis_summary;
}

function detailHref(listing: ClusterListing, profileId?: string): Route {
  const params = new URLSearchParams();
  if (profileId) {
    params.set("profile", profileId);
  }
  if (listing.cluster_id) {
    params.set("cluster", listing.cluster_id);
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  return `/listings/${listing.id}${query}` as Route;
}

export function ClusterListingCard({
  item,
  profileId,
  pending = false,
  showHide = true,
  onState,
}: Props) {
  const { listing, match } = item;
  const image = listing.images.at(0);

  return (
    <article className="cluster-route-card">
      <Link
        href={detailHref(listing, profileId)}
        className="cluster-route-card__main"
        aria-label={`Відкрити ${listing.title}`}
      >
        <div
          className="cluster-route-card__visual"
          style={image ? { backgroundImage: `url(${image})` } : undefined}
        >
          {!image && <strong>{listing.rooms}к</strong>}
          {match && (
            <span className="cluster-route-card__match">
              {match.score}% Match
            </span>
          )}
          {listing.member_count > 1 && (
            <span className="cluster-route-card__sources">
              {sourceLabel(listing.source_count || listing.member_count)}
            </span>
          )}
        </div>
        <div className="cluster-route-card__body">
          <small>
            {listing.city} · {listing.district || "район не вказано"}
          </small>
          <h3>{listing.title}</h3>
          <strong>
            {formatClusterPriceRange(
              listing.price_min_uah,
              listing.price_max_uah,
            )}
          </strong>
          <p>
            {listing.rooms} кімн. ·{" "}
            {listing.total_area ? `${listing.total_area} м²` : "площа не вказана"}
          </p>
          <AnalysisChips summary={analysisSummary(listing)} />
          {match?.summary && <p>{match.summary}</p>}
        </div>
      </Link>

      <div className="cluster-route-card__actions">
        <button
          type="button"
          disabled={pending}
          className={listing.user_state.is_favorite ? "is-active" : undefined}
          onClick={() => {
            onState("is_favorite", !listing.user_state.is_favorite);
          }}
        >
          {listing.user_state.is_favorite ? "В обраному" : "В обране"}
        </button>
        <button
          type="button"
          disabled={pending}
          className={listing.user_state.is_compared ? "is-active" : undefined}
          onClick={() => {
            onState("is_compared", !listing.user_state.is_compared);
          }}
        >
          {listing.user_state.is_compared ? "У порівнянні" : "Порівняти"}
        </button>
        {showHide && (
          <button
            type="button"
            disabled={pending}
            onClick={() => {
              onState("is_hidden", true);
            }}
          >
            Сховати
          </button>
        )}
      </div>
    </article>
  );
}
