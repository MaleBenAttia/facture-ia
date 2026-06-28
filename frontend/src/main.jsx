import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { THEME } from "./config/theme.js";
import "./index.css";

/**
 * Injecte toutes les couleurs définies dans theme.js comme variables CSS globales.
 * Toute personnalisation du fichier theme.js se répercute immédiatement dans le design.
 */
function appliquerTheme(theme) {
  const racine = document.documentElement;
  const c = theme.couleurs;

  // Couleur primaire (Racing Red)
  racine.style.setProperty("--color-primary", c.primaire);
  racine.style.setProperty("--color-primary-light", c.primaire_clair);
  racine.style.setProperty("--color-primary-50", c.primaire_clair);
  racine.style.setProperty("--color-primary-100", c.primaire_clair);
  racine.style.setProperty("--color-primary-900", c.primaire);

  // Couleur secondaire (Success Green)
  racine.style.setProperty("--color-secondary", c.secondaire);
  racine.style.setProperty("--color-secondary-pale", c.secondaire_pale);

  // Compatibilité alias accent = secondary
  racine.style.setProperty("--color-accent", c.secondaire);
  racine.style.setProperty("--color-accent-soft", c.secondaire_pale);

  // Fonds
  racine.style.setProperty("--color-bg", c.fond);
  racine.style.setProperty("--color-surface", c.surface);
  racine.style.setProperty("--color-surface-raised", c.surface_haute);

  // Textes
  racine.style.setProperty("--color-ink", c.texte);
  racine.style.setProperty("--color-text", c.texte);
  racine.style.setProperty("--color-text-muted", c.texte_attenue);

  // Titre de la page
  document.title = `${theme.nom_app} · ${theme.nom_magasin}`;
}

appliquerTheme(THEME);

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
