import type { ClusterMember, ListingClusterDetail } from "@/lib/cluster-api";
import { formatClusterPriceRange, sourceLabel } from "@/lib/cluster-api";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function confidenceText(member: ClusterMember): string {
  if (member.role === "primary") return "Основне оголошення";
  const score = Math.round(Number(member.confidence));
  if (member.joined_by === "manual") return `Підтверджено вручну · ${String(score)}%`;
  if (member.joined_by === "exact") return `Точний збіг · ${String(score)}%`;
  return `Ймовірний дублікат · ${String(score)}%`;
}

export function ClusterSources({ cluster }: { cluster: ListingClusterDetail }) {
  const minimum = cluster.price_min_uah ?? cluster.primary.price_uah;
  const maximum = cluster.price_max_uah ?? cluster.primary.price_uah;
  return (
    <section className="cluster-sources" aria-labelledby="cluster-sources-title">
      <header>
        <div>
          <span>ОДНА КВАРТИРА · КІЛЬКА ПУБЛІКАЦІЙ</span>
          <h3 id="cluster-sources-title">Джерела оголошення</h3>
          <p>
            FlatHunter об’єднав {sourceLabel(cluster.member_count)}. Перевірте ціну, свіжість і умови кожної публікації.
          </p>
        </div>
        <strong>{formatClusterPriceRange(minimum, maximum)}</strong>
      </header>
      <div className="cluster-sources__list">
        {cluster.members.map((member) => (
          <article key={member.listing.id} className={member.role === "primary" ? "is-primary" : ""}>
            <div className="cluster-sources__source">
              <span>{member.listing.source_name}</span>
              {member.role === "primary" && <b>Основне</b>}
            </div>
            <strong>{formatClusterPriceRange(member.listing.price_uah, member.listing.price_uah)}</strong>
            <small>Опубліковано {formatDate(member.listing.published_at)}</small>
            <small>{confidenceText(member)}</small>
            {member.reasons[0] && <p>{member.reasons[0]}</p>}
            <a href={member.listing.source_url} target="_blank" rel="noreferrer">
              Відкрити це джерело ↗
            </a>
          </article>
        ))}
      </div>
      <style jsx>{`
        .cluster-sources{display:grid;gap:14px;margin-top:22px;padding-top:20px;border-top:1px solid var(--line)}
        header{display:flex;justify-content:space-between;align-items:start;gap:18px} header span{font-size:10px;font-weight:900;letter-spacing:.12em;color:var(--accent)}
        h3{margin:5px 0} p{margin:0;color:var(--muted);line-height:1.55} header>strong{white-space:nowrap;font-size:18px}
        .cluster-sources__list{display:grid;gap:9px} article{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:7px 14px;padding:14px;border:1px solid var(--line);border-radius:16px;background:var(--bg)} article.is-primary{border-color:color-mix(in srgb,var(--accent) 58%,var(--line));background:color-mix(in srgb,var(--accent) 8%,var(--bg))}
        .cluster-sources__source{display:flex;align-items:center;gap:7px;font-weight:900}.cluster-sources__source b{padding:3px 6px;border-radius:7px;background:var(--accent);color:var(--accent-text);font-size:9px;text-transform:uppercase}
        small{color:var(--muted)} article p{grid-column:1/-1;font-size:12px} a{grid-column:1/-1;color:var(--accent);font-weight:900;text-decoration:none}
        @media(max-width:520px){header{flex-direction:column}article{grid-template-columns:1fr}header>strong{font-size:16px}}
      `}</style>
    </section>
  );
}
