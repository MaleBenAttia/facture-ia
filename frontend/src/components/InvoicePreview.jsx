import {
  Building2,
  User,
  FileSpreadsheet,
  FileDown,
  Receipt,
  CheckCircle2,
  CircleSlash,
  AlertTriangle,
  XCircle,
  Info,
  Globe,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/Card";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";
import { formatMontant, formatNombre, formatPourcentage, estVide } from "../lib/utils";
import { THEME } from "../config/theme";

function Champ({ label, valeur }) {
  if (estVide(valeur)) return null;
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-text-muted">{label}</p>
      <p className="text-sm text-ink mt-0.5">{valeur}</p>
    </div>
  );
}

const ALERTE_STYLES = {
  erreur:        { bg: "rgba(220,38,38,0.08)",  border: "rgba(220,38,38,0.3)",  text: "#dc2626", Icon: XCircle },
  avertissement: { bg: "rgba(234,179,8,0.08)",  border: "rgba(234,179,8,0.35)", text: "#b45309", Icon: AlertTriangle },
  info:          { bg: "rgba(59,130,246,0.07)", border: "rgba(59,130,246,0.25)",text: "#2563eb", Icon: Info },
  success:       { bg: "rgba(22,163,74,0.07)",  border: "rgba(22,163,74,0.25)", text: "#16a34a", Icon: CheckCircle2 },
};

