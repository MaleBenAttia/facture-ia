// ============================================================================
// THEME.JS — Configuration (Whitelabel)
// ============================================================================

export const THEME = {
  // --- Identité ---
  nom_app: "Scanner-Pro",
  nom_magasin: "Premium Auto Parts",
  slogan: "Intelligence Artificielle de pointe pour l'automobile.",
  description_app: "Un module de scan haute performance conçu pour votre plateforme.",
  devise: "TND",

  // --- Thème : Light Aurora (Clair, premium & animé) ---
  couleurs: {
    primaire:       "#E63946",   // Rouge racing
    primaire_clair: "#ff6b6b",
    secondaire:     "#2A9D8F",   // Vert succès

    fond:           "#f8fafc",   // Gris très clair bleuté
    surface:        "rgba(255,255,255,0.7)",  // Verre dépoli clair
    surface_haute:  "rgba(255,255,255,0.9)",

  },

  formats_acceptes: ["image/jpeg", "image/png", "image/webp", "application/pdf"],
  taille_max_mo: 15,
};

export default THEME;
