// Navbar.jsx — Barre de navigation avec logo, nom app et nom magasin
import { ScanLine } from "lucide-react";
import { THEME } from "../config/theme";

export function Navbar() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b"
      style={{ borderColor: "var(--color-border)", backgroundColor: "rgba(255,255,255,0.6)", backdropFilter: "blur(16px)" }}>
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4 sm:px-6">

        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl"
            style={{ background: "linear-gradient(135deg, #E63946, #c62435)", boxShadow: "0 0 16px rgba(230,57,70,0.4)" }}>
            <ScanLine className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="font-display text-sm font-extrabold tracking-tight" style={{ color: "var(--color-text)" }}>
              {THEME.nom_app}
            </p>
            <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--color-text-muted)" }}>
              {THEME.nom_magasin}
            </p>
          </div>
        </div>

        {/* Status badge */}
        <div className="hidden sm:flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold"
          style={{ backgroundColor: "rgba(42,157,143,0.12)", border: "1px solid rgba(42,157,143,0.25)", color: "#2A9D8F" }}>
          <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
          Système en ligne
        </div>

        {/* Nav */}
        <nav className="hidden items-center gap-1 sm:flex">
          <a href="#scanner"
            className="rounded-lg px-4 py-2 text-sm font-bold transition-all"
            style={{ color: "var(--color-primary)", backgroundColor: "rgba(230,57,70,0.08)" }}>
            Scanner
          </a>
          <a href="#history"
            className="rounded-lg px-4 py-2 text-sm font-semibold transition-all hover:opacity-80"
            style={{ color: "var(--color-text-muted)" }}>
            Historique
          </a>
        </nav>
      </div>
    </header>
  );
}
