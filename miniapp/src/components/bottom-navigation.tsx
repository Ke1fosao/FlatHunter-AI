"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  CompareIcon,
  HeartIcon,
  MapIcon,
  SearchIcon,
  UserIcon,
} from "@/components/icons";
import { triggerSelectionFeedback } from "@/lib/telegram";

const items = [
  { href: "/search", label: "Пошук", icon: SearchIcon },
  { href: "/map", label: "Карта", icon: MapIcon },
  { href: "/favorites", label: "Обране", icon: HeartIcon },
  { href: "/compare", label: "Порівняння", icon: CompareIcon },
  { href: "/profile", label: "Профіль", icon: UserIcon },
] as const;

function activeHref(pathname: string): string {
  if (pathname.startsWith("/listings/")) {
    return "/search";
  }
  return items.find((item) => pathname.startsWith(item.href))?.href ?? "/search";
}

export function BottomNavigation() {
  const pathname = usePathname();
  const current = activeHref(pathname);

  return (
    <div className="miniapp-bottom-navigation-layer">
      <nav className="miniapp-bottom-navigation" aria-label="Основна навігація">
        {items.map(({ href, label, icon: Icon }) => {
          const active = current === href;
          return (
            <Link
              key={href}
              href={href}
              className={active ? "is-active" : undefined}
              aria-current={active ? "page" : undefined}
              onClick={triggerSelectionFeedback}
            >
              <Icon />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
