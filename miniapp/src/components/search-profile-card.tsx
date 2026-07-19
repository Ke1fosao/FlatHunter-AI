import type { SearchProfileSummary } from "@/lib/api";

export function SearchProfileCard({ profile }: { profile: SearchProfileSummary }) {
  return (
    <article className="search-profile-card">
      <div className="search-profile-card__icon" aria-hidden="true">
        ⌕
      </div>
      <div className="search-profile-card__body">
        <span>{profile.city}</span>
        <h3>{profile.name}</h3>
        <small>{profile.is_active ? "Активний пошук" : "Пошук призупинено"}</small>
      </div>
      <span
        className={
          profile.is_active
            ? "search-profile-card__status is-active"
            : "search-profile-card__status"
        }
      >
        {profile.is_active ? "Працює" : "Пауза"}
      </span>
    </article>
  );
}
