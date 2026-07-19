import type { Metadata, Viewport } from "next";
import Script from "next/script";

import uk from "@/locales/uk.json";

import "leaflet/dist/leaflet.css";
import "./globals.css";
import "./stage-six.css";
import "./miniapp-shell.css";
import "./routed-pages.css";
import "./search-wizard.css";

export const metadata: Metadata = {
  title: uk.meta.title,
  description: uk.meta.description,
  applicationName: "FlatHunter AI",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f5f6f2" },
    { media: "(prefers-color-scheme: dark)", color: "#101411" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="uk">
      <body>
        {children}
        <Script
          src="https://telegram.org/js/telegram-web-app.js"
          strategy="beforeInteractive"
        />
      </body>
    </html>
  );
}
