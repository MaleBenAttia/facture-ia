import PIL.Image
import io
import yaml
import json, os, random, threading, time
from pathlib import Path
from datetime import date, datetime
from dotenv import load_dotenv
import cv2
from image_preprocessor import preparer_image_pour_llm

# Charge le .env depuis le répertoire du fichier lui-même (indépendant du cwd)
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

QUOTA_JOUR   = 1500
QUOTA_MINUTE = 10
FICHIER      = "usage_counter.json"
compteur_lock = threading.Lock()

# ─── CLÉS API (charge 1 a 6 cles depuis .env, retrocompatible GEMINI_API_KEY) ─
GEMINI_API_KEYS = [
    k for k in [
        os.getenv("GEMINI_API_KEY1"),
        os.getenv("GEMINI_API_KEY2"),
        os.getenv("GEMINI_API_KEY3"),
        os.getenv("GEMINI_API_KEY4"),
        os.getenv("GEMINI_API_KEY5"),
        os.getenv("GEMINI_API_KEY6"),
        os.getenv("GEMINI_API_KEY"),   # ancienne clé unique (fallback final)
    ] if k
]
if not GEMINI_API_KEYS:
    raise EnvironmentError("Aucune clé API Gemini trouvée dans le fichier .env ! "
                           "Définissez GEMINI_API_KEY1..6 ou GEMINI_API_KEY.")

# ─── MODÈLE UNIQUE (Gemini Flash, pas de fallback multi-modèle) ──────────────
MODELES = ["gemini-2.5-flash"]

# ─── ROTATION DES CLÉS (thread-safe) : pool aleatoire, mise de côté si 2 echecs
#     Quand le pool est vide, toutes les cles redeviennent disponibles.
_key_lock = threading.Lock()
_available_keys = list(enumerate(GEMINI_API_KEYS))  # [(idx, key), ...]

# Log de démarrage : confirme le chargement des clés (masquées)
print(f"[GEMINI] {len(GEMINI_API_KEYS)} clé(s) API chargée(s) :", end=" ")
for i, k in enumerate(GEMINI_API_KEYS, 1):
    print(f"Clé{i}=...{k[-6:]}", end="  ")
print()


PRIX_INPUT_PAR_MILLION    = 0.30
PRIX_OUTPUT_PAR_MILLION   = 2.50
PRIX_THINKING_PAR_MILLION = 0.30

COLONNES_PRODUIT_STANDARDS = {
    "numero_ligne", "designation", "quantite", "prix_u_ht",
    "tva_pct", "total_ht_ligne", "total_ttc", "remise_pct"
}

_ALIASES_COLONNES = {
    "numero_ligne":  {"numero_ligne", "n°", "n", "no", "num", "ligne"},
    "designation":   {"designation", "désignation", "description", "article", "libellé", "libelle", "produit"},
    "quantite":      {"quantite", "quantité", "qté", "qte", "qty", "qtt"},
    "prix_u_ht":     {"prix_u_ht", "pu.ht", "pu", "prix unitaire", "prix", "pu ht", "prix_u"},
    "tva_pct":       {"tva_pct", "tva", "tva %", "tva%"},
    "total_ht_ligne":{"total_ht_ligne", "total ht", "montant ht", "total_ht", "montant_ht", "montant ht"},
    "total_ttc":     {"total_ttc", "total ttc", "montant ttc", "total_ttc", "montant_ttc"},
    "remise_pct":    {"remise_pct", "remise", "r%", "r %", "remise %"},
}

_MAPPEUR_SUPP_VERS_STANDARD = {
    "qté": "quantite", "qte": "quantite", "qty": "quantite", "quantité": "quantite",
    "pu.ht": "prix_u_ht", "pu": "prix_u_ht", "prix": "prix_u_ht",
    "tva": "tva_pct", "tva %": "tva_pct", "tva%": "tva_pct",
    "montant ht": "total_ht_ligne", "montant_ht": "total_ht_ligne",
    "total ht": "total_ht_ligne",
    "r%": "remise_pct", "r %": "remise_pct", "remise": "remise_pct", "remise %": "remise_pct",
    "total ttc": "total_ttc", "montant ttc": "total_ttc",
}


