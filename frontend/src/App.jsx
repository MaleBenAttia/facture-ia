// App.jsx — Racine : upload → barre de progression → resultat table + telechargements + historique
import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Navbar } from "./components/Navbar";
import { ScanZone } from "./components/ScanZone";
import { InvoicePreview } from "./components/InvoicePreview";
import { InvoiceHistory } from "./components/InvoiceHistory";
import { ToastProvider, useToast } from "./components/ui/Toast";
import { FloatingIconsBackground } from "./components/FloatingIconsBackground";
import { traiterFacture, annulerJob, urlExcel, urlPdf, telecharger, previsualiserFacture, ApiError } from "./lib/api";

/* Animation d'entrée au scroll pour les sections */
const fadeUp = {
  hidden:  { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.25, 0.1, 0.25, 1] } },
};

/* Carte glassmorphism réutilisable */
function DarkCard({ children, className = "" }) {
  return (
    <div className={`glass rounded-2xl p-6 sm:p-8 ${className}`}>
      {children}
    </div>
  );
}

/* En-tête de section */
function SectionHead({ color = "#E63946", label }) {
  return (
    <div className="flex items-center gap-2 mb-6">
      <div className="h-1 w-8 rounded" style={{ backgroundColor: color }} />
      <p className="text-xs font-extrabold uppercase tracking-widest" style={{ color: "var(--color-text-muted)" }}>
        {label}
      </p>
    </div>
  );
}