function AlertsBanner({ analyse }) {
  if (!analyse) return null;
  const alertes = analyse.alertes?.filter(a => a?.message) ?? [];
  const devise = analyse.devise_detecte;

  // Séparer les erreurs/avertissements des succès
  const problems = alertes.filter(a => a.type !== "success" && a.type !== "info");
  const success  = alertes.filter(a => a.type === "success");
  const infos    = alertes.filter(a => a.type === "info");

  return (
    <div className="space-y-2">
      {/* Bandeau devise en petit, discret */}
      {devise && (
        <div className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold"
          style={{ backgroundColor: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.15)", color: "#2563eb" }}>
          <Globe className="h-3.5 w-3.5 shrink-0" />
          <span>Devise détectée : <strong>{devise}</strong></span>
        </div>
      )}

      {/* Erreurs et avertissements uniquement */}
      {problems.map((alerte, i) => {
        const style = ALERTE_STYLES[alerte.type] ?? ALERTE_STYLES.info;
        const { Icon } = style;
        return (
          <div key={i} className="flex items-start gap-2.5 rounded-lg px-3 py-2.5 text-sm"
            style={{ backgroundColor: style.bg, border: `1px solid ${style.border}` }}>
            <Icon className="h-4 w-4 mt-0.5 shrink-0" style={{ color: style.text }} />
            <span style={{ color: style.text }}>{alerte.message}</span>
          </div>
        );
      })}

      {/* Message "tout est correct" seulement si aucune erreur */}
      {problems.length === 0 && success.length > 0 && (
        <div className="flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm"
          style={{ backgroundColor: "rgba(22,163,74,0.07)", border: "1px solid rgba(22,163,74,0.25)" }}>
          <CheckCircle2 className="h-4 w-4 shrink-0" style={{ color: "#16a34a" }} />
          <span style={{ color: "#16a34a" }} className="font-semibold">Calculs vérifiés et corrects.</span>
        </div>
      )}
    </div>
  );
}

export function InvoicePreview({ resultat, onTelechargerExcel, onTelechargerPdf, telechargement }) {
  if (!resultat) return null;
  const { facture: f = {}, client: c = {}, produits = [] } = resultat.data || {};
  
  // Limiter l'affichage à 50 produits max pour éviter les plantages de rendu
  const produitsAffiches = produits.slice(0, 50);
  const produitsTronques = produits.length > 50;
  
  // Utiliser la devise détectée par l'IA si disponible, sinon repli sur celle du thème
  const devise = resultat.data?.analyse?.devise_detecte || THEME.devise;

  const colonnes = {
    tva: produitsAffiches.some((p) => !estVide(p.tva_pct)),
    remise: produitsAffiches.some((p) => !estVide(p.remise_pct) && p.remise_pct !== 0),
    totalHt: produitsAffiches.some((p) => !estVide(p.total_ht_ligne)),
    totalTtc: produitsAffiches.some((p) => !estVide(p.total_ttc)),
  };

  // Collecter toutes les cles uniques de champs_supplementaires produits
  const proSupKeys = [];
  produitsAffiches.forEach(p => {
    if (p.champs_supplementaires) {
      Object.keys(p.champs_supplementaires).forEach(k => {
        if (!proSupKeys.includes(k)) proSupKeys.push(k);
      });
    }
  });

  // Filtrer les champs supplementaires client non vides
  const clientSupEntries = c.champs_supplementaires
    ? Object.entries(c.champs_supplementaires).filter(([, v]) => !estVide(v) && typeof v !== 'object')
    : [];

  const clientNom = [c.nom, c.prenom].filter((v) => !estVide(v)).join(" ");
  const estPaye = f.etat && f.etat.toUpperCase() === "PAYE";

  return (
    <div id="resultat" className="mx-auto w-full max-w-4xl animate-fade-up space-y-5">

      {/* Alertes et contexte IA — toujours en premier */}
      {resultat.data?.analyse && (
        <AlertsBanner analyse={resultat.data.analyse} />
      )}

      {/* En-tête facture */}
      <Card glow>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/15 text-accent">
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <CardTitle>{f.societe_nom || "Société non identifiée"}</CardTitle>
              <p className="text-xs text-text-muted mt-0.5">
                {f.type_facture || "Facture"} {f.numero_facture ? `· N° ${f.numero_facture}` : ""}
              </p>
            </div>
          </div>
          {f.etat && (
            <Badge variant={estPaye ? "success" : "danger"}>
              {estPaye ? <CheckCircle2 className="h-3.5 w-3.5" /> : <CircleSlash className="h-3.5 w-3.5" />}
              {f.etat.toUpperCase()}
            </Badge>
          )}
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Champ label="Date" valeur={f.date} />
            <Champ label="Matricule fiscal" valeur={f.societe_matricule_fiscal} />
            <Champ label="Téléphone" valeur={f.societe_tel} />
            <Champ label="Email" valeur={f.societe_email} />
            {f.champs_supplementaires && Object.entries(f.champs_supplementaires).map(([key, value]) => {
              if (estVide(value) || typeof value === 'object') return null;
              const motsExclus = ["signature", "fournisseur", "client", "cachet"];
              if (motsExclus.some(mot => key.toLowerCase().includes(mot))) return null;
              const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
              return <Champ key={key} label={label} valeur={value} />;
            })}
          </div>
        </CardContent>
      </Card>

      {/* Infos client */}
      {(clientNom || c.code_client || c.adresse || clientSupEntries.length > 0) && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/8 text-ink">
                <User className="h-5 w-5" />
              </div>
              <CardTitle>Client</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Champ label="Nom" valeur={clientNom} />
              <Champ label="Code client" valeur={c.code_client} />
              <Champ label="Adresse" valeur={c.adresse} />
              <Champ label="Téléphone" valeur={c.telephone} />
              <Champ label="Matricule fiscal" valeur={c.matricule_fiscal} />
              {clientSupEntries.map(([key, value]) => {
                const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                return <Champ key={key} label={label} valeur={value} />;
              })}
            </div>
          </CardContent>
        </Card>
      )}

{/* Tableau produits */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/8 text-ink">
              <Receipt className="h-5 w-5" />
            </div>
            <CardTitle>
              Produits ({produits.length})
              {produitsTronques && (
                <span className="ml-2 text-xs font-normal text-orange-500">
                  (affichage limité à 50)
                </span>
              )}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[480px] text-sm">
            <thead>
              <tr className="border-b border-white/10 text-left text-[11px] uppercase tracking-wide text-text-muted">
                {proSupKeys.length > 0 ? (
                  proSupKeys.map(key => (
                    <th key={key} className="py-2 px-3 font-medium text-center text-[11px]">
                      {key.replace(/_/g, ' ')}
                    </th>
                  ))
                ) : (
                  <>
                    <th className="py-2 pr-3 font-medium">Désignation</th>
                    <th className="py-2 px-3 font-medium text-center">Qté</th>
                    <th className="py-2 px-3 font-medium text-right">Prix U HT</th>
                    {colonnes.tva && <th className="py-2 px-3 font-medium text-center">TVA</th>}
                    {colonnes.remise && <th className="py-2 px-3 font-medium text-center">Remise</th>}
                    {colonnes.totalHt && <th className="py-2 px-3 font-medium text-right">Total HT</th>}
                    {colonnes.totalTtc && <th className="py-2 pl-3 font-medium text-right">Total TTC</th>}
                  </>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {produitsAffiches.map((p, i) => (
                <tr key={i} className="text-ink">
                  {proSupKeys.length > 0 ? (
                    proSupKeys.map(key => {
                      const val = p.champs_supplementaires?.[key];
                      return (
                        <td key={key} className="py-2.5 px-3 text-center text-text-muted text-xs">
                          {estVide(val) ? "—" : String(val)}
                        </td>
                      );
                    })
                  ) : (
                    <>
                      <td className="py-2.5 pr-3">{p.designation || "—"}</td>
                      <td className="py-2.5 px-3 text-center text-text-muted">
                        {estVide(p.quantite) ? "—" : p.quantite}
                      </td>
                      <td className="py-2.5 px-3 text-right">{formatMontant(p.prix_u_ht, devise)}</td>
                      {colonnes.tva && (
                        <td className="py-2.5 px-3 text-center text-text-muted">
                          {formatPourcentage(p.tva_pct)}
                        </td>
                      )}
                      {colonnes.remise && (
                        <td className="py-2.5 px-3 text-center text-text-muted">
                          {formatPourcentage(p.remise_pct)}
                        </td>
                      )}
                      {colonnes.totalHt && (
                        <td className="py-2.5 px-3 text-right">
                          {formatMontant(p.total_ht_ligne, devise)}
                        </td>
                      )}
                      {colonnes.totalTtc && (
                        <td className="py-2.5 pl-3 text-right font-medium">
                          {formatMontant(p.total_ttc, devise)}
                        </td>
                      )}
                    </>
                  )}
                </tr>
              ))}
              {produitsTronques && (
                <tr className="bg-amber-50/20">
                  <td colSpan={proSupKeys.length > 0 ? proSupKeys.length : 8} className="py-3 text-center text-amber-600 text-xs font-medium">
                    ... et {produits.length - 50} autres produits (voir Excel/PDF complets)
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Totaux */}
      <Card>
        <CardContent className="pt-5">
          <div className="ml-auto w-full max-w-xs space-y-2 text-sm">
            {!estVide(f.total_ht) && (
              <div className="flex justify-between text-text-muted">
                <span>Total HT</span>
                <span className="text-ink">{formatMontant(f.total_ht, devise)}</span>
              </div>
            )}
            {!estVide(f.montant_tva) && (
              <div className="flex justify-between text-text-muted">
                <span>TVA</span>
                <span className="text-ink">{formatMontant(f.montant_tva, devise)}</span>
              </div>
            )}
            {!estVide(f.timbre_fiscal) && f.timbre_fiscal !== 0 && (
              <div className="flex justify-between text-text-muted">
                <span>Timbre fiscal</span>
                <span className="text-ink">{formatMontant(f.timbre_fiscal, devise)}</span>
              </div>
            )}
            {!estVide(f.net_a_payer) && (
              <div className="flex justify-between rounded-lg bg-accent/10 px-3 py-2 font-display font-semibold text-secondary-pale">
                <span>Net à payer</span>
                <span>{formatMontant(f.net_a_payer, devise)}</span>
              </div>
            )}
          </div>
          {f.montant_en_lettres && (
            <p className="mt-4 text-xs italic text-text-muted">
              Arrêtée à la somme de : <span className="text-ink">{f.montant_en_lettres}</span>
            </p>
          )}
        </CardContent>
      </Card>

      {/* Actions de téléchargement */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button
          variant="secondary"
          size="lg"
          className="flex-1"
          onClick={onTelechargerExcel}
          disabled={telechargement === "excel"}
        >
          <FileSpreadsheet className="h-4.5 w-4.5" />
          {telechargement === "excel" ? "Téléchargement…" : "Télécharger Excel"}
        </Button>
        <Button
          variant="primary"
          size="lg"
          className="flex-1"
          onClick={onTelechargerPdf}
          disabled={telechargement === "pdf"}
        >
          <FileDown className="h-4.5 w-4.5" />
          {telechargement === "pdf" ? "Téléchargement…" : "Télécharger PDF"}
        </Button>
      </div>
    </div>
  );
}