def _normaliser_nombre(val):
    """Convertit '1,804' → 1.804 (format tunisien virgule comme decimal)."""
    if isinstance(val, (int, float)):
        return val
    val = val.strip().replace(" ", "").replace("\u202f", "").replace("\xa0", "")
    if not val:
        return -9999
    # Compter les points et virgules
    nb_points = val.count(".")
    nb_virgules = val.count(",")
    if nb_points > 0 and nb_virgules > 0:
        # Les deux présents : la dernière occurrence est le séparateur décimal
        if val.rfind(",") > val.rfind("."):
            # Virgule est le séparateur décimal
            val = val.replace(".", "").replace(",", ".")
        else:
            # Point est le séparateur décimal
            val = val.replace(",", "")
    elif nb_virgules == 1:
        # Une seule virgule → c'est le séparateur décimal
        val = val.replace(",", ".")
    elif nb_virgules > 1:
        # Plusieurs virgules → ce sont des séparateurs de milliers, enlever
        val = val.replace(",", "")
    try:
        return float(val)
    except (ValueError, TypeError):
        return -9999


def _parser_tsv_produits(tsv_text):
    """Parse le TSV → liste de dicts. Detecte les colonnes par nom, garde l'ordre original."""
    lignes = [l for l in tsv_text.strip().split("\n") if l.strip()]
    if not lignes:
        return [], []

    headers_raw = [h.strip() for h in lignes[0].split("\t")]
    headers_lower = [h.lower().strip() for h in headers_raw]

    col_index = {}
    supp_indices = []

    for cle_standard, aliases in _ALIASES_COLONNES.items():
        for i, h in enumerate(headers_lower):
            if h in aliases:
                col_index[cle_standard] = i
                break

    for i, h in enumerate(headers_lower):
        if i not in col_index.values():
            supp_indices.append(i)

    # Construire col_order dans l'ordre d'apparition dans le TSV
    col_order = []
    std_to_label = {
        "numero_ligne": "N°", "designation": "Désignation", "quantite": "Qté",
        "prix_u_ht": "Prix U HT", "tva_pct": "TVA %", "remise_pct": "Remise %",
        "total_ht_ligne": "Total HT", "total_ttc": "Total TTC",
    }
    # Colonnes standards (sans numero_ligne) dans l'ordre du TSV
    for i, h in enumerate(headers_raw):
        h_lower = h.lower().strip()
        if h_lower in _ALIASES_COLONNES.get("numero_ligne", set()):
            continue
        found = False
        for cle_standard, aliases in _ALIASES_COLONNES.items():
            if h_lower in aliases:
                col_order.append({"label": std_to_label.get(cle_standard, cle_standard), "field": cle_standard, "supp_key": None})
                found = True
                break
        if not found:
            col_order.append({"label": h, "field": None, "supp_key": h})

    produits = []
    for ligne in lignes[1:]:
        valeurs = ligne.split("\t")
        produit = {"champs_supplementaires": {}}

        for cle_standard in COLONNES_PRODUIT_STANDARDS:
            if cle_standard in col_index:
                idx = col_index[cle_standard]
                val = valeurs[idx].strip() if idx < len(valeurs) else ""
                produit[cle_standard] = val

        for idx in supp_indices:
            val = valeurs[idx].strip() if idx < len(valeurs) else ""
            nom_colonne = headers_raw[idx]
            nom_lower = headers_lower[idx]
            cle_standard_mappee = _MAPPEUR_SUPP_VERS_STANDARD.get(nom_lower)
            if cle_standard_mappee and cle_standard_mappee in produit:
                std_val = _normaliser_nombre(produit[cle_standard_mappee])
                supp_val = _normaliser_nombre(val)
                if std_val == -9999 and supp_val != -9999:
                    produit[cle_standard_mappee] = val
            elif val:
                produit["champs_supplementaires"][nom_colonne] = val

        for cle in ["quantite", "prix_u_ht", "tva_pct", "total_ht_ligne", "total_ttc", "remise_pct"]:
            if cle in produit:
                produit[cle] = _normaliser_nombre(produit[cle])

        if "numero_ligne" in produit:
            try:
                produit["numero_ligne"] = int(_normaliser_nombre(produit["numero_ligne"]))
            except (ValueError, TypeError):
                pass

        produits.append(produit)
    return produits, col_order


