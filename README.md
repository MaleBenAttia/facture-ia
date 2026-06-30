# 🧾 Facture-IA — Extraction intelligente de factures

Système complet et moderne pour scanner une facture (image ou PDF), en extraire les données structurées via l'Intelligence Artificielle (Gemini 2.5), et générer des exports formatés (Excel & PDF propres).

## 🚀 Fonctionnalités
- **Interface Premium** : Design "Light Aurora" avec verre dépoli (Glassmorphism), animations cinématiques (Scroll/Float), et indicateurs de traitement dynamiques.
- **Support Multi-format** : Import de factures aux formats JPG, PNG, WEBP et PDF (jusqu'à 15 Mo).
- **Extraction par IA (Google Gemini)** : Analyse instantanée des montants, TVA, numéros de factures, et détail ligne par ligne des pièces (références, quantités, prix unitaires).
- **Exports direct** : Téléchargement immédiat du tableau structuré au format Excel (`.xlsx`) ou PDF (`.pdf`).
- **Historique de Session** : Garde une trace visuelle de toutes les factures traitées durant votre session.
- **Prétraitement automatique des images** : Correction d'ombre, upscaling adaptatif, rehaussement de contraste (CLAHE), netteté optimisée avant envoi au LLM.
- **Aperçu instantané** : Dès l'upload, l'image prétraitée est affichée dans l'interface (PDF converti en image visible).
- **Débogage visuel** : L'image exacte envoyée à Gemini est sauvegardée dans `imagetraiter/`.
- **Parsing JSON robuste** : Extraction du bloc `{...}`, 2 passes de réparation automatique (virgules, guillemets, clés), fallback avec logs.
- **Vérification des prix par article et pays** : Le LLM valide la cohérence des montants (ex: stylo en Tunisie → max 5 TND, pneu → 50-300 TND) pour éviter les erreurs de virgule.

---

## 📂 Architecture du Projet

Le projet est divisé très proprement en deux parties distinctes :

```text
facture-ia/
│
├── frontend/               # 🎨 INTERFACE UTILISATEUR (React + Vite + Tailwind CSS)
│   ├── index.html          # Point d'entrée web
│   ├── package.json        # Dépendances Node.js (Framer Motion, Lucide, Tailwind...)
│   └── src/
│       ├── App.jsx         # Architecture principale et Layout (Thème clair + Aurora)
│       ├── main.jsx        # Point de montage React
│       ├── components/     # Composants UI modulaires (ScanZone, HeroScroll, Navbar...)
│       ├── config/         # Configuration du thème (theme.js)
│       └── lib/            # Utilitaires et appels API vers le Backend
│
├── .env                    # 🔐 Variables d'environnement (Clé API Gemini)
├── requirements.txt        # 📦 Dépendances Python (FastAPI, google-genai, etc.)
├── main.py                 # ⚙️ SERVEUR BACKEND (FastAPI - Routes et configuration)
├── gemini_extractor.py     # Logique métier : Appel à l'API Gemini 2.5 pour l'extraction
├── image_preprocessor.py   # 🖼️ Pipeline de prétraitement : ombre, upscale, CLAHE, sharpening
├── imagetraiter/           # 📁 Dossier de débogage : dernière image envoyée à Gemini
├── excel_generator.py      # Génération du fichier Excel via openpyxl
└── pdf_generator.py        # Génération du fichier PDF via reportlab
```

---

## 🛠️ Stack Technique

### Frontend
- **Framework :** React 18
- **Bundler :** Vite (HMR ultra rapide)
- **Style :** Tailwind CSS (Utilitaires) + CSS natif pour animations Aurora
- **Animations :** Framer Motion (Transitions complexes) + Animations CSS `@keyframes`
- **Icônes :** Lucide React

### Backend
- **Framework API :** FastAPI (Performant et typé)
- **Serveur WSGI :** Uvicorn
- **Modèle IA :** Google Gemini 2.5 (via le SDK `google-genai`)
- **Génération de fichiers :** `openpyxl` (Excel) et `reportlab` (PDF)
- **Prétraitement d'images :** `opencv-contrib-python-headless` (CLAHE, upscaling, ombre, netteté)
- **Extraction PDF :** `pymupdf` (conversion PDF → image, extraction page)

---

## 💻 Installation & Lancement

### 1. Pré-requis
- **Python 3.10+**
- **Node.js 18+**
- Une clé API Google Gemini valide.

### 2. Configuration du Backend (Python)
Depuis le dossier racine (`facture-ia`) :

```bash
# 1. Créer l'environnement virtuel (si pas déjà fait)
python -m venv venv

# 2. Activer l'environnement (Windows)
.\venv\Scripts\activate
# (Sur Mac/Linux : source venv/bin/activate)

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
# Copiez .env.example vers .env et ajoutez votre clé GEMINI_API_KEY
```

**Lancer le serveur API :**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# L'API tourne sur http://localhost:8000
```

### 3. Configuration du Frontend (Node.js)
Dans un nouveau terminal, depuis le dossier `frontend` :

```bash
# 1. Entrer dans le dossier
cd frontend

# 2. Installer les paquets
npm install

# 3. Lancer le serveur de développement
npm run dev
# L'interface tourne sur http://localhost:5173
```

---

## 🖼️ Pipeline de Prétraitement (image_preprocessor.py)

Avant d'envoyer une image à Gemini, elle passe par un pipeline adaptatif :

| Étape | Déclencheur | Description |
|---|---|---|
| **Détection PDF** | `content_type == "application/pdf"` | Distingue PDF scanné (image) vs natif (texte vectoriel) |
| **Extraction page** | PDF scanné | Rendu de la 1ʳᵉ page en image via PyMuPDF (300 DPI) |
| **Suppression d'ombre** | Écart-type du fond > 18 | Algorithme de dilation + médian + normalisation |
| **Upscaling** | < 0,5 MP → x4 ; < 2 MP → x2 | `cv2.INTER_CUBIC` + unsharp mask pour éviter les pixels |
| **CLAHE** | Toujours (sauf PDF natif) | Rehaussement de contraste local pour mieux lire les chiffres |
| **Filtre bilatéral** | Toujours | Réduction du bruit en préservant les contours |
| **Sharpening** | Toujours | Netteté renforcée (`unsharp mask`) |

L'image finale est encodée en PNG et envoyée à Gemini. Une copie est conservée dans `imagetraiter/derniere_image.png` pour déboguer.

---

## 🛡️ Corrections & Robustesse

| Correctif | Détail |
|---|---|
| **Parsing JSON tolérant** | Extraction du bloc `{…}`, correction virgules traînantes, guillemets simples, clés non quotées, `None`/`True` Python → `null`/`true`. |
| **Validation prix article + pays** | Le LLM vérifie que le montant est cohérent avec la désignation (stylo, pneu…) et le pays (TND, EUR…). Corrige automatiquement la virgule si 100x trop haut. |
| **Décodage image sécurisé** | `cv2.imdecode` → lève une erreur claire si l'image est corrompue (plus de crash silencieux). |
| **PDF niveaux de gris** | Gestion des pixmaps à 1 canal (niveaux de gris) dans `pdf_vers_images`. |
| **Validation PNG** | Vérification que `cv2.imencode` produit bien un PNG valide avant envoi à Gemini. |
| **Thread safety** | `threading.Lock()` sur les jobs partagés (`_jobs`, `_job_cancel`, compteur d'usage). |
| **Taille max upload** | Vérification 15 Mo côté backend (HTTP 413 si dépassé). |
| **Sécurité downloads** | Les endpoints `/excel/` et `/pdf/` vérifient que le fichier appartient à un job terminé. |

---

*Projet audité et nettoyé automatiquement. Aucun fichier parasite n'est présent dans l'architecture.*

---

## 🔄 Gestion des versions & Push sur GitHub

### 1. Premier envoi du projet (Initialisation)
Si vous venez de créer un dépôt vide sur votre compte GitHub (par exemple `facture-ia`) :

```bash
# 1. Lier le dépôt local à votre dépôt GitHub distant
git remote add origin https://github.com/MaleBenAttia/facture-ia.git

# 2. Envoyer la branche principale
git push -u origin main
```

### 2. Pousser vos modifications futures (Workflow classique)
À chaque fois que vous modifiez le code et souhaitez mettre à jour GitHub :

```bash
# 1. Voir la liste des fichiers modifiés
git status

# 2. Ajouter toutes les modifications au prochain commit (en respectant le .gitignore)
git add .

# 3. Créer un commit avec un message descriptif
git commit -m "api + annu"

# 4. Envoyer les modifications sur GitHub
git push origin main
```

---

## 🐛 Notes sur les Problèmes Réseaux Résolus (VPN / Mobile)

Lors du test de l'application via un réseau local (`192.168.x.x`) ou un VPN (comme **Tailscale**), deux problèmes techniques majeurs ont été identifiés et corrigés :

1. **La limitation des payloads sur Safari iOS (`ConnectionResetError`) :** 
   Safari (particulièrement sur iPhone) coupe brutalement les requêtes HTTP qui durent trop longtemps ou qui tentent de télécharger un fichier JSON trop lourd d'un seul coup. 
   **Solution implémentée :** Un système de *Polling en 3 étapes* (Lancement du job ➔ Demande légère du statut ➔ Récupération dédiée du gros JSON).
2. **Le blocage de `crypto.randomUUID()` hors HTTPS :**
   Les navigateurs modernes désactivent les API cryptographiques (`crypto.randomUUID`) lorsque la connexion n'est pas sécurisée (tout ce qui n'est pas `https://` ou `localhost`). L'application plantait silencieusement au moment de sauvegarder l'historique sur IP locale, déclenchant une fausse erreur de "Timeout serveur".
   **Solution implémentée :** Utilisation d'un générateur d'identifiant unique (UUID) alternatif fonctionnant sur les contextes non-sécurisés (HTTP simple).

---

## 🎨 Évolutions de l'Interface Utilisateur (UI)

- **Refonte de la page d'accueil :** Suppression de la section "Hero" (images de démonstration) pour afficher directement le cœur de l'application (le scanner) en plein écran, rendant l'outil plus immédiat et productif.
- **Background animé :** Mise en place d'un fond dynamique subtil (icônes flottantes) avec correction de l'ordre d'empilement (z-index) et ajustement des couleurs pour être parfaitement lisible sur le thème clair.
- **Nettoyage des assets :** Suppression de toutes les images statiques devenues obsolètes pour alléger le projet.
