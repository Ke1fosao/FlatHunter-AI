import { MiniAppShell } from "@/components/miniapp-shell";

export default function MiniAppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return <MiniAppShell>{children}</MiniAppShell>;
}
