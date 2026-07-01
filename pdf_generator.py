from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph,
    HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from html import escape
import os

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)
NULL_VAL = -9999


def fmt(val, decimals=3):
    if val is None or val == NULL_VAL:
        return "-"
    try:
        return f"{float(val):.{decimals}f}"
    except (TypeError, ValueError):
        # Valeur non numerique (ex: quantite = "Tout-En-Un") -> on l'affiche telle quelle
        return str(val)


def fmt_tva(val):
    if val is None or val == NULL_VAL:
        return "-"
    try:
        return f"{int(float(val))}%"
    except (TypeError, ValueError):
        return str(val)


def safe(txt):
    """Echappe le texte pour l'utiliser dans un Paragraph (gere les None)."""
    if txt is None:
        return ""
    return escape(str(txt))


def formater_valeur_remarque(v):
    """
    Transforme une valeur de champs_supplementaires (qui peut etre une
    liste, un dict, ou une liste de dicts comme tax_breakdown) en texte
    lisible, au lieu d'afficher le dump Python brut.
    """
    if isinstance(v, list):
        if v and all(isinstance(item, dict) for item in v):
            morceaux = []
            for item in v:
                sous = ", ".join(f"{k} : {val}" for k, val in item.items())
                morceaux.append(f"({sous})")
            return " ; ".join(morceaux)
        return ", ".join(str(item) for item in v)

    if isinstance(v, dict):
        return ", ".join(f"{k} : {val}" for k, val in v.items())

    return str(v)


def libelle_remarque(cle):
    """Transforme une cle technique (snake_case) en libelle lisible."""
    return cle.replace("_", " ").strip().capitalize()


def json_vers_pdf(facture: dict, filename: str = None) -> str:
    f = facture.get("facture", {})
    c = facture.get("client", {})
    produits = facture.get("produits", [])

    analyse = facture.get("analyse", {})
    devise = (analyse.get("devise_detecte") or "TND").strip()
    decimals = 3 if devise == "TND" else 2

    num = f.get("numero_facture") or "FACTURE"
    pdf_path = f"{OUTPUT_DIR}/facture_{num.replace(' ', '_').replace('/', '-')}.pdf"
    if filename:
        pdf_path = f"{OUTPUT_DIR}/{filename}"

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    bold = ParagraphStyle("bold", parent=styles["Normal"], fontName="Helvetica-Bold")
    center = ParagraphStyle("center", parent=styles["Normal"], alignment=TA_CENTER)
    right = ParagraphStyle("right", parent=styles["Normal"], alignment=TA_RIGHT)
    title_style = ParagraphStyle("title", parent=styles["Normal"],
                                  fontName="Helvetica-Bold", fontSize=16, alignment=TA_CENTER)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=11)
    italic = ParagraphStyle("italic", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=9)

    # Styles "cellule" avec retour a la ligne automatique
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=9, leading=11)
    cell_style_center = ParagraphStyle("cell_center", parent=cell_style, alignment=TA_CENTER)
    cell_header_style = ParagraphStyle("cell_header", parent=cell_style_center,
                                        textColor=colors.white, fontName="Helvetica-Bold")
    client_label_style = ParagraphStyle("client_label", parent=cell_style,
                                         textColor=colors.white, fontName="Helvetica-Bold")

    elements = []

    # --- En-tete societe ---
    type_fac = f.get("type_facture") or "FACTURE"
    societe_data = [
        [Paragraph(safe(f.get("societe_nom")), bold), "", Paragraph(f"<b>{safe(type_fac.upper())}</b>", title_style)],
        [Paragraph(safe(f.get("societe_adresse")), cell_style), "",
         Paragraph(f"N&#176; : {safe(f.get('numero_facture'))}", cell_style)],
        [Paragraph(f"T&#233;l : {safe(f.get('societe_tel'))}", cell_style), "",
         Paragraph(f"Date : {safe(f.get('date'))}", cell_style)],
        [Paragraph(safe(f.get("societe_email")), cell_style), "", ""],
    ]
    t_header = Table(societe_data, colWidths=[8 * cm, 2 * cm, 8 * cm])
    t_header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elements.append(t_header)

    # --- Infos societe supplementaires ---
    infos_soc = []
    if f.get("societe_matricule_fiscal"):
        infos_soc.append(f"M.F : {safe(f.get('societe_matricule_fiscal'))}")
    if f.get("societe_rc"):
        infos_soc.append(f"RC : {safe(f.get('societe_rc'))}")
    if f.get("societe_ai"):
        infos_soc.append(f"AI : {safe(f.get('societe_ai'))}")
    if f.get("societe_compte_bancaire"):
        infos_soc.append(f"Compte : {safe(f.get('societe_compte_bancaire'))}")
    if infos_soc:
        elements.append(Spacer(1, 0.2 * cm))
        elements.append(Paragraph("  |  ".join(infos_soc), small))

    elements.append(Spacer(1, 0.5 * cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2E4057")))
    elements.append(Spacer(1, 0.3 * cm))

    # --- Infos client ---
    client_nom = f"{c.get('nom') or ''} {c.get('prenom') or ''}".strip()
    client_rows = [
        ("Client", client_nom),
        ("Code", c.get("code_client") or ""),
        ("Adresse", c.get("adresse") or ""),
        ("T\u00e9l", c.get("telephone") or ""),
        ("Matricule fiscal", c.get("matricule_fiscal") or ""),
    ]
    client_rows = [(k, v) for k, v in client_rows if v and str(v).strip()]
    # Ajouter les champs supplementaires client
    cli_champs_sup = c.get("champs_supplementaires") or {}
    for k, v in cli_champs_sup.items():
        if v not in (None, "", -9999, [], {}):
            client_rows.append((libelle_remarque(k), formater_valeur_remarque(v)))
    client_data = [
        [Paragraph(safe(k), client_label_style), Paragraph(safe(v), cell_style)]
        for k, v in client_rows
    ]

    if client_data:
        t_client = Table(client_data, colWidths=[4 * cm, 14 * cm])
        t_client.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#2E4057")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_client)
        elements.append(Spacer(1, 0.5 * cm))

    # --- Tableau produits ---
    has_remise = any(
        p.get("remise_pct") not in (None, NULL_VAL, 0) for p in produits
    )
    has_tva = any(
        p.get("tva_pct") not in (None, NULL_VAL) for p in produits
    )
    has_ttc = any(
        p.get("total_ttc") not in (None, NULL_VAL) for p in produits
    )
    has_ht_ligne = any(
        p.get("total_ht_ligne") not in (None, NULL_VAL) for p in produits
    )

    prod_headers = ["D\u00e9signation", "Qt\u00e9", "Prix U HT"]
    col_widths = [6.5 * cm, 1.3 * cm, 2.7 * cm]

    if has_tva:
        prod_headers.append("TVA %")
        col_widths.append(1.8 * cm)
    if has_remise:
        prod_headers.append("Remise %")
        col_widths.append(1.8 * cm)
    if has_ht_ligne:
        prod_headers.append("Total HT")
        col_widths.append(2.4 * cm)
    if has_ttc:
        prod_headers.append("Total TTC")
        col_widths.append(2.4 * cm)

    # Collecter les cles uniques de champs_supplementaires dans les produits
    pro_champs_sup_keys = []
    for p in produits:
        sup = p.get("champs_supplementaires") or {}
        for k in sup:
            if k not in pro_champs_sup_keys:
                pro_champs_sup_keys.append(k)
    for k in pro_champs_sup_keys:
        prod_headers.append(k)
        col_widths.append(2.5 * cm)

    # Ligne d'en-tete en Paragraph (pour un wrap propre meme sur l'en-tete)
    prod_data = [[Paragraph(safe(h), cell_header_style) for h in prod_headers]]

    for p in produits:
        designation = Paragraph(safe(p.get("designation") or "-"), cell_style)
        qte_val = p.get("quantite")
        qte = fmt(qte_val, 0) if qte_val not in (None, NULL_VAL) else "-"
        row = [
            designation,
            Paragraph(safe(qte), cell_style_center),
            Paragraph(safe(fmt(p.get("prix_u_ht"), decimals)), cell_style_center),
        ]
        if has_tva:
            row.append(Paragraph(safe(fmt_tva(p.get("tva_pct"))), cell_style_center))
        if has_remise:
            remise_val = p.get("remise_pct")
            remise = f"{fmt(remise_val, 0)}%" if remise_val not in (None, NULL_VAL) else "-"
            row.append(Paragraph(safe(remise), cell_style_center))
        if has_ht_ligne:
            row.append(Paragraph(safe(fmt(p.get("total_ht_ligne"), decimals)), cell_style_center))
        if has_ttc:
            row.append(Paragraph(safe(fmt(p.get("total_ttc"), decimals)), cell_style_center))
        # Ajouter les champs supplementaires
        pro_champs_sup = p.get("champs_supplementaires") or {}
        for k in pro_champs_sup_keys:
            val = pro_champs_sup.get(k)
            if val in (None, NULL_VAL):
                row.append(Paragraph("-", cell_style_center))
            elif isinstance(val, (dict, list)):
                row.append(Paragraph(safe(formater_valeur_remarque(val)), cell_style))
            else:
                row.append(Paragraph(safe(str(val)), cell_style_center))
        prod_data.append(row)

    t_prod = Table(prod_data, colWidths=col_widths, repeatRows=1)
    t_prod.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E4057")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUND", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_prod)
    elements.append(Spacer(1, 0.5 * cm))

    # --- Totaux (bloc groupe pour ne pas etre coupe entre 2 pages) ---
    bloc_totaux = []

    totaux_data = []
    if f.get("total_ht") not in (None, NULL_VAL):
        totaux_data.append(["Total HT", f"{fmt(f.get('total_ht'), decimals)} {devise}"])
    if f.get("montant_tva") not in (None, NULL_VAL):
        totaux_data.append(["TVA", f"{fmt(f.get('montant_tva'), decimals)} {devise}"])
    if f.get("timbre_fiscal") not in (None, NULL_VAL, 0):
        totaux_data.append(["Timbre fiscal", f"{fmt(f.get('timbre_fiscal'), decimals)} {devise}"])
    if f.get("net_a_payer") not in (None, NULL_VAL):
        totaux_data.append(["Net \u00e0 payer", f"{fmt(f.get('net_a_payer'), decimals)} {devise}"])

    if totaux_data:
        t_totaux = Table(totaux_data, colWidths=[4 * cm, 4 * cm])
        t_totaux.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#2E4057")),
            ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ]))
        t_totaux_wrapper = Table([[None, t_totaux]], colWidths=[10 * cm, 8 * cm])
        bloc_totaux.append(t_totaux_wrapper)
        bloc_totaux.append(Spacer(1, 0.3 * cm))

    # --- Montant en lettres ---
    if f.get("montant_en_lettres"):
        bloc_totaux.append(
            Paragraph(f"Arr\u00eat\u00e9e \u00e0 la somme de : <b>{safe(f.get('montant_en_lettres'))}</b>", italic)
        )
        bloc_totaux.append(Spacer(1, 0.3 * cm))

    # --- Mode reglement ---
    if f.get("mode_reglement"):
        bloc_totaux.append(
            Paragraph(f"Mode de r\u00e8glement : <b>{safe(f.get('mode_reglement'))}</b>", styles["Normal"])
        )
        bloc_totaux.append(Spacer(1, 0.3 * cm))

    # --- Etat PAYE / IMPAYE ---
    etat = f.get("etat")
    if etat:
        couleur = colors.green if etat.upper() == "PAYE" else colors.red
        etat_data = [[Paragraph(f"<b>{safe(etat.upper())}</b>", ParagraphStyle(
            "etat", parent=styles["Normal"], textColor=colors.white, alignment=TA_CENTER,
            fontName="Helvetica-Bold", fontSize=14))]]
        t_etat = Table(etat_data, colWidths=[4 * cm])
        t_etat.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), couleur),
        ]))
        bloc_totaux.append(t_etat)
        bloc_totaux.append(Spacer(1, 0.3 * cm))

    if bloc_totaux:
        elements.append(KeepTogether(bloc_totaux))

    # --- Remarques ---
    champs_sup = f.get("champs_supplementaires", {}) or {}
    mots_a_exclure = ["signature", "fournisseur", "client", "cachet"]
    champs_filtres = {
        k: v for k, v in champs_sup.items()
        if v not in (None, "", [], {}) and not any(mot in k.lower() for mot in mots_a_exclure)
    }

    if champs_filtres:
        entete_remarques = [
            HRFlowable(width="100%", thickness=0.5, color=colors.grey),
            Spacer(1, 0.2 * cm),
            Paragraph("<b>Remarques :</b>", small),
            Spacer(1, 0.1 * cm),
        ]

        # Tableau libelle | valeur (avec wrap propre), au lieu d'une ligne
        # de texte brut par champ qui deborde ou s'affiche en dump Python.
        remarques_data = []
        for k, v in champs_filtres.items():
            valeur_txt = formater_valeur_remarque(v)
            remarques_data.append([
                Paragraph(f"<b>{safe(libelle_remarque(k))}</b>", small),
                Paragraph(safe(valeur_txt), small),
            ])

        t_remarques = Table(remarques_data, colWidths=[4.5 * cm, 13 * cm])
        t_remarques.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#E0E0E0")),
        ]))

        # Si la liste est courte, on garde tout groupe sur une page.
        # Si elle est longue, on laisse le moteur la repartir naturellement
        # plutot que de risquer un gros vide en bas de page.
        if len(remarques_data) <= 6:
            elements.append(KeepTogether(entete_remarques + [t_remarques]))
        else:
            elements.extend(entete_remarques)
            elements.append(t_remarques)

    doc.build(elements)
    return pdf_path