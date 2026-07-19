import type { ReactNode } from "react";

type PageStateKind = "loading" | "empty" | "error" | "offline";

type PageStateProps = {
  kind: PageStateKind;
  title: string;
  description?: string;
  action?: ReactNode;
};

const icons: Record<PageStateKind, string> = {
  loading: "…",
  empty: "⌂",
  error: "!",
  offline: "↯",
};

export function PageState({
  kind,
  title,
  description,
  action,
}: PageStateProps) {
  return (
    <section className={`page-state page-state--${kind}`} role="status">
      <span className="page-state__icon" aria-hidden="true">
        {icons[kind]}
      </span>
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {action && <div className="page-state__action">{action}</div>}
    </section>
  );
}
