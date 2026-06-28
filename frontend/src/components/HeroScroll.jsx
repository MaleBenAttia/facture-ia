import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * HeroScroll — Cinematic auto-slideshow hero
 *
 * Plus de scroll-scrubbing contraignant.
 * Les images défilent automatiquement toutes les 3.5s.
 * Le CTA "Scanner une facture" est visible immédiatement.
 * L'utilisateur peut accéder au scanner en 1 clic sans attendre.
 */

const SLIDES = [
  {
    src:      "/assets/images/manager-face.png",
    alt:      "Expert automobile",
    eyebrow:  "Intelligence Artificielle",
    title:    "Vos factures,\nanalysées en secondes",
    sub:      "Importez une image ou un PDF — l'IA extrait tout automatiquement.",
    position: "50% 20%",
  },
  {
    src:      "/assets/images/manager-3quarter.png",
    alt:      "Manager terrain",
    eyebrow:  "Précision 97%",
    title:    "Zéro saisie\nmanuelle",
    sub:      "Références, quantités, montants — structurés en un instant.",
    position: "40% 25%",
  },
  {
    src:      "/assets/images/manager-wide.png",
    alt:      "Vision globale",
    eyebrow:  "Export Excel & PDF",
    title:    "Prêt à\nexporter",
    sub:      "Téléchargez vos données formatées directement après l'analyse.",
    position: "50% 35%",
  },
];

const INTERVAL = 3500; // ms entre chaque slide

export function HeroScroll() {
  const [current, setCurrent] = useState(0);
  /* ─ Auto-avance permanente ─ */
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrent((c) => (c + 1) % SLIDES.length);
    }, INTERVAL);
    return () => clearInterval(timer);
  }, []);

  const slide = SLIDES[current];

  return (
    <section className="relative h-screen overflow-hidden bg-black">
      {/* ── Images en crossfade automatique ── */}
      <AnimatePresence mode="sync">
        <motion.div
          key={slide.src}
          className="absolute inset-0"
          initial={{ opacity: 0, scale: 1.04 }}
          animate={{ opacity: 1,  scale: 1.0  }}
          exit={{    opacity: 0,  scale: 0.98 }}
          transition={{ duration: 1.1, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <img
            src={slide.src}
            alt={slide.alt}
            className="h-full w-full object-cover"
            style={{ objectPosition: slide.position }}
            draggable={false}
          />

          {/* Dégradé cinématique */}
          <div
            className="absolute inset-0"
            style={{
              background:
                "linear-gradient(to top,  rgba(0,0,0,0.80) 0%, rgba(0,0,0,0.30) 50%, rgba(0,0,0,0.10) 100%)," +
                "linear-gradient(to right, rgba(0,0,0,0.50) 0%, transparent 55%)",
            }}
          />
        </motion.div>
      </AnimatePresence>

      {/* ── Grain film premium ── */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.035] mix-blend-overlay"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
          backgroundSize: "140px 140px",
        }}
        aria-hidden
      />

      {/* ── Texte — animate à chaque changement de slide ── */}
      <div className="absolute inset-x-0 bottom-0 px-8 sm:px-16 pb-10">
        <AnimatePresence mode="wait">
          <motion.div
            key={slide.eyebrow}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0  }}
            exit={{    opacity: 0, y: -10 }}
            transition={{ duration: 0.55, ease: "easeOut" }}
          >
            {/* Eyebrow */}
            <p className="mb-3 flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-[0.25em] text-white/55">
              <span className="h-px w-8 bg-white/35" />
              {slide.eyebrow}
            </p>

            {/* Titre */}
            <h1 className="whitespace-pre-line text-4xl sm:text-6xl lg:text-7xl font-black leading-none tracking-tight text-white drop-shadow-2xl max-w-2xl">
              {slide.title}
            </h1>

            {/* Sous-titre */}
            <p className="mt-4 max-w-md text-sm sm:text-base font-medium text-white/65 leading-relaxed">
              {slide.sub}
            </p>
          </motion.div>
        </AnimatePresence>

        {/* ── CTA principal — TOUJOURS visible ── */}
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <a
            href="#scanner"
            className="inline-flex items-center gap-2 rounded-2xl px-7 py-3.5 text-sm font-extrabold text-white shadow-lg transition-all hover:opacity-90 hover:-translate-y-0.5 active:translate-y-0"
            style={{ background: "linear-gradient(135deg, #E63946 0%, #c62435 100%)" }}
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
            Scanner une facture
          </a>

          <a
            href="#scanner"
            className="inline-flex items-center gap-1.5 rounded-2xl border border-white/25 bg-white/10 px-5 py-3.5 text-sm font-bold text-white backdrop-blur-sm hover:bg-white/20 transition-all"
          >
            Voir la démo
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </a>
        </div>

        {/* ── Dots de navigation ── */}
        <div className="mt-6 flex items-center gap-2">
          {SLIDES.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrent(i)}
              aria-label={`Slide ${i + 1}`}
              className="relative h-0.5 overflow-hidden rounded-full transition-all duration-300"
              style={{ width: i === current ? "2rem" : "0.75rem", backgroundColor: "rgba(255,255,255,0.3)" }}
            >
              {i === current && (
                <motion.span
                  className="absolute inset-y-0 left-0 rounded-full bg-white"
                  initial={{ width: "0%" }}
                  animate={{ width: "100%" }}
                  transition={{ duration: INTERVAL / 1000, ease: "linear" }}
                  key={current}
                />
              )}
            </button>
          ))}

          {/* Compteur discret */}
          <span className="ml-2 text-[11px] font-bold text-white/35 tabular-nums">
            {String(current + 1).padStart(2, "0")} / {String(SLIDES.length).padStart(2, "0")}
          </span>
        </div>
      </div>

      {/* ── Barre rouge en haut ── */}
      <div
        className="absolute top-0 left-0 right-0 h-[2px]"
        style={{ background: "linear-gradient(90deg, #E63946, #ff6b35)" }}
      />
    </section>
  );
}
