from google import genai
from google.genai import types
import json, os, threading, time
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

# ─── CLÉS API AVEC FALLBACK ────────────────────────────────────────────────
# Charge jusqu'à 6 clés (rétrocompatible : si KEY1 absent, tente GEMINI_API_KEY)
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

# ─── MODÈLES PRIORITAIRES ──────────────────────────────────────────────────
# Chaque clé peut avoir accès à des modèles différents selon son quota.
# On essaie dans cet ordre jusqu'à trouver un modèle qui répond.
MODELES = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-001"]

# Log de démarrage : confirme le chargement des clés (masquées)
print(f"[GEMINI] {len(GEMINI_API_KEYS)} clé(s) API chargée(s) :", end=" ")
for i, k in enumerate(GEMINI_API_KEYS, 1):
    print(f"Clé{i}=...{k[-6:]}", end="  ")
print()


PRIX_INPUT_PAR_MILLION    = 0.075
PRIX_OUTPUT_PAR_MILLION   = 0.30
PRIX_THINKING_PAR_MILLION = 0.075

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

def _appeler_gemini(api_key: str, pages_data: list, prompt: str, max_retries: int = 2):
    """
    Effectue un appel Gemini avec la clé fournie.
    Essaye chaque modèle dans MODELES jusqu'à en trouver un qui répond.
    pages_data: liste de tuples (image_data: bytes, mime_type: str) — une par page.
    Lève une exception si tous les modèles échouent.
    """
    if not api_key or not api_key.strip():
        raise ValueError(
            "api_key est vide ou None. Vérifiez GEMINI_API_KEY1..6 dans .env"
        )
    client = genai.Client(api_key=api_key.strip())
    contents = [types.Part.from_bytes(data=data, mime_type=mime)
                for data, mime in pages_data] + [prompt]

    dernier_erreur = None
    for modele in MODELES:
        for tentative in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=modele,
                    contents=contents
                )
                if modele != MODELES[0]:
                    print(f"  [API]  Modèle utilisé: {modele}")
                return response
            except Exception as e:
                dernier_erreur = e
                msg = str(e)
                est_503 = "503" in msg or "UNAVAILABLE" in msg
                est_429 = "429" in msg or "RESOURCE_EXHAUSTED" in msg
                est_image = "image" in msg.lower() and "not support" in msg.lower()

                if est_503 and tentative < max_retries:
                    attente = 2 ** tentative
                    print(f"  [API]  {modele} 503 (tentative {tentative}/{max_retries}) — dans {attente}s...")
                    time.sleep(attente)
                    continue
                if est_429 or est_image or tentative == max_retries:
                    break

    raise dernier_erreur or RuntimeError("Impossible d'atteindre Gemini.")


