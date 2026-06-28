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
 * Envoie une facture (image ou PDF) au backend pour extraction + génération
 * Excel/PDF. Retourne { data, excel, pdf }.
 */
export async function traiterFacture(file, { onProgress } = {}) {
  const formData = new FormData();
  formData.append("file", file);

  // XHR plutôt que fetch ici, pour pouvoir suivre la progression de l'upload
  // (fetch ne donne pas d'event de progression natif sur le corps envoyé).
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/process`);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new ApiError("Réponse invalide du serveur", xhr.status));
        }
      } else {
        let detail = `Erreur serveur (${xhr.status})`;
        try {
          const body = JSON.parse(xhr.responseText);
          if (body?.detail) detail = body.detail;
        } catch {
          // ignore
        }
        reject(new ApiError(detail, xhr.status));
      }
    };

    xhr.onerror = () => reject(new ApiError("Connexion au serveur impossible", 0));
    xhr.send(formData);
  });
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
