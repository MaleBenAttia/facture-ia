// ============================================================================
// THEME.JS — Configuration (Whitelabel)
// ============================================================================

export const THEME = {
  // --- Identité ---
  nom_app: "Scanner-Pro",
  nom_magasin: "Premium Auto Parts",
  devise: "TND",

  // --- Thème : Light Aurora (Clair, premium & animé) ---
  couleurs: {
    primaire:       "#E63946",   // Rouge racing
    primaire_clair: "#ff6b6b",
    secondaire:     "#2A9D8F",   // Vert succès
    texte:          "#0f172a",   // Texte principal (injecté dans --color-text, main.jsx)
    texte_attenue:  "#64748b",   // Texte atténué (injecté dans --color-text-muted, main.jsx)

    fond:           "#f8fafc",   // Gris très clair bleuté
    surface:        "rgba(255,255,255,0.7)",  // Verre dépoli clair
    surface_haute:  "rgba(255,255,255,0.9)",

  },

  taille_max_mo: 15,
};

export default THEME;
