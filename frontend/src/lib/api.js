// ============================================================================
// API.JS — Centralise tous les appels vers le backend FastAPI
// ============================================================================
// Aucun fetch() ne doit être fait ailleurs dans l'app : tout passe par ici,
// pour que l'URL de base et la gestion d'erreurs restent cohérentes.
// ============================================================================

const API_BASE = (window.location.port === "8000" || !window.location.port)
  ? ""
  : `http://${window.location.hostname}:8000`;

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function gererReponse(res) {
  if (!res.ok) {
    let detail = `Erreur serveur (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // pas de corps JSON, on garde le message générique
    }
    throw new ApiError(detail, res.status);
  }
  return res;
}

/** Vérifie que le backend répond. */
export async function verifierSante() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    await gererReponse(res);
    return true;
  } catch {
    return false;
  }
}

/**
 * Envoie une facture au backend, reçoit un job_id immédiatement,
 * puis poll /status/{job_id} toutes les 2s jusqu'à obtenir le résultat.
 * Cette approche évite les timeouts mobiles sur les longues requêtes.
 */
export async function traiterFacture(file) {
  const formData = new FormData();
  formData.append("file", file);

  // Étape 1 : upload + démarrage du job (réponse immédiate < 1s)
  let jobId;
  try {
    const res = await fetch(`${API_BASE}/process`, {
      method: "POST",
      body: formData,
    });
    await gererReponse(res);
    const body = await res.json();
    jobId = body.job_id;
    if (!jobId) throw new ApiError("Réponse inattendue du serveur (pas de job_id)", 500);
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError("Impossible de démarrer le traitement", 0);
  }

  // Étape 2 : polling du résultat toutes les 2s (max 3 minutes)
  const MAX_ATTENTE_MS = 180_000;
  const INTERVALLE_MS  = 2_000;
  const debut = Date.now();

  while (Date.now() - debut < MAX_ATTENTE_MS) {
    await new Promise((r) => setTimeout(r, INTERVALLE_MS));
    try {
      const res = await fetch(`${API_BASE}/status/${jobId}`);
      if (!res.ok) {
        // Erreur HTTP passagère (ex: serveur en train de redémarrer) → on réessaie
        continue;
      }
      const job = await res.json();

      if (job.status === "done") {
        // Étape 3 : récupérer les données complètes dans une requête dédiée
        // (la réponse /status est légère, les données sont dans /result)
        const resData = await fetch(`${API_BASE}/result/${jobId}`);
        if (!resData.ok) {
          // Si /result échoue, on réessaie au prochain tour
          continue;
        }
        const { data } = await resData.json();
        return { data, excel: job.excel, pdf: job.pdf };
      }
      if (job.status === "error") {
        // Le serveur a retourné une erreur métier explicite → on échoue
        throw new ApiError(job.detail || "Erreur lors du traitement", 500);
      }
      // status === "processing" ou "not_found" (serveur redémarré) → on réessaie
    } catch (err) {
      if (err instanceof ApiError) throw err;
      // Erreur réseau passagère (VPN/WiFi instable) → on réessaie silencieusement
    }
  }

  throw new ApiError("Délai d'attente dépassé (3 minutes). Réessayez.", 408);
}

/** Construit l'URL de téléchargement pour une feuille Excel donnée. */
export function urlExcel(sheet) {
  return `${API_BASE}/excel/${sheet}`;
}

/** Construit l'URL de téléchargement pour un PDF généré. */
export function urlPdf(filename) {
  const nom = filename?.split("/").pop() || filename;
  return `${API_BASE}/pdf/${nom}`;
}

/** Déclenche le téléchargement d'un fichier depuis une URL donnée. */
export async function telecharger(url, nomFichier) {
  const res = await fetch(url);
  await gererReponse(res);
  const blob = await res.blob();
  const lien = document.createElement("a");
  lien.href = URL.createObjectURL(blob);
  lien.download = nomFichier;
  document.body.appendChild(lien);
  lien.click();
  lien.remove();
}

export { ApiError, API_BASE };