def extraire_facture(image_path: str, content_type: str = "image/png", cancel_event=None) -> dict:
    # ── Rechargement dynamique du .env (sécurité si le module est importé tôt)
    load_dotenv(dotenv_path=_ENV_PATH, override=True)

    # Relit les clés à chaque appel pour être sûr d'avoir les valeurs actuelles
    cles_actives = [
        k for k in [
            os.getenv("GEMINI_API_KEY1"),
            os.getenv("GEMINI_API_KEY2"),
            os.getenv("GEMINI_API_KEY3"),
            os.getenv("GEMINI_API_KEY4"),
            os.getenv("GEMINI_API_KEY5"),
            os.getenv("GEMINI_API_KEY6"),
            os.getenv("GEMINI_API_KEY"),
        ] if k and k.strip()
    ]
    if not cles_actives:
        raise EnvironmentError(
            f"Aucune clé API trouvée dans {_ENV_PATH}. "
            "Définissez GEMINI_API_KEY1..6 ou GEMINI_API_KEY."
        )
    print(f"  [API] {len(cles_actives)} clé(s) disponibles : "
          + "  ".join(f"Clé{i}=...{k[-6:]}" for i, k in enumerate(cles_actives, 1)))

    # ── Vérification annulation AVANT lecture du fichier et appel Gemini ─────
    if cancel_event and cancel_event.is_set():
        raise InterruptedError("Job annulé par l'utilisateur.")

    # ── Lecture et préprocessing de l'image (multi‑pages supporté) ────────

    with open(image_path, "rb") as f:
        file_bytes = f.read()
    print(f"  [PREPROC] Fichier original: {len(file_bytes)/1024:.1f} Ko, type: {content_type}")
    images_bgr = preparer_image_pour_llm(file_bytes, content_type)
    if not images_bgr:
        raise ValueError("Aucune image extraite du fichier")
    print(f"  [PREPROC] {len(images_bgr)} page(s) prétraitée(s), encodage PNG...")
    MAX_LONG_COTE = 1200
    pages_data = []
    for i, img_bgr in enumerate(images_bgr):
        h, w = img_bgr.shape[:2]
        if len(images_bgr) > 1 and max(w, h) > MAX_LONG_COTE:
            echelle = MAX_LONG_COTE / max(w, h)
            nouvelle = (int(w * echelle), int(h * echelle))
            img_bgr = cv2.resize(img_bgr, nouvelle, interpolation=cv2.INTER_AREA)
        success, buffer = cv2.imencode(".png", img_bgr)
        if not success or buffer is None or len(buffer) == 0:
            raise ValueError(f"Échec de l'encodage PNG pour la page {i+1}")
        image_data = buffer.tobytes()
        pages_data.append((image_data, "image/png"))
        print(f"  [PREPROC]   Page {i+1}: {img_bgr.shape[1]}x{img_bgr.shape[0]} px, {len(image_data)/1024:.1f} Ko")
    os.makedirs("imagetraiter", exist_ok=True)
    for i, (data, _) in enumerate(pages_data):
        with open(f"imagetraiter/page_{i+1}.png", "wb") as f:
            f.write(data)
    total_ko = sum(len(d) for d, _ in pages_data) / 1024
    print(f"  [PREPROC] {len(pages_data)} page(s) sauvegardée(s) dans imagetraiter/page_*.png")
    print(f"  [PREPROC] Envoi à Gemini: {len(pages_data)} page(s), {total_ko:.1f} Ko total")

    prompt = """
Tu es un expert-comptable senior et analyste financier specialise dans les factures du Maghreb, d'Europe et du Moyen-Orient.
Cette facture peut contenir plusieurs pages fournies ci-dessous. Utilise TOUTES les pages pour extraire les donnees.


Ton travail est d'extraire les donnees avec une precision maximale ET d'identifier tout element anormal ou suspect.

════════════════════════════════════════
PARTIE 1 — EXTRACTION DES DONNEES
════════════════════════════════════════

REGLES ABSOLUES :
- Reponds UNIQUEMENT avec du JSON brut valide. Zero markdown, zero backticks, zero commentaire.
- Champ absent ou illisible → null exactement.
- Valeur numerique absente → -9999. Ne jamais inventer.
- Valeur explicitement 0 dans la facture → 0.0.

DETECTION GEOGRAPHIQUE ET DEVISE (critique) :
Analyse tous les indices : langue, ville, code postal, mentions legales, matricule fiscal, symbole monetaire.
- Tunisie → TND (3 decimales, 1 DT = 1000 millimes. Ex: 78.411 = soixante-dix-huit dinars)
- Algerie → DZD (2 decimales. Cherche "DA", "DZD", wilaya, NIF algerien)
- Maroc → MAD (2 decimales. Cherche "MAD", "DH", "ICE", ville marocaine)
- France / zone Euro → EUR (2 decimales. Cherche "SIRET", "TVA FR", "€")
- USA / international → USD si indices clairs
- Si aucun indice : deduis depuis le format des montants (dernier separateur = decimale)
IMPORTANT : si devise TND, le point dans les montants est TOUJOURS decimal, jamais separateur de milliers.

VERIFICATION PRIX RAISONNABLE SELON ARTICLE ET PAYS (critique) :
- Analyse le designation de chaque ligne et verifie que le prix_u_ht est coherent avec l'article ET le pays.
  EXEMPLE : "Stylo" en Tunisie → 0.5 a 5 TND max. "Pneu" en Tunisie → 50 a 300 TND.
- Si le prix extrait est absurde pour l'article detecte, c'est que le separateur decimal est mal interprete.
  EXEMPLE : 7.411 TND sur une bouteille → 7.411 TND (correct, 7 dinars 411 millimes).
  7411 TND sur une bouteille → ABSURDE, le point est decimal : c'est 7.411 TND, pas 7411.
- TND (Tunisie) : 3 decimales. 1 DT = 1000 millimes. Ex: 7.411 = 7 dinars 411 millimes.
- DZD (Algerie) : 2 decimales. Ex: 150.50 DA.
- MAD (Maroc) : 2 decimales. Ex: 85.00 DH.
- EUR : 2 decimales. Ex: 12.99 €.
- Si le prix semble 100x ou 1000x trop eleve pour l'article, corrige automatiquement la position de la virgule.

CHAMPS A EXTRAIRE :
- type_facture : "Facture", "Proforma", "Avoir", "Bon de livraison", "Devis", etc.
- etat : "PAYE" ou "IMPAYE" ou null. Cherche tampons, cachets, mentions explicites.
- mode_reglement : "Especes", "Cheque", "Virement", "Traite", "Carte", etc.
- remarques : notes de bas de page, conditions de paiement ("paiement fin du mois", "sous 30 jours"),
  escomptes, penalites de retard, mentions legales. Concatene tout en une seule chaine. null si absent.
- matricule_fiscal : cherche "M.F", "MF", "NIF", "Matricule", "ICE", "SIRET", "SIREN".
- societe_tel / societe_email : Extraire le contact principal. S'il y a PLUSIEURS numéros ou emails, place les autres EXCLUSIVEMENT dans `champs_supplementaires` avec des clés explicites (ex: "gsm1", "gsm2", "fixe", "email2").
- champs_supplementaires : tout champ visible non couvert par le schema (dont les numéros/emails supplémentaires).

PRODUITS — 100% DYNAMIQUE VIA champs_supplementaires (obligatoire) :
- Les colonnes du tableau de facture changent selon le fournisseur.
- `champs_supplementaires` DOIT contenir TOUTES les colonnes visibles avec leurs noms EXACTS.
- Peu importe les colonnes : "Famille", "Catégorie", "Article", "Code", "Couleur", "Taille", "Unité", "Poids" → tout va dans `champs_supplementaires` avec le nom exact.
- Les champs standards (designation, quantite...) sont remplis par déduction.
- Mais AUCUNE colonne ne doit être perdue. Si la facture a 5 colonnes, `champs_supplementaires` a 5 entrées.

EXEMPLE :
  Facture avec colonnes : "Famille", "Article", "Qté", "PU", "Total"
  {
    "designation": "Stylo",
    "quantite": 10,
    "prix_u_ht": 2.5,
    "total_ht_ligne": 25.0,
    "champs_supplementaires": {
      "Famille": "Bureau",
      "Article": "Stylo",
      "Qté": 10,
      "PU": 2.5,
      "Total": 25.0
    }
  }

════════════════════════════════════════
PARTIE 2 — VERIFICATION MATHEMATIQUE
════════════════════════════════════════

REGLES ABSOLUES - NE PAS DEVIER :
- Tu dois retourner UN SEUL element dans le tableau "alertes". Pas deux, pas trois. UN SEUL.
- INTERDIT : commentaires sur les noms, matricules, conformite, TVA globale, labels ambigus, pays, devise, ou quoi que ce soit d'autre que les chiffres.
- AUTORISE UNIQUEMENT : verifier si total_ht + montant_tva + timbre_fiscal = net_a_payer (tolerance 1%).

CAS 1 - Tout est correct (ou champs manquants) :
  alertes: [{"type": "success", "message": "Calculs vérifiés."}]

CAS 2 - Erreur de calcul uniquement :
  alertes: [{"type": "erreur", "message": "Total attendu : X. Affiché : Y. Écart : Z."}]

FORMAT JSON FINAL :
{
  "facture": {
    "type_facture": null,
    "numero_facture": null,
    "date": "DD/MM/YYYY",
    "societe_nom": null,
    "societe_adresse": null,
    "societe_tel": null,
    "societe_email": null,
    "societe_matricule_fiscal": null,
    "societe_rc": null,
    "societe_ai": null,
    "societe_compte_bancaire": null,
    "total_ht": -9999,
    "montant_tva": -9999,
    "tva_pct": -9999,
    "timbre_fiscal": -9999,
    "net_a_payer": -9999,
    "montant_en_lettres": null,
    "mode_reglement": null,
    "etat": null,
    "remarques": null,
    "champs_supplementaires": {}
  },
  "client": {
    "code_client": null,
    "nom": null,
    "prenom": null,
    "telephone": null,
    "adresse": null,
    "matricule_fiscal": null,
    "champs_supplementaires": {}
  },
  "produits": [
    {
      "numero_ligne": 1,
      "designation": null,
      "quantite": -9999,
      "prix_u_ht": -9999,
      "tva_pct": -9999,
      "remise_pct": -9999,
      "total_ht_ligne": -9999,
      "total_ttc": -9999,
      "champs_supplementaires": {
        "Article": "valeur de la colonne Article",
        "Qté": 0
      }
    }
  ],
  "analyse": {
    "pays_detecte": null,
    "ville_detecte": null,
    "devise_detecte": null,
    "alertes": [
      {
        "type": "erreur | avertissement | info",
        "message": "Description claire et actionnable pour le comptable"
      }
    ]
  }
}
"""


    # ── Appel avec fallback entre les clés API ─────────────────────────────
    response      = None
    api_utilisee  = None
    erreurs_api   = []

    for index, api_key in enumerate(cles_actives, start=1):
        try:
            print(f"\n  [API] Tentative avec la clé n°{index}...")
            response     = _appeler_gemini(api_key, pages_data, prompt)
            api_utilisee = index
            print(f"  [API] ✅ Clé n°{index} a répondu avec succès.")
            break
        except Exception as e:
            msg = f"Clé n°{index} → {type(e).__name__}: {e}"
            erreurs_api.append(msg)
            print(f"  [API] ❌ {msg}")
            if index < len(cles_actives):
                print(f"  [API] Basculement sur la clé n°{index + 1}...")

    if response is None:
        detail = " | ".join(erreurs_api)
        raise RuntimeError(
            f"Toutes les clés API ont échoué ({len(cles_actives)} clé(s) testée(s)). "
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

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    if not text:
        raise ValueError("Gemini a retourne une reponse vide")

    # Extrait l'objet JSON entre { et } (ignore texte avant/apres)
    debut = text.find("{")
    fin = text.rfind("}")
    if debut != -1 and fin != -1 and fin > debut:
        text = text[debut:fin+1]
    text = text.strip()

    import re

    def reparer_json(t):
        t = re.sub(r",\s*([}\]])", r"\1", t)
        t = re.sub(r"'", '"', t)
        t = re.sub(r"\bNone\b", "null", t)
        t = re.sub(r"\bTrue\b", "true", t)
        t = re.sub(r"\bFalse\b", "false", t)
        t = re.sub(r"([{,])\s*(\w+)\s*:", r'\1"\2":', t)
        t = re.sub(r'"\s+', '"', t)
        return t

    for _ in range(2):
        try:
            resultat = json.loads(text)
            break
        except json.JSONDecodeError:
            text = reparer_json(text)
    else:
        print(f"  [JSON] ÉCHEC — contenu brut (premiers 500c) : {text[:500]}")
        raise ValueError(f"Réponse JSON invalide après réparation.")

    # ── Tokens et quotas (affiché en dernier dans le debug) ──────────────
    restant_jour   = QUOTA_JOUR   - compteur["requetes_jour"]
    restant_minute = QUOTA_MINUTE - compteur["requetes_minute"]

    print("\n=============================")
    print(f"   TOKENS CETTE REQUETE  (API clé n°{api_utilisee})")
    if len(erreurs_api) > 0:
        print(f"   ⚠️  {len(erreurs_api)} clé(s) ont échoué avant succès")
        for e in erreurs_api:
            print(f"      • {e}")
    print("=============================")
    print(f"  Input    : {tokens_input:,} tokens")
    print(f"  Thinking : {tokens_thinking:,} tokens")
    print(f"  Output   : {tokens_output:,} tokens")
    print(f"  Total    : {tokens_total:,} tokens")
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