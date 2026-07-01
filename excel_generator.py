import openpyxl
from openpyxl.styles import Font, PatternFill
import os

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="2E4057")

def init_workbook():
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Factures"
    wb.create_sheet("Clients")
    wb.create_sheet("Produits")
    return wb

def write_headers(ws, headers):
    for col, h in enumerate(headers, 1):
        cell = ws.cell(1, col, h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL

def ajouter_ligne(ws, headers, data: dict):
    row = ws.max_row + 1
    if ws.max_row == 1 and ws.cell(1, 1).value is None:
        row = 2
    for col, h in enumerate(headers, 1):
        ws.cell(row, col, data.get(h, None))

def json_vers_excel(facture: dict):
    f = facture.get("facture", {})
    c = facture.get("client", {})
    produits = facture.get("produits", [])

    # Génération d'un nom de fichier unique basé sur le numéro et la date de facture
    def nettoyer(s):
        """Remplace les caractères interdits dans les noms de fichiers."""
        return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(s)).strip("-")

    num   = nettoyer(f.get("numero_facture", "")) or "inconnu"
    date  = nettoyer(f.get("date", ""))           or "sans-date"

    filename = f"facture_{num}_{date}.xlsx"
    filepath = f"{OUTPUT_DIR}/{filename}"

    wb = init_workbook()
    ws_fac = wb["Factures"]
    ws_cli = wb["Clients"]
    ws_pro = wb["Produits"]

    # Injecter la devise dans l'objet facture pour l'écrire dans l'Excel
    analyse = facture.get("analyse", {})
    f["devise"] = (analyse.get("devise_detecte") or "TND").strip()

    # --- Feuille Factures ---
    fac_headers = [
        "numero_facture", "date", "societe_nom", "societe_adresse",
        "societe_tel", "societe_email", "total_ht", "montant_tva",
        "timbre_fiscal", "net_a_payer", "mode_reglement", "etat", "remarques", "devise"
    ]
    
    # Intégrer les champs supplémentaires dynamiques
    champs_sup = f.get("champs_supplementaires") or {}
    champs_sup_keys = [k for k, v in champs_sup.items() if v not in (None, "", -9999, [], {})]
    
    # Filtrer les colonnes vides (null ou -9999) pour cette facture
    fac_headers = [h for h in fac_headers if f.get(h) not in (None, "", -9999)]
    
    # Ajouter les clés supplémentaires à la fin
    fac_headers.extend(champs_sup_keys)
    
    # Colonne "remarque" obligatoire en dernier
    fac_headers.append("remarque")
    
    write_headers(ws_fac, fac_headers)
    # Ecrire les valeurs en ligne 2
    for col, h in enumerate(fac_headers, 1):
        if h == "remarque":
            parties = []
            if f.get("mode_reglement"):
                parties.append(f"Paiement : {f['mode_reglement']}")
            if f.get("etat"):
                parties.append(f"État : {f['etat']}")
            echeance = champs_sup.get("Echeance") or champs_sup.get("Échéance") or champs_sup.get("echeance")
            if echeance:
                parties.append(f"Échéance : {echeance}")
            if f.get("remarques"):
                parties.append(f"{f['remarques']}")
            ws_fac.cell(2, col, "; ".join(parties) if parties else "Rien à signaler")
        elif h in champs_sup_keys:
            val = champs_sup.get(h)
            if isinstance(val, (dict, list)):
                val = str(val)
            ws_fac.cell(2, col, val)
        else:
            ws_fac.cell(2, col, f.get(h))

    # --- Feuille Clients ---
    cli_headers = [
        "numero_facture", "code_client", "nom", "prenom",
        "telephone", "adresse", "matricule_fiscal"
    ]
    c["numero_facture"] = f.get("numero_facture")
    # Filtrer les colonnes vides pour ce client
    cli_headers = [h for h in cli_headers if c.get(h) not in (None, "", -9999)]
    # Ajouter les champs supplementaires client
    cli_champs_sup = c.get("champs_supplementaires") or {}
    cli_champs_sup_keys = [k for k, v in cli_champs_sup.items() if v not in (None, "", -9999, [], {})]
    cli_headers.extend(cli_champs_sup_keys)
    write_headers(ws_cli, cli_headers)
    for col, h in enumerate(cli_headers, 1):
        if h in cli_champs_sup_keys:
            val = cli_champs_sup.get(h)
            if isinstance(val, (dict, list)):
                val = str(val)
            ws_cli.cell(2, col, val)
        else:
            ws_cli.cell(2, col, c.get(h))

    # --- Feuille Produits ---
    # Collecter toutes les cles uniques de champs_supplementaires dans les produits
    pro_champs_sup_keys = []
    for p in produits:
        sup = p.get("champs_supplementaires") or {}
        for k in sup:
            if k not in pro_champs_sup_keys:
                pro_champs_sup_keys.append(k)

    # Si champs_supplementaires existe, on les utilise UNIQUEMENT (pas de doublon)
    if pro_champs_sup_keys:
        pro_headers = pro_champs_sup_keys
    else:
        # Fallback : colonnes standard si pas de champs_supplementaires
        pro_headers = ["designation", "quantite", "prix_u_ht"]
        has_remise = any(p.get("remise_pct") not in (None, "", -9999) for p in produits)
        has_total_ht = any(p.get("total_ht_ligne") not in (None, "", -9999) for p in produits)
        has_total_ttc = any(p.get("total_ttc") not in (None, "", -9999) for p in produits)
        has_tva = any(p.get("tva_pct") not in (None, "", -9999) for p in produits)
        if has_tva:      pro_headers.append("tva_pct")
        if has_remise:   pro_headers.append("remise_pct")
        if has_total_ht: pro_headers.append("total_ht_ligne")
        if has_total_ttc: pro_headers.append("total_ttc")

    write_headers(ws_pro, pro_headers)
    for row_idx, p in enumerate(produits, 2):
        pro_champs_sup = p.get("champs_supplementaires") or {}
        for col, h in enumerate(pro_headers, 1):
            val = pro_champs_sup.get(h)
            if val is None and not pro_champs_sup_keys:
                val = p.get(h)
            if isinstance(val, (dict, list)):
                val = str(val)
            ws_pro.cell(row_idx, col, val if val not in (-9999,) else None)

    wb.save(filepath)
    return filename