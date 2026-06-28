# 🧾 Facture-IA — Extraction intelligente de factures

Système complet et moderne pour scanner une facture (image ou PDF), en extraire les données structurées via l'Intelligence Artificielle (Gemini 2.5), et générer des exports formatés (Excel & PDF propres).

## 🚀 Fonctionnalités
- **Interface Premium** : Design "Light Aurora" avec verre dépoli (Glassmorphism), animations cinématiques (Scroll/Float), et indicateurs de traitement dynamiques.
- **Support Multi-format** : Import de factures aux formats JPG, PNG, WEBP et PDF (jusqu'à 15 Mo).
- **Extraction par IA (Google Gemini)** : Analyse instantanée des montants, TVA, numéros de factures, et détail ligne par ligne des pièces (références, quantités, prix unitaires).
- **Exports direct** : Téléchargement immédiat du tableau structuré au format Excel (`.xlsx`) ou PDF (`.pdf`).
- **Historique de Session** : Garde une trace visuelle de toutes les factures traitées durant votre session.

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
git commit -m "correction vpn"

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
