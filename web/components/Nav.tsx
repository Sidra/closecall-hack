"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSyncExternalStore } from "react";

const subscribe = (cb: () => void) => {
  const o = new MutationObserver(cb);
  o.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => o.disconnect();
};
const getTheme = () => document.documentElement.dataset.theme || "dark";

const LINKS = [
  { href: "/demo", label: "Demo" },
  { href: "/ledger", label: "Ledger" },
  { href: "/evals", label: "Evals" },
];

export function Nav() {
  const path = usePathname();
  const theme = useSyncExternalStore(subscribe, getTheme, () => "dark");
  const flip = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("cc-theme", next); } catch {}
  };
  return (
    <nav className="nav">
      <div className="wrap">
        <Link href="/" className="brand"><span className="brand-mark"><i /></span><span>CloseCall</span></Link>
        <div className="nav-links">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} aria-current={path === l.href ? "page" : undefined}>{l.label}</Link>
          ))}
        </div>
        <button className="theme-btn" onClick={flip} aria-label="Toggle colour theme">{theme === "dark" ? "☀ light" : "☾ dark"}</button>
      </div>
    </nav>
  );
}
