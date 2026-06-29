from google import genai
from google.genai import types
import json, os
from datetime import date, datetime
from dotenv import load_dotenv
import mimetypes
load_dotenv()

QUOTA_JOUR   = 1500
QUOTA_MINUTE = 10
FICHIER      = "usage_counter.json"

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

def extraire_facture(image_path: str) -> dict:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    with open(image_path, "rb") as f:
        image_data = f.read()

    prompt = """
Tu es un expert-comptable senior et analyste financier specialise dans les factures du Maghreb, d'Europe et du Moyen-Orient.
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

CHAMPS A EXTRAIRE :
- type_facture : "Facture", "Proforma", "Avoir", "Bon de livraison", "Devis", etc.
- etat : "PAYE" ou "IMPAYE" ou null. Cherche tampons, cachets, mentions explicites.
- mode_reglement : "Especes", "Cheque", "Virement", "Traite", "Carte", etc.
- remarques : notes de bas de page, conditions de paiement ("paiement fin du mois", "sous 30 jours"),
  escomptes, penalites de retard, mentions legales. Concatene tout en une seule chaine. null si absent.
- matricule_fiscal : cherche "M.F", "MF", "NIF", "Matricule", "ICE", "SIRET", "SIREN".
- societe_tel / societe_email : Extraire le contact principal. S'il y a PLUSIEURS numéros ou emails, place les autres EXCLUSIVEMENT dans `champs_supplementaires` avec des clés explicites (ex: "gsm1", "gsm2", "fixe", "email2").
- champs_supplementaires : tout champ visible non couvert par le schema (dont les numéros/emails supplémentaires).

════════════════════════════════════════
PARTIE 2 — ANALYSE MATHEMATIQUE
════════════════════════════════════════

Apres extraction, effectue une verification STRICTEMENT MATHEMATIQUE. 
NE FAIS AUCUN COMMENTAIRE sur la conformite, les matricules, ou les noms generiques.

REGLE DES ALERTES :
1. Verifie l'addition : total_ht + montant_tva + timbre_fiscal ≈ net_a_payer (tolerance 1%)
2. Verifie les lignes : quantite * prix_u_ht * (1 - remise/100) * (1 + tva/100) ≈ total_ttc
3. Si TOUT EST CORRECT, genere EXACTEMENT UNE SEULE alerte de type "success" : 
   {"type": "success", "message": "Calculs vérifiés et corrects."}
4. S'il y a une ERREUR DE CALCUL, genere une alerte de type "erreur" tres courte (2 lignes max) indiquant la difference exacte. 
   Exemple : {"type": "erreur", "message": "Erreur Total : le calcul donne 101 DT mais la facture affiche 100 DT. Difference de 1 DT."}

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
      "champs_supplementaires": {}
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


    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_data, mime_type=mimetypes.guess_type(image_path)[0] or "image/png"),
            prompt
        ]
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

    compteur = lire_compteur()
    compteur["requetes_jour"]   += 1
    compteur["requetes_minute"] += 1
    compteur["tokens_jour"]     += tokens_total
    compteur["cout_jour"]       += cout_requete
    sauver_compteur(compteur)

    restant_jour   = QUOTA_JOUR   - compteur["requetes_jour"]
    restant_minute = QUOTA_MINUTE - compteur["requetes_minute"]

    print("\n=============================")
    print("   TOKENS CETTE REQUETE")
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

    return json.loads(text)