# Facture-IA — Frontend

Frontend React (Vite + Tailwind) pour l'application Facture-IA.
Consomme le backend FastAPI existant (`/process`, `/excel/{sheet}`, `/pdf/{filename}`).

## Installation

```bash
cd frontend
npm install
```

## Configuration

Copiez `.env.example` en `.env` et ajustez si votre backend ne tourne pas sur
`http://localhost:8000` :

```bash
cp .env.example .env
```

## Développement

Lancez le backend FastAPI dans un terminal :

```bash
cd ..
venv\Scripts\activate
uvicorn main:app --reload
```

Puis le frontend dans un autre terminal :

```bash
cd frontend
npm run dev
```

Le site est servi sur http://localhost:5173 avec hot-reload, et appelle le
backend sur http://localhost:8000 (CORS déjà activé côté FastAPI).

## Build de production

```bash
npm run build
```

Génère le dossier `dist/`. Pour que FastAPI serve ce build au lieu de
l'ancien dossier `frontend/` statique, changez dans `main.py` :

```python
# avant
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

# après
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

Puis reconstruisez après chaque changement frontend (`npm run build`) avant
de relancer `uvicorn`.

## Personnalisation de la marque

Toute la marque (nom, slogan, couleurs, logo) se configure dans un seul
fichier : `src/config/theme.js`. Aucune couleur n'est codée en dur dans les
composants — tout lit ce fichier via des variables CSS injectées au
démarrage (`src/main.jsx`).

## Structure

```
src/
├── components/
│   ├── ui/              Composants de base (Button, Card, Badge, Toast)
│   ├── ScanZone.jsx      Zone d'upload/scan (élément signature de l'app)
│   ├── Hero.jsx          En-tête de page
│   ├── Navbar.jsx
│   ├── InvoicePreview.jsx  Affichage du résultat d'extraction
│   └── InvoiceHistory.jsx  Historique des factures de la session
├── lib/
│   ├── api.js            Tous les appels au backend FastAPI
│   └── utils.js           Formatage montants, classes Tailwind (cn)
├── config/
│   └── theme.js           Configuration de marque (couleurs, textes, logo)
├── App.jsx                 Orchestration du flux complet
├── main.jsx                 Point d'entrée + injection du thème
└── index.css                Tailwind + polices + classes utilitaires de thème
```

## Notes

- Les polices (Space Grotesk, Inter) sont auto-hébergées dans
  `public/fonts/` — pas de dépendance à Google Fonts en production.
- L'historique des factures est conservé en mémoire React pour la durée de
  la session (pas de persistance après rechargement de page).
