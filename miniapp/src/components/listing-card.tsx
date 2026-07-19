import Link from "next/link";

import { AnalysisChips } from "@/components/listing-analysis-panel";
import type { AnalysisSummary } from "@/lib/analysis-api";
import type { ListingFeedItem, PersonalizedMatch } from "@/lib/api";
import type { ListingStateAction } from "@/hooks/use-listing-state";

type AnalyzedListing = ListingFeedItem & {
  analysis_summary?: AnalysisSummary;
};

type ListingCardProps = {
  listing: ListingFeedItem;
  match?: PersonalizedMatch["match"];
  pending?: boolean;
  showHide?: boolean;
  onState?: (
    listing: ListingFeedItem,
    action: ListingStateAction,
    value: boolean,
  ) => void;
};

function formatPrice(value: number): string {
  return `${new Intl.NumberFormat("uk-UA").format(value)} грн`;
}

function analysisSummary(listing: ListingFeedItem): AnalysisSummary | undefined {
  return (listing as AnalyzedListing).analysis_summary;
}

export function ListingCard({
  listing,
  match,
  pending = false,
  showHide = true,
  onState,
}: ListingCardProps) {
  const image = listing.images[0];

  return (
    <article className="routed-listing-card">
      <Link
        href={`/listings/${listing.id}`}
        className="routed-listing-card__main"
        aria-label={`Відкрити ${listing.title}`}
      >
        <div
          className="routed-listing-card__visual"
          style={image ? { backgroundImage: `url(${image})` } : undefined}
        >
          {!image && <strong>{listing.rooms}к</strong>}
          {match && (
            <span className="routed-listing-card__match">{match.score}%</span>
          )}
          {listing.is_demo && (
            <span className="routed-listing-card__demo">DEMO</span>
          )}
        </div>
        <div className="routed-listing-card__body">
          <small>
            {listing.city} · {listing.district || "район не вказано"}
          </small>
          <h3>{listing.title}</h3>
          <strong className="routed-listing-card__price">
            {formatPrice(listing.price_uah)}
          </strong>
          <p>
            {listing.rooms} кімн. · {listing.total_area ?? "площа не вказана"}
            {listing.total_area ? " м²" : ""}
          </p>
          <AnalysisChips summary={analysisSummary(listing)} />
          {match?.summary && (
            <p className="routed-listing-card__summary">{match.summary}</p>
          )}
        </div>
      </Link>

      {onState && (
        <div className="routed-listing-card__actions">
          <button
            type="button"
            disabled={pending}
            className={listing.user_state.is_favorite ? "is-active" : undefined}
            onClick={() => {
              onState(
                listing,
                "favorite",
                !listing.user_state.is_favorite,
              );
            }}
          >
            {listing.user_state.is_favorite ? "★ Обране" : "☆ В обране"}
          </button>
          <button
            type="button"
            disabled={pending}
            className={listing.user_state.is_compared ? "is-active" : undefined}
            onClick={() => {
              onState(
                listing,
                "compare",
                !listing.user_state.is_compared,
              );
            }}
          >
            {listing.user_state.is_compared ? "✓ Додано" : "⇄ Порівняти"}
          </button>
          {showHide && (
            <button
              type="button"
              disabled={pending}
              onClick={() => {
                onState(listing, "hide", true);
              }}
            >
              Сховати
            </button>
          )}
        </div>
      )}
    </article>
  );
}
