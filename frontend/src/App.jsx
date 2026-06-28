import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { Navbar } from "./components/Navbar";
import { HeroScroll } from "./components/HeroScroll";
import { ScanZone } from "./components/ScanZone";
import { InvoicePreview } from "./components/InvoicePreview";
import { InvoiceHistory } from "./components/InvoiceHistory";
import { ToastProvider, useToast } from "./components/ui/Toast";
import { FloatingIconsBackground } from "./components/FloatingIconsBackground";
import { traiterFacture, urlExcel, urlPdf, telecharger, ApiError } from "./lib/api";

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

  const [etat,          setEtat]          = useState("attente");
  const [progression,   setProgression]   = useState(0);
  const [fichierActuel, setFichierActuel] = useState(null);
  const [resultat,      setResultat]      = useState(null);
  const [telechargement,setTelechargement]= useState(null);
  const [historique,    setHistorique]    = useState([]);
  const [selectionneeId,setSelectionneeId]= useState(null);

  const handleFichierSelect = useCallback((file) => {
    setFichierActuel(file);
    setEtat("preview");
    setResultat(null);
    setProgression(0);
  }, []);

  const lancerTraitement = useCallback(async () => {
    if (!fichierActuel) return;
    setEtat("traitement");
    setProgression(3); // démarre visible, pas à zéro

    // Progression simulée : ease-out sur ~6s jusqu'à 94%, puis attend la réponse
    const DUREE_MS  = 6000; // durée estimée du traitement IA
    const STEP_MS   = 120;  // mise à jour toutes les 120ms pour un rendu fluide
    let elapsed     = 0;
    const interval  = setInterval(() => {
      elapsed += STEP_MS;
      const ratio = Math.min(elapsed / DUREE_MS, 1);
      const eased = 1 - Math.pow(1 - ratio, 2.5); // ease-out cubique — rapide au début, ralentit vers 94%
      setProgression(Math.round(3 + eased * 91)); // plage : 3% → 94%
    }, STEP_MS);

    try {
      const reponse = await traiterFacture(fichierActuel);
      clearInterval(interval);
      setProgression(100);
      setEtat("succes");
      setResultat(reponse);
      const entree = { id: crypto.randomUUID(), fichier: fichierActuel, ...reponse };
      setHistorique((h) => [entree, ...h]);
      setSelectionneeId(entree.id);
      toast({ variant: "success", title: "Facture analysée", description: "Données extraites avec succès." });
    } catch (err) {
      clearInterval(interval);
      setEtat("erreur");
      const message = err instanceof ApiError ? err.message : "Connexion au serveur impossible.";
      toast({ variant: "error", title: "Extraction impossible", description: message });

    }
  }, [fichierActuel, toast]);

  const annulerTraitement = useCallback(() => {
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

      {/* 3. Hero cinématique */}
      <HeroScroll />

      {/* 4. Contenu principal */}
      <div className="relative" style={{ zIndex: 10 }}>
        <main>
          <div className="mx-auto max-w-3xl px-4 sm:px-6 pb-28 pt-10">

            {/* Zone de scan */}
            <motion.section
              id="scanner"
              className="scroll-mt-20"
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
                className="mt-8 scroll-mt-20"
                variants={fadeUp}
                initial="hidden"
                animate="visible"
              >
                <DarkCard>
                  <SectionHead label="Résultat de l'extraction" color="#2A9D8F" />
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
              className="mt-8 scroll-mt-20"
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