def lire_compteur():
    aujourd_hui     = str(date.today())
    minute_actuelle = datetime.now().strftime("%Y-%m-%d %H:%M")
    if os.path.exists(FICHIER):
        with open(FICHIER, "r") as f:
            data = json.load(f)
        if data.get("date") != aujourd_hui:
            data = {"date": aujourd_hui, "requetes_jour": 0, "tokens_jour": 0, "cout_jour": 0.0, "minute": minute_actuelle, "requetes_minute": 0}
        if data.get("minute") != minute_actuelle:
            data["minute"]          = minute_actuelle
            data["requetes_minute"] = 0
        return data
    return {"date": aujourd_hui, "requetes_jour": 0, "tokens_jour": 0, "cout_jour": 0.0, "minute": minute_actuelle, "requetes_minute": 0}

def sauver_compteur(data):
    with open(FICHIER, "w") as f:
        json.dump(data, f)

def _appeler_gemini(api_key: str, pages_data: list, prompt: str, max_retries: int = 2, text_content: str = None):
    """Appelle Gemini Flash, reessaie 1x si 429/503 avec backoff exponentiel."""
    from google import genai
    from google.genai import types

    if not api_key or not api_key.strip():
        raise ValueError("api_key est vide ou None. Verifiez GEMINI_API_KEY1..6 dans .env")

    client = genai.Client(api_key=api_key.strip())

    if text_content is not None:
        contents = [text_content, prompt]
    else:
        pil_images = []
        for data, mime in pages_data:
            pil_images.append(PIL.Image.open(io.BytesIO(data)))
        contents = pil_images + [prompt]

    config = types.GenerateContentConfig(
        max_output_tokens=65536,
        thinking_config=types.ThinkingConfig(thinking_budget=5555)
    )

    modele = MODELES[0]
    for tentative in range(1, max_retries + 1):
        try:
            t0 = time.perf_counter()
            response = client.models.generate_content(
                model=modele,
                contents=contents,
                config=config
            )
            duree = time.perf_counter() - t0

            # ── Métriques de performance ──────────────────────────────
            usage = getattr(response, "usage_metadata", None)
            tokens_out   = getattr(usage, "candidates_token_count", 0) or 0
            tokens_in    = getattr(usage, "prompt_token_count",     0) or 0
            tokens_think = getattr(usage, "thoughts_token_count",   0) or 0
            tokens_total = getattr(usage, "total_token_count",      0) or 0
            tok_s = tokens_out / duree if duree > 0 else 0

            print(
                f"  [PERF] ✅ {modele} | "
                f"⏱  {duree:.2f}s | "
                f"🚀 {tok_s:.1f} tok/s | "
                f"in={tokens_in} out={tokens_out}"
                + (f" think={tokens_think}" if tokens_think else "")
                + f" total={tokens_total}"
            )
            # ─────────────────────────────────────────────────────────

            # Attache la durée à la réponse pour la réutiliser dans le résumé
            response._perf_duree  = duree
            response._perf_tok_s  = tok_s

            return response
        except Exception as e:
            dernier_erreur = e
            msg = str(e)
            est_503 = "503" in msg or "UNAVAILABLE" in msg
            est_429 = "429" in msg or "RESOURCE_EXHAUSTED" in msg

            if tentative < max_retries:
                if est_503:
                    attente = min(2 ** tentative, 10)
                    print(f"  [API]  {modele} 503 (tentative {tentative}/{max_retries}) -- attente {attente}s...")
                    time.sleep(attente)
                    continue
                elif est_429:
                    import re as _re
                    match = _re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+\.?\d*)s", msg)
                    wait = float(match.group(1)) if match else 30
                    wait = min(wait, 60)
                    print(f"  [API]  {modele} 429 (tentative {tentative}/{max_retries}) -- attente {wait:.0f}s...")
                    time.sleep(wait)
                    continue
                else:
                    print(f"  [API]  {modele} erreur (tentative {tentative}/{max_retries}) : {type(e).__name__}")
                    continue

    raise dernier_erreur or RuntimeError("Impossible d'atteindre Gemini.")


