import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Fusionne des classes Tailwind en résolvant les conflits intelligemment.
 * Convention standard shadcn/ui.
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/**
 * Formate un montant en devise configurée (Dinar Tunisien = 3 décimales).
 * Gère les valeurs absentes (-9999, null, undefined).
 */
export function formatMontant(val, devise = "DT", decimals = 3) {
  if (val === null || val === undefined || val === -9999) return "—";
  const num = Number(val);
  if (Number.isNaN(num)) return String(val);
  return `${num.toFixed(decimals)} ${devise}`;
}

/**
 * Formate un nombre simple (quantité, pourcentage) en gérant les valeurs
 * absentes et les valeurs non numériques (ex: "Tout-En-Un").
 */
export function formatNombre(val, decimals = 0) {
  if (val === null || val === undefined || val === -9999) return "—";
  const num = Number(val);
  if (Number.isNaN(num)) return String(val);
  return num.toFixed(decimals);
}

/** Formate un pourcentage de TVA/remise en gérant les valeurs absentes. */
export function formatPourcentage(val) {
  if (val === null || val === undefined || val === -9999) return "—";
  const num = Number(val);
  if (Number.isNaN(num)) return String(val);
  return `${num % 1 === 0 ? num.toFixed(0) : num}%`;
}

/** Renvoie true si une valeur de champ doit être considérée comme "absente". */
export function estVide(val) {
  return val === null || val === undefined || val === -9999 || val === "";
}
