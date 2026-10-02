import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "CloseCall",
  description: "A flight recorder for intersections: finds and triages possible near-misses in traffic-camera video for an engineer to review.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <head>
        {/* eslint-disable-next-line @next/next/no-sync-scripts -- must run before first paint to avoid a theme flash */}
        <script src="/theme-boot.js" />
      </head>
      <body>
        <Nav />
        <main>{children}</main>
        <footer><div className="wrap">CloseCall · @SidraMiconi · footage: CC BY-SA 4.0, Wikimedia Commons (see <a href="/ledger#sources">sources</a>)</div></footer>
      </body>
    </html>
  );
}