def extraire_facture(image_path: str, content_type: str = "image/png", cancel_event=None) -> dict:
    """Pipeline complet : preprocess → rotation cle → Gemini → parse YAML+TSV."""
    global _available_keys, _key_lock
    if cancel_event and cancel_event.is_set():
        raise InterruptedError("Job annulé par l'utilisateur.")

    # ── Lecture et préprocessing de l'image (multi‑pages supporté) ────────

    with open(image_path, "rb") as f:
        file_bytes = f.read()
    print(f"  [PREPROC] Fichier original: {len(file_bytes)/1024:.1f} Ko, type: {content_type}")
    prepared = preparer_image_pour_llm(file_bytes, content_type)

    # ── Cas markdown : texte brut envoyé directement au LLM ──────────────
    is_markdown = isinstance(prepared, str)
    if is_markdown:
        markdown_text = prepared
        print(f"  [PREPROC] Fichier markdown : {len(markdown_text)} caractères, envoi texte brut au LLM")
    else:
        images_bgr = prepared
        if not images_bgr:
            raise ValueError("Aucune image extraite du fichier")
        print(f"  [PREPROC] {len(images_bgr)} page(s) prétraitée(s), encodage JPG...")
        MAX_LONG_COTE = 2000
        pages_data = []
        for i, img_bgr in enumerate(images_bgr):
            h, w = img_bgr.shape[:2]
            if len(images_bgr) > 1 and max(w, h) > MAX_LONG_COTE:
                echelle = MAX_LONG_COTE / max(w, h)
                nouvelle = (int(w * echelle), int(h * echelle))
                img_bgr = cv2.resize(img_bgr, nouvelle, interpolation=cv2.INTER_AREA)
            success, buffer = cv2.imencode(".jpg", img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            if not success or buffer is None or len(buffer) == 0:
                raise ValueError(f"Échec de l'encodage JPG pour la page {i+1}")
            image_data = buffer.tobytes()
            pages_data.append((image_data, "image/jpeg"))
            print(f"  [PREPROC]   Page {i+1}: {img_bgr.shape[1]}x{img_bgr.shape[0]} px, {len(image_data)/1024:.1f} Ko")
        os.makedirs("imagetraiter", exist_ok=True)
        for i, (data, _) in enumerate(pages_data):
            with open(f"imagetraiter/page_{i+1}.jpg", "wb") as f:
                f.write(data)
        total_ko = sum(len(d) for d, _ in pages_data) / 1024
        print(f"  [PREPROC] {len(pages_data)} page(s) sauvegardée(s) dans imagetraiter/page_*.jpg")
        print(f"  [PREPROC] Envoi à Gemini: {len(pages_data)} page(s), {total_ko:.1f} Ko total")

    # Prompt envoye tel quel a Gemini (instructions extraction + format attendu)
    prompt = """
Expert-comptable specialise factures Maghreb/Europe/MO. Extrais TOUTES les donnees avec precision.

════════════════════════════════════════
PARTIE 1 — EXTRACTION
════════════════════════════════════════

REGLES :
- Retourne bloc <YAML> (metadonnees) + bloc <TSV> (produits). Zero markdown, backticks, commentaires.
- Champ absent/vide → laisse vide. Valeur numerique absente → -9999. 0 dans la facture → 0.0.
- Si valeur YAML contient ":" → guillemets doubles ex: "Siège Social : 76, Rue...".
- Texte en FRANCAIS. Produits par ordre croissant de numero_ligne.
- tva_pct : taux EXACT de la colonne TVA. Jamais 20% par defaut.

DEVISE : Analyse tous les indices (ville, MF, symbole, langue).
  TND=3 dec (1 DT=1000 millimes). DZD=2 (DA). MAD=2 (DH). EUR=2 (€). USD=2 ($).
  SANITY CHECK PRIX : une baguette ← 0.2 DT (200 millimes), un cafe ← 1 DT, un stylo ← 1-5 DT,
  un pneu ← 50-300 DT, une piece auto ← 5-500 DT. Si le prix est 100x trop haut/bas →
  separateur decimal mal interprete, corrige automatiquement. Ex: 0.200 DT = 200 millimes.

CHAMPS : type_facture, etat(PAYE/IMPAYE/null), mode_reglement(Especes/Cheque/Virement), remarques(toujours entre guillemets), matricule_fiscal, societe_tel/email.
- Contacts multiples (tel, fax, email) : le principal dans le champ standard, les autres dans champs_supplementaires avec cles explicites ("gsm1", "fax", "email2").
- champs_supplementaires facture+client : TOUS les champs visibles non-couverts, noms EXACTS, ordre original. Les champs standards sont remplis EN PLUS. AUCUN champ perdu.

PRODUITS en TSV. La 1ere ligne = les EN-TETES EXACTS de la facture, EXACTEMENT dans le MEME ORDRE visible (gauche a droite). INTERDICTION de reordonner ou de grouper les colonnes "standards" ensemble.
- Les colonnes sont reconnues par leur NOM : designation, quantite, prix_u_ht, tva_pct, total_ht_ligne, total_ttc, remise_pct.
- numero_ligne : seulement si la facture a une colonne "N°", "Ligne" ou "#". Sinon, NE PAS l'ajouter.
- Separe par des tabulations. AUCUNE colonne perdue.

════════════════════════════════════════
PARTIE 2 — VERIFICATION
════════════════════════════════════════

Un SEUL element dans alertes. INTERDIT tout commentaire autre que le calcul.
VERIFIER : total_ht + montant_tva + timbre_fiscal ≈ net_a_payer (tolerance 1%).
- Si = ou champs manquants → success : "Calculs verifies. Aucune erreur detectee."
- Si ecart → erreur : "Erreur de calcul : Total attendu : X. Affiche : Y. Ecart : Z."
- Total HT ligne = quantite × prix_u_ht × (1 - remise_pct/100) si remise_pct > 0. Signaler toute ligne non-conforme.
- Colonnes TSV : chaque ligne de donnees doit avoir le meme nombre de colonnes que l'en-tete.
- Si total_ht_ligne fourni, verifier que la somme ≈ total_ht facture (tolerance 1%).
- Ne jamais signaler d'erreur si l'ecart est inferieur a 5% : les arrondis, centimes et taxes differentes sont normaux.

════════════════════════════════════════
FORMAT FINAL
════════════════════════════════════════

<YAML>
facture:
  type_facture:
  numero_facture:
  date: DD/MM/YYYY
  societe_nom:
  societe_adresse:
  societe_tel:
  societe_email:
  societe_matricule_fiscal:
  societe_rc:
  societe_ai:
  societe_compte_bancaire:
  total_ht: -9999
  montant_tva: -9999
  tva_pct: -9999
  timbre_fiscal: -9999
  net_a_payer: -9999
  montant_en_lettres:
  mode_reglement:
  etat:
  remarques: ""
  champs_supplementaires:
    "N Facture": FAC-2026-0001
    Date: 01/07/2026
    Client: NOM DU CLIENT
    MF: "1234567/A/M/000"
    Adresse: Adresse complete
    Tel: "71 000 000"
client:
  code_client:
  nom:
  prenom:
  telephone:
  adresse:
  matricule_fiscal:
  champs_supplementaires:
    Code client: CL-001
    Service Achats: M. Nom Prenom
    Contact: contact@email.tn
analyse:
  pays_detecte:
  ville_detecte:
  devise_detecte:
  alertes:
    - type: info
      message: Description claire et actionnable pour le comptable
</YAML>
<TSV>
Reference\tdesignation\tquantite\tprix_u_ht\ttva_pct\ttotal_ht_ligne\ttotal_ttc\tremise_pct\tFamille
REF-001\tStylo\t10\t2.5\t19\t25.0\t29.75\t0\tPapeterie
</TSV>
"""


    # ── Rotation : pioche aleatoire, 2 tentatives, mise de cote si echec ────
    response      = None
    api_utilisee  = None
    erreurs_api   = []

    for _ in range(len(GEMINI_API_KEYS)):
        with _key_lock:
            if not _available_keys:
                _available_keys = list(enumerate(GEMINI_API_KEYS))
                print(f"  [API] 🔄 Cycle terminé, toutes les clés sont de nouveau disponibles")
            idx = random.randrange(len(_available_keys))
            key_index, api_key = _available_keys.pop(idx)
        key_num = key_index + 1

        # 1re tentative avec cette cle
        try:
            print(f"\n  [API] Tentative avec la clé n°{key_num}...")
            if is_markdown:
                response = _appeler_gemini(api_key, [], prompt, text_content=markdown_text)
            else:
                response = _appeler_gemini(api_key, pages_data, prompt)
            api_utilisee = key_num
            print(f"  [API] ✅ Clé n°{key_num} a répondu avec succès.")
            break
        except Exception as e:
            msg = f"Clé n°{key_num} (1er essai) → {type(e).__name__}: {e}"
            erreurs_api.append(msg)
            print(f"  [API] ❌ {msg}")

            # 2e tentative avec la même clé
            try:
                print(f"  [API] ↻ 2e tentative avec la clé n°{key_num}...")
                if is_markdown:
                    response = _appeler_gemini(api_key, [], prompt, text_content=markdown_text)
                else:
                    response = _appeler_gemini(api_key, pages_data, prompt)
                api_utilisee = key_num
                print(f"  [API] ✅ Clé n°{key_num} a répondu au 2e essai.")
                break
            except Exception as e2:
                msg2 = f"Clé n°{key_num} (2e essai) → {type(e2).__name__}: {e2}"
                erreurs_api.append(msg2)
                print(f"  [API] ❌ {msg2}")
                print(f"  [API] ⛔ Clé n°{key_num} mise de côté pour ce cycle")
                # La clé reste retirée de _available (mise de côté)
                continue

    if response is None:
        detail = " | ".join(erreurs_api)
        raise RuntimeError(
            f"Toutes les clés API ont échoué ({len(GEMINI_API_KEYS)} clé(s) testée(s)). "
            f"Détails : {detail}"
        )


    usage = response.usage_metadata
    tokens_input    = usage.prompt_token_count
    tokens_output   = usage.candidates_token_count
    tokens_thinking = usage.total_token_count - tokens_input - tokens_output
    tokens_total    = usage.total_token_count

    cout_requete = (
        (tokens_input    / 1_000_000) * PRIX_INPUT_PAR_MILLION +
        (tokens_output   / 1_000_000) * PRIX_OUTPUT_PAR_MILLION +
        (tokens_thinking / 1_000_000) * PRIX_THINKING_PAR_MILLION
    )

    with compteur_lock:
        compteur = lire_compteur()
        compteur["requetes_jour"]   += 1
        compteur["requetes_minute"] += 1
        compteur["tokens_jour"]     += tokens_total
        compteur["cout_jour"]       += cout_requete
        sauver_compteur(compteur)

    text = response.text.strip()
    print("=== REPONSE GEMINI ===")
    print(text)
    print("=====================")

    if not text:
        raise ValueError("Gemini a retourne une reponse vide")

    yaml_text = ""
    tsv_text = ""

    import re
    bloc_yaml = re.search(r"<YAML>\s*(.*?)\s*</YAML>", text, re.DOTALL)
    bloc_tsv = re.search(r"<TSV>\s*(.*?)\s*</TSV>", text, re.DOTALL)

    if bloc_yaml and bloc_tsv:
        yaml_text = bloc_yaml.group(1).strip()
        tsv_text = bloc_tsv.group(1).strip()
    else:
        fallback = text
        if fallback.startswith("```"):
            fallback = fallback.split("```")[1]
            if fallback.startswith("yaml"):
                fallback = fallback[4:]
            fallback = fallback.strip()
        yaml_text = fallback

    if not yaml_text:
        raise ValueError("Bloc YAML vide dans la reponse Gemini")

    try:
        resultat = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        # Tentative de correction : mettre entre guillemets les valeurs contenant des ":"
        import re as _re
        lignes = yaml_text.split('\n')
        corrige = []
        for ligne in lignes:
            if ':' in ligne:
                partie_val = ligne.split(':', 1)[1].lstrip()
                if ':' in partie_val and not partie_val.startswith(('"', "'", '-')) and not partie_val.startswith('['):
                    # La valeur contient ":" sans guillemets → on quote toute la valeur
                    debut = ligne[:len(ligne)-len(partie_val)]
                    corrige.append(debut + '"' + partie_val + '"')
                else:
                    corrige.append(ligne)
            else:
                corrige.append(ligne)
        corrige = '\n'.join(corrige)
        try:
            resultat = yaml.safe_load(corrige)
            print("  [YAML] ✅ Corrigé automatiquement (valeurs quotees)")
        except yaml.YAMLError:
            print(f"  [YAML] ECHEC — contenu brut (premiers 500c) : {yaml_text[:500]}")
            raise ValueError(f"Reponse YAML invalide: {e}")

    if not isinstance(resultat, dict):
        raise ValueError(f"Reponse YAML invalide: attendu dict, obtenu {type(resultat).__name__}")

    if tsv_text:
        produits, col_order = _parser_tsv_produits(tsv_text)
        resultat["produits"] = produits
        resultat["col_order"] = col_order
    elif "produits" not in resultat:
        resultat["produits"] = []

    # ── Tokens et quotas (affiché en dernier dans le debug) ──────────────
    restant_jour   = QUOTA_JOUR   - compteur["requetes_jour"]
    restant_minute = QUOTA_MINUTE - compteur["requetes_minute"]

    # Récupère durée et tok/s attachés par _appeler_gemini
    _duree = getattr(response, "_perf_duree", None)
    _tok_s = getattr(response, "_perf_tok_s", None)

    print("=============================")
    print(f"   TOKENS CETTE REQUETE  (API clé n°{api_utilisee})")
    if len(erreurs_api) > 0:
        print(f"   ⚠️  {len(erreurs_api)} erreur(s) avant succès")
        for e in erreurs_api:
            print(f"      • {e}")
    print("----- CLÉS DISPONIBLES -----")
    with _key_lock:
        snapshot = _available_keys.copy()
    for i, k in enumerate(GEMINI_API_KEYS, 1):
        dispo = any(idx == i - 1 for idx, _ in snapshot)
        etat = "✅" if dispo else "⛔"
        nb = " (moi)" if i == api_utilisee else ""
        print(f"  Clé {i} {etat}{nb}")
    print("=============================")
    print(f"  Input    : {tokens_input:,} tokens")
    print(f"  Thinking : {tokens_thinking:,} tokens  (budget max: 5555)")
    print(f"  Output   : {tokens_output:,} tokens")
    print(f"  Total    : {tokens_total:,} tokens")
    if _duree is not None:
        print(f"  Temps    : {_duree:.2f}s  |  🚀 {_tok_s:.1f} tok/s")
    print(f"  Cout     : ${cout_requete:.6f}  ({cout_requete * 3.3:.6f} TND)")
    print("----- QUOTA MINUTE -----")
    print(f"  Utilises : {compteur['requetes_minute']} / {QUOTA_MINUTE}")
    print(f"  Restants : {restant_minute}")
    print("----- QUOTA JOUR -------")
    print(f"  Utilises : {compteur['requetes_jour']} / {QUOTA_JOUR}")
    print(f"  Restants : {restant_jour}")
    print(f"  Tokens   : {compteur['tokens_jour']:,}")
    print(f"  Cout     : ${compteur['cout_jour']:.6f}  ({compteur['cout_jour'] * 3.3:.6f} TND)")
    print("=============================\n")

    return resultat