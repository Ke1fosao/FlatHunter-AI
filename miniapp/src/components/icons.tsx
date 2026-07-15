type IconProps = { className?: string };

const defaults = { width: 20, height: 20, viewBox: "0 0 24 24", fill: "none" } as const;

export function HomeIcon({ className }: IconProps) {
  return <svg {...defaults} className={className} aria-hidden="true"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1V10Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/></svg>;
}

export function SearchIcon({ className }: IconProps) {
  return <svg {...defaults} className={className} aria-hidden="true"><circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8"/><path d="m20 20-4-4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>;
}

export function MapIcon({ className }: IconProps) {
  return <svg {...defaults} className={className} aria-hidden="true"><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/><path d="M9 3v15M15 6v15" stroke="currentColor" strokeWidth="1.8"/></svg>;
}

export function HeartIcon({ className }: IconProps) {
  return <svg {...defaults} className={className} aria-hidden="true"><path d="M20.8 4.7a5.5 5.5 0 0 0-7.8 0L12 5.8l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.4 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/></svg>;
}

export function CompareIcon({ className }: IconProps) {
  return <svg {...defaults} className={className} aria-hidden="true"><path d="M8 4H4v16h4M16 4h4v16h-4M10 8h4M10 12h4M10 16h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}

export function UserIcon({ className }: IconProps) {
  return <svg {...defaults} className={className} aria-hidden="true"><circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.8"/><path d="M4 21a8 8 0 0 1 16 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>;
}

export function ArrowIcon({ className }: IconProps) {
  return <svg {...defaults} className={className} aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}

export function SparkleIcon({ className }: IconProps) {
  return <svg {...defaults} className={className} aria-hidden="true"><path d="M12 2c.6 5.3 4.1 8.8 9 10-4.9 1.2-8.4 4.7-9 10-.6-5.3-4.1-8.8-9-10 4.9-1.2 8.4-4.7 9-10Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/></svg>;
}

export function CheckIcon({ className }: IconProps) {
  return <svg {...defaults} className={className} aria-hidden="true"><path d="m5 12 4 4L19 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