function AppContenu() {
  const { toast } = useToast();

  const [etat,                setEtat]                = useState("attente");
  const [progression,         setProgression]         = useState(0);
  const [fichierActuel,       setFichierActuel]       = useState(null);
  const [previewProcessedUrl, setPreviewProcessedUrl] = useState(null);
  const [resultat,            setResultat]            = useState(null);
  const [telechargement,      setTelechargement]      = useState(null);
  const [historique,          setHistorique]          = useState([]);
  const [selectionneeId,      setSelectionneeId]      = useState(null);
  const [dureeTraitement,     setDureeTraitement]     = useState(null);
  const [nbPages,             setNbPages]             = useState(1);

  // Nettoie l'URL du preview quand elle change ou au démontage
  useEffect(() => {
    return () => {
      if (previewProcessedUrl) URL.revokeObjectURL(previewProcessedUrl);
    };
  }, [previewProcessedUrl]);

  // Références pour l'annulation du job en cours
  const abortCtrlRef = useRef(null);  // AbortController pour stopper le polling
  const jobIdRef     = useRef(null);  // job_id backend du job en cours
  const runIdRef     = useRef(0);     // identifie le traitement actif

  const handleFichierSelect = useCallback(async (file) => {
    setFichierActuel(file);
    setEtat("preview");
    setResultat(null);
    setProgression(0);
    setPreviewProcessedUrl(null);
    try {
      const blob = await previsualiserFacture(file);
      const url = URL.createObjectURL(blob);
      setPreviewProcessedUrl(url);
    } catch {
      // fallback : on affiche l'aperçu brut si le preprocessing échoue
    }
  }, []);

  const lancerTraitement = useCallback(async () => {
    if (!fichierActuel) return;
    setEtat("traitement");
    setProgression(3);
    setDureeTraitement(null);
    setNbPages(1);
    const debutTimer = Date.now();

    // Crée un AbortController pour pouvoir annuler le fetch/polling
    const ctrl = new AbortController();
    const runId = runIdRef.current + 1;
    runIdRef.current = runId;
    abortCtrlRef.current = ctrl;
    jobIdRef.current     = null; // sera rempli par traiterFacture

    let interval = null;

    const demarrerProgression = (pages) => {
      // ~12.5s par page (4 pages → 50s, 1 page → 25s)
      const dureeEstimeeMs = Math.min(Math.max(pages * 12_500, 20_000), 120_000);
      const STEP_MS = 120;
      if (interval) clearInterval(interval);
      let elapsed = 0;
      interval = setInterval(() => {
        elapsed += STEP_MS;
        const ratio = Math.min(elapsed / dureeEstimeeMs, 1);
        setProgression(Math.round(3 + ratio * 96));
      }, STEP_MS);
    };

    demarrerProgression(1);

    try {
      const reponse = await traiterFacture(
        fichierActuel,
        ctrl.signal,
        (jobId, pages) => {
          if (runIdRef.current === runId && !ctrl.signal.aborted) {
            jobIdRef.current = jobId;
            if (pages && pages > 1) {
              setNbPages(pages);
              demarrerProgression(pages);
            }
          } else {
            annulerJob(jobId);
          }
        }
      );
      clearInterval(interval);
      if (ctrl.signal.aborted || runIdRef.current !== runId) return;
      setProgression(100);
      setDureeTraitement(((Date.now() - debutTimer) / 1000).toFixed(1));
      setEtat("succes");
      setResultat(reponse);
      
      const id = crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2);
      const entree = { id, fichier: fichierActuel, ...reponse };
      setHistorique((h) => [entree, ...h]);
      setSelectionneeId(entree.id);
      toast({ variant: "success", title: "Facture analysée", description: "Données extraites avec succès." });
    } catch (err) {
      if (interval) clearInterval(interval);
      // Si annulé par l'utilisateur → retour silencieux à l'état preview
      const annule = err instanceof ApiError && err.status === 0 && err.message.includes("annulé");
      if (annule) {
        if (runIdRef.current === runId) {
          setEtat("preview");
          setProgression(0);
        }
        return;
      }
      setEtat("erreur");
      const message = err instanceof ApiError
        ? err.message
        : `[${err?.constructor?.name || "Error"}] ${err?.message || "inconnu"}`;
      toast({ variant: "error", title: "Extraction impossible", description: message });
    } finally {
      if (runIdRef.current === runId) {
        abortCtrlRef.current = null;
        jobIdRef.current     = null;
      }
    }
  }, [fichierActuel, toast]);

  const annulerTraitement = useCallback(async () => {
    runIdRef.current += 1;
    // 1. Stoppe le polling frontend immédiatement
    if (abortCtrlRef.current) {
      abortCtrlRef.current.abort();
      abortCtrlRef.current = null;
    }
    // 2. Envoie le signal d'annulation au backend (best-effort)
    if (jobIdRef.current) {
      await annulerJob(jobIdRef.current);
      jobIdRef.current = null;
    }
    setEtat("attente");
    setFichierActuel(null);
    setProgression(0);
  }, []);


  const selectionnerHistorique = useCallback((item) => {
    setResultat(item);
    setFichierActuel(item.fichier);
    setEtat("succes");
    setSelectionneeId(item.id);
    document.getElementById("resultat")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const handleTelechargerExcel = useCallback(async () => {
    if (!resultat?.excel) return;
    setTelechargement("excel");
    try {
      const nom = resultat.excel.split("/").pop();
      await telecharger(urlExcel(nom), nom);
      toast({ variant: "success", title: "Excel téléchargé" });
    } catch {
      toast({ variant: "error", title: "Téléchargement impossible" });
    } finally {
      setTelechargement(null);
    }
  }, [resultat, toast]);

  const handleTelechargerPdf = useCallback(async () => {
    if (!resultat?.pdf) return;
    setTelechargement("pdf");
    try {
      const nom = resultat.pdf.split("/").pop();
      await telecharger(urlPdf(resultat.pdf), nom);
      toast({ variant: "success", title: "PDF téléchargé" });
    } catch {
      toast({ variant: "error", title: "Téléchargement impossible" });
    } finally {
      setTelechargement(null);
    }
  }, [resultat, toast]);

  return (
    <div className="min-h-screen" style={{ backgroundColor: "var(--color-bg)" }}>

      {/* 1. Fond avec icônes flottantes (pièces auto) */}
      <FloatingIconsBackground />

      {/* 2. Navbar fixe */}
      <Navbar />

      {/* 4. Contenu principal */}
      <div className="relative" style={{ zIndex: 10 }}>
        <main>
          <div className="mx-auto max-w-4xl px-4 sm:px-6 pb-32 pt-28">

            {/* Bandeau discret en haut */}
            <div className="mb-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h1 className="text-3xl font-black tracking-tight drop-shadow-sm" style={{ color: "var(--color-primary)" }}>
                  Scanner vos factures
                </h1>
                <p className="mt-1 text-sm font-medium text-slate-500">
                  Importez une image ou un PDF pour extraire les données.
                </p>
              </div>
              <div className="inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-white/50 px-3 py-1.5 text-[11px] font-bold tracking-widest text-[var(--color-primary)] uppercase shadow-sm">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--color-primary)] opacity-75"></span>
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--color-primary)]"></span>
                </span>
                Système en ligne
              </div>
            </div>

            {/* Zone de scan */}
            <motion.section
              id="scanner"
              className="scroll-mt-32"
              variants={fadeUp}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.15 }}
            >
              <DarkCard>
                <SectionHead label="Zone de scan" />
                <ScanZone
                  etat={etat}
                  progression={progression}
                  fichierActuel={fichierActuel}
                  previewProcessedUrl={previewProcessedUrl}
                  dureeTraitement={dureeTraitement}
                  nbPages={nbPages}
                  onFileReady={handleFichierSelect}
                  onScanConfirm={lancerTraitement}
                  onAnnuler={annulerTraitement}
                />
              </DarkCard>
            </motion.section>

            {/* Résultats */}
            {etat === "succes" && resultat && (
              <motion.section
                id="resultat"
                className="mt-12 scroll-mt-32"
                variants={fadeUp}
                initial="hidden"
                animate="visible"
              >
                <DarkCard>
                  <div className="flex items-center justify-between mb-6">
                    <SectionHead label="Résultat de l'extraction" color="#2A9D8F" />
                    {dureeTraitement && (
                      <span className="text-xs font-bold px-3 py-1 rounded-full" style={{ backgroundColor: "rgba(42,157,143,0.1)", color: "#2A9D8F" }}>
                        ⏱ {dureeTraitement}s
                      </span>
                    )}
                  </div>
                  <InvoicePreview
                    resultat={resultat}
                    telechargement={telechargement}
                    onTelechargerExcel={handleTelechargerExcel}
                    onTelechargerPdf={handleTelechargerPdf}
                  />
                </DarkCard>
              </motion.section>
            )}

            {/* Historique */}
            <motion.section
              id="history"
              className="mt-12 scroll-mt-32"
              variants={fadeUp}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.1 }}
            >
              <InvoiceHistory
                historique={historique}
                onSelectionner={selectionnerHistorique}
                selectionneeId={selectionneeId}
              />
            </motion.section>

          </div>
        </main>

        {/* Footer */}
        <footer className="border-t py-5 text-center text-xs font-medium"
          style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}>
          Scanner‑Pro · Intelligence Artificielle pour l'Automobile · {new Date().getFullYear()}
        </footer>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AppContenu />
    </ToastProvider>
  );
}
