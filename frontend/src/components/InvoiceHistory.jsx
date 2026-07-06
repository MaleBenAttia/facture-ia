// InvoiceHistory.jsx — Liste des factures traitees dans la session, clic pour revoir le resultat
import { History, FileText, FileImage, ChevronRight, Inbox } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/Card";
import { formatMontant } from "../lib/utils";

export function InvoiceHistory({ historique, onSelectionner, selectionneeId }) {
  return (
    <Card id="historique">
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/8 text-ink">
            <History className="h-5 w-5" />
          </div>
          <CardTitle>Historique de la session</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        {historique.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-center">
            <Inbox className="h-8 w-8 text-text-muted" />
            <p className="text-sm text-text-muted">
              Les factures traitées dans cette session apparaîtront ici.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-white/5">
            {historique.map((item) => {
              const f = item.data?.facture || {};
              const estImage = item.fichier?.type !== "application/pdf";
              return (
                <li key={item.id}>
                  <button
                    onClick={() => onSelectionner(item)}
                    className={`flex w-full items-center gap-3 rounded-lg px-2 py-3 text-left transition-colors hover:bg-white/5 ${
                      selectionneeId === item.id ? "bg-accent/10" : ""
                    }`}
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/8 text-text-muted">
                      {estImage ? <FileImage className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-ink">
                        {f.societe_nom || item.fichier?.name || "Facture"}
                      </p>
                      <p className="text-xs text-text-muted">
                        {f.numero_facture ? `N° ${f.numero_facture} · ` : ""}
                        {f.date || ""}
                      </p>
                    </div>
                    {f.net_a_payer && f.net_a_payer !== -9999 && (
                      <span className="shrink-0 text-sm font-semibold text-secondary-pale">
                        {formatMontant(f.net_a_payer, item.data?.analyse?.devise_detecte || "TND")}
                      </span>
                    )}
                    <ChevronRight className="h-4 w-4 shrink-0 text-text-muted" />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
