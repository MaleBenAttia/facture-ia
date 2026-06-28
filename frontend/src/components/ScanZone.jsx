import { useCallback, useState, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { ScanLine, FileImage, FileText, UploadCloud, X } from "lucide-react";
import { cn } from "../lib/utils";
import { THEME } from "../config/theme";

const MESSAGES = [
  "Analyse de la facture en cours…",
  "Extraction des références pièces…",
  "Vérification des montants et TVA…",
  "On est avec vous, encore un instant…",
  "Structuration des données…",
  "Finalisation de l'extraction…",
];

export function ScanZone({ onFileReady, onScanConfirm, etat, progression, fichierActuel, onAnnuler }) {
  const [erreurLocale, setErreurLocale] = useState(null);
  const [messageIndex, setMessageIndex] = useState(0);
  const [previewUrl, setPreviewUrl] = useState(null);

  useEffect(() => {
    if (fichierActuel && etat === "preview") {
      const url = URL.createObjectURL(fichierActuel);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [fichierActuel, etat]);

  useEffect(() => {
    let interval;
    if (etat === "traitement") {
      interval = setInterval(() => {
        setMessageIndex((prev) => (prev + 1) % MESSAGES.length);
      }, 2500);
    } else {
      setMessageIndex(0);
    }
    return () => clearInterval(interval);
  }, [etat]);

  const onDrop = useCallback(
    (accepted, rejected) => {
      setErreurLocale(null);
      if (rejected?.length) {
        setErreurLocale("Format non supporté. Utilisez JPG, PNG, WEBP ou PDF.");
        return;
      }
      if (accepted?.[0]) onFileReady(accepted[0]);
    },
    [onFileReady]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    disabled: etat === "traitement" || etat === "preview",
    accept: {
      "image/jpeg": [],
      "image/png": [],
      "image/webp": [],
      "application/pdf": [],
    },
    maxSize: THEME.taille_max_mo * 1024 * 1024,
  });

  const enTraitement = etat === "traitement";
  const estPdf = fichierActuel?.type === "application/pdf";

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={cn(
          "relative overflow-hidden rounded-2xl border-2 border-dashed transition-all duration-300 cursor-pointer",
          "min-h-[320px] flex flex-col items-center justify-center px-8 py-12 text-center",
          isDragActive
            ? "scale-[1.01]"
            : (enTraitement || etat === "preview")
            ? "cursor-default"
            : "hover:scale-[1.005]"
        )}
        style={{
          borderColor: isDragActive
            ? "rgba(230,57,70,0.7)"
            : (enTraitement || etat === "preview")
            ? "rgba(230,57,70,0.4)"
            : "rgba(0,0,0,0.1)",
          backgroundColor: isDragActive
            ? "rgba(230,57,70,0.06)"
            : "rgba(255,255,255,0.4)",
        }}
      >
        <input {...getInputProps()} />

        {/* Scanline animée en arrière-plan */}
        {!enTraitement && (
          <div className="pointer-events-none absolute inset-x-0 top-0 bottom-0 overflow-hidden opacity-30" aria-hidden>
            <div
              className="absolute left-0 right-0 h-16 bg-gradient-to-b from-transparent via-red-500/20 to-transparent animate-scanline"
            />
          </div>
        )}

        {/* Coins style viseur */}
        {["top-3 left-3 border-t-2 border-l-2", "top-3 right-3 border-t-2 border-r-2",
          "bottom-3 left-3 border-b-2 border-l-2", "bottom-3 right-3 border-b-2 border-r-2"
        ].map((cls, i) => (
          <span key={i} className={`pointer-events-none absolute h-5 w-5 ${cls}`}
            style={{ borderColor: "rgba(230,57,70,0.4)" }} aria-hidden />
        ))}

        <AnimatePresence mode="wait">
          {etat === "attente" || etat === "succes" || etat === "erreur" ? (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="relative z-10 flex flex-col items-center"
            >
              {/* Icône centrale avec pulse */}
              <div className="relative mb-6">
                <div className="absolute inset-0 rounded-full animate-pulse-ring"
                  style={{ backgroundColor: "rgba(230,57,70,0.15)" }} />
                <div className="relative flex h-20 w-20 items-center justify-center rounded-full animate-float"
                  style={{ backgroundColor: "rgba(230,57,70,0.1)", border: "1.5px solid rgba(230,57,70,0.3)" }}>
                  {isDragActive
                    ? <UploadCloud className="h-9 w-9" style={{ color: "#E63946" }} />
                    : <ScanLine className="h-9 w-9" style={{ color: "#E63946" }} />
                  }
                </div>
              </div>

              <p className="text-xl font-extrabold" style={{ color: "var(--color-text)" }}>
                {isDragActive ? "Déposez le fichier ici" : "Glissez votre facture ici"}
              </p>
              <p className="mt-2 text-sm" style={{ color: "var(--color-text-muted)" }}>
                ou{" "}
                <span className="font-bold underline underline-offset-2" style={{ color: "#E63946" }}>
                  cliquez pour choisir
                </span>
              </p>
              <p className="mt-4 text-xs font-mono" style={{ color: "var(--color-text-muted)" }}>
                JPG · PNG · WEBP · PDF — max {THEME.taille_max_mo} Mo
              </p>

              {erreurLocale && (
                <p className="mt-4 text-sm font-bold px-4 py-2 rounded-lg"
                  style={{ color: "#E63946", backgroundColor: "rgba(230,57,70,0.1)" }}>
                  ⚠ {erreurLocale}
                </p>
              )}
            </motion.div>
          ) : etat === "preview" ? (
            /* État aperçu */
            <motion.div
              key="preview"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative z-10 flex w-full flex-col items-center gap-5 px-2"
            >
              {/* Aperçu grand format */}
              <div className="relative w-full rounded-xl overflow-hidden shadow-md" style={{ backgroundColor: "rgba(0,0,0,0.04)", minHeight: "420px" }}>
                {estPdf ? (
                  <div className="w-full flex flex-col items-center justify-center py-20">
                    <FileText className="h-16 w-16 opacity-40 mb-3" style={{ color: "var(--color-text-muted)" }} />
                    <span className="text-sm font-bold" style={{ color: "var(--color-text)" }}>Document PDF</span>
                    <span className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>{fichierActuel?.name}</span>
                  </div>
                ) : (
                  <img
                    src={previewUrl}
                    alt="Aperçu de la facture"
                    className="w-full h-auto"
                    style={{ maxHeight: "600px", objectFit: "contain" }}
                  />
                )}
                {/* Bandeau nom fichier en bas */}
                <div className="absolute inset-x-0 bottom-0 px-3 py-2 bg-gradient-to-t from-black/50 to-transparent">
                  <p className="text-xs text-white font-bold truncate">{fichierActuel?.name}</p>
                </div>
              </div>
              
              <div className="flex w-full gap-3">
                <button
                  onClick={(e) => { e.stopPropagation(); onAnnuler?.(); }}
                  className="flex-1 py-2.5 rounded-lg text-sm font-bold transition-all hover:bg-black/5"
                  style={{ color: "var(--color-text)", border: "1px solid rgba(0,0,0,0.1)" }}
                >
                  Annuler
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onScanConfirm?.(); }}
                  className="flex-1 py-2.5 rounded-lg text-sm font-bold text-white shadow-md transition-all hover:opacity-90 flex items-center justify-center gap-2"
                  style={{ backgroundColor: "#E63946" }}
                >
                  <ScanLine className="h-4 w-4" />
                  Scanner
                </button>
              </div>
            </motion.div>
          ) : (
            /* État traitement */
            <motion.div
              key="processing"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="relative z-10 flex w-full max-w-sm flex-col items-center gap-5"
            >
              {/* Fichier */}
              <div className="flex items-center gap-3 rounded-xl w-full px-4 py-3"
                style={{ backgroundColor: "rgba(0,0,0,0.04)", border: "1px solid rgba(0,0,0,0.08)" }}>
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
                  style={{ backgroundColor: "rgba(230,57,70,0.15)" }}>
                  {estPdf
                    ? <FileText className="h-5 w-5" style={{ color: "#E63946" }} />
                    : <FileImage className="h-5 w-5" style={{ color: "#E63946" }} />
                  }
                </div>
                <p className="text-sm font-bold truncate" style={{ color: "var(--color-text)" }}>
                  {fichierActuel?.name}
                </p>
              </div>

              {/* Message rotatif */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={messageIndex}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.3 }}
                  className="flex items-center gap-2"
                >
                  <div className="h-4 w-4 rounded-full border-2 animate-spin"
                    style={{ borderColor: "#E63946", borderTopColor: "transparent" }} />
                  <p className="text-sm font-bold font-mono" style={{ color: "#E63946" }}>
                    {MESSAGES[messageIndex]}
                  </p>
                </motion.div>
              </AnimatePresence>

              {/* Barre de progression */}
              <div className="w-full">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold" style={{ color: "var(--color-text-muted)" }}>Traitement IA</span>
                  <span className="text-xs font-extrabold font-mono" style={{ color: "#E63946" }}>{progression}%</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full"
                  style={{ backgroundColor: "rgba(0,0,0,0.06)" }}>
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: "linear-gradient(90deg, #E63946, #ff6b6b)" }}
                    animate={{ width: `${Math.max(progression, 5)}%` }}
                    transition={{ duration: 0.4, ease: "easeOut" }}
                  />
                </div>
              </div>

              <button
                onClick={(e) => { e.stopPropagation(); onAnnuler?.(); }}
                className="text-xs font-bold flex items-center gap-1 transition-colors hover:opacity-80"
                style={{ color: "var(--color-text-muted)" }}
              >
                <X className="h-3.5 w-3.5" /> Annuler
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
