# NewsFoundry — Documentation technique

> Assistant IA de revue de presse. Projet réalisé dans le cadre du cours **P14DevIA**.

Cette documentation a pour but de permettre à une nouvelle personne (ou à vous-même, plus tard) de comprendre rapidement comment le projet est construit, pourquoi certains choix ont été faits, et comment le faire tourner et le tester.

---

## 1. Présentation générale

NewsFoundry est une application web qui permet à un utilisateur de discuter avec un agent IA au sujet de l'actualité récente, et de générer à partir de cette discussion une **revue de presse** synthétique sur un sujet donné.

L'application est composée de deux parties déployées séparément :

- un **backend** (API) en Python, déployé sur **Railway** avec une base de données PostgreSQL ;
- un **frontend** en Next.js, déployé sur **Vercel**.

---

## 2. Architecture globale

```
Utilisateur
   │
   ▼
Frontend (Next.js, Vercel)
   │  appels HTTP (fetch + JWT)
   ▼
Backend (FastAPI, Railway)
   │               │
   ▼               ▼
PostgreSQL     Services externes
(Railway)      ├── World News API (actualités)
               └── Groq (LLM — agent PydanticAI)
```

- Le **frontend** ne contient aucune logique métier : il affiche les données et appelle l'API backend.
- Le **backend** gère l'authentification, la persistance des discussions, et orchestre les appels à l'agent IA (PydanticAI) et à l'API d'actualités (World News API).
- L'**agent IA** utilise des *tools* (function calling) pour aller chercher de l'actualité en temps réel plutôt que de se baser uniquement sur ses connaissances internes.

---

## 3. Structure des dossiers

```
P14DevIA-main/
├── backend/
│   ├── src/
│   │   ├── main.py              # Point d'entrée FastAPI, middleware CORS
│   │   ├── database.py          # Connexion SQLModel / PostgreSQL (engine)
│   │   ├── models.py            # Modèles SQLModel (User, Chat)
│   │   ├── routers/
│   │   │   ├── auth.py          # Inscription / connexion / JWT
│   │   │   └── chat.py          # Discussions, agent PydanticAI, revue de presse
│   │   └── services/
│   │       └── worldnews.py     # Client HTTP pour World News API
│   ├── tests/
│   │   ├── conftest.py          # Fixtures pytest (DB de test, mocks)
│   │   └── test_chat.py         # Tests du routeur chat
│   ├── create_test_user.py      # Script utilitaire pour créer un utilisateur de test
│   ├── pyproject.toml           # Dépendances (gérées avec uv)
│   └── .env                     # Variables d'environnement (non versionné)
│
├── frontend/
│   └── src/
│       └── app/
│           ├── page.tsx         # Page principale (chat + revue de presse)
│           ├── layout.tsx
│           ├── globals.css
│           └── login/           # Page de connexion
│
├── .github/
│   └── workflows/
│       └── backend-tests.yml    # CI : exécution des tests backend à chaque push
│
└── .gitignore
```

---

## 4. Choix techniques et justifications

### 4.1 Backend : FastAPI + SQLModel + PostgreSQL

- **FastAPI** a été choisi pour sa simplicité, sa validation automatique des données via Pydantic, et sa documentation interactive générée automatiquement (Swagger UI sur `/docs`), très utile pour tester les endpoints pendant le développement.
- **SQLModel** combine Pydantic et SQLAlchemy : les mêmes classes servent à la fois de schéma de validation et de modèle de base de données, ce qui évite de dupliquer les définitions.
- **PostgreSQL** est utilisé en production (hébergé par Railway) et en local pour rester cohérent entre les deux environnements.

### 4.2 Authentification : JWT + bcrypt

- Les mots de passe sont hashés avec **bcrypt** avant d'être stockés (jamais en clair).
- L'authentification utilise des **tokens JWT** (librairie `pyjwt`) : après connexion, le frontend stocke le token et l'envoie dans l'en-tête `Authorization: Bearer <token>` à chaque requête, ce qui évite d'avoir à gérer des sessions côté serveur.

### 4.3 Agent IA : PydanticAI

**PydanticAI** a été choisi plutôt que d'appeler directement l'API du fournisseur LLM, pour plusieurs raisons :

- il permet de définir des **tools** (`@agent.tool` / `@agent.tool_plain`) que l'agent peut appeler lui-même pendant la conversation (ex. rechercher de l'actualité) ;
- il permet de définir une **sortie structurée** (`output_type=`) avec un modèle Pydantic, ce qui garantit un format de réponse fiable (utilisé pour la génération de la revue de presse) ;
- il est indépendant du fournisseur de modèle : changer de LLM revient à changer une simple chaîne de caractères (`"groq:..."`, `"google:..."`, etc.) sans réécrire la logique métier — ce qui s'est avéré très utile (voir section suivante).

Deux agents distincts sont utilisés :

- `agent` : l'agent conversationnel du chat, avec le tool `search_news` (et optionnellement `load_article_content`, voir section 4.6).
- `press_review_agent` : un agent séparé, dédié à la génération de la revue de presse, avec une sortie structurée (`title`, `synthese_generale`, `syntheses_articles`).

Les séparer permet d'avoir un *system prompt* et un comportement différents pour chaque usage, sans qu'ils interfèrent.

### 4.4 Fournisseur LLM : Groq (et non Gemini)

Le projet a d'abord utilisé **Google Gemini**, mais celui-ci s'est révélé peu fiable en pratique sur plusieurs jours d'utilisation :

- erreurs répétées `503 UNAVAILABLE` ("high demand"), y compris sur un compte gratuit ;
- plusieurs modèles dépréciés / renommés en cours de projet (`gemini-3.6-flash`, puis `gemini-2.5-flash`, puis `gemini-3.8-flash`), chacun nécessitant une migration.

Le projet est donc passé à **Groq** (librairie `pydantic-ai-slim[groq]`), pour les raisons suivantes :

- **gratuit sans carte bancaire**, contrainte importante pour ce projet ;
- infrastructure dédiée à l'inférence rapide, peu de problèmes de disponibilité rencontrés en pratique ;
- compatible nativement avec PydanticAI (changement d'une seule variable d'environnement, `CHAT_MODEL`).

Le modèle utilisé est configurable via la variable d'environnement `CHAT_MODEL` (ex. `groq:openai/gpt-oss-120b`), ce qui permet de changer de modèle sans modifier le code — précaution directement motivée par les changements de modèles subis avec Gemini.

### 4.5 Source d'actualité : World News API

**World News API** fournit les données d'actualité utilisées par l'agent, via deux endpoints :

- `/news/top` : digest de l'actualité du jour, injecté dans le *system prompt* de l'agent au démarrage d'une discussion ;
- `/search-news` : recherche d'articles sur un sujet précis, exposée à l'agent comme le tool `search_news`, pour qu'il puisse approfondir un sujet à la demande de l'utilisateur plutôt que de se limiter au digest du jour.

### 4.6 RAG sur le contenu des articles — non implémenté (Étape 8, optionnelle)

L'étape optionnelle de RAG (*Retrieval Augmented Generation*) avec **LlamaIndex** a été évaluée mais volontairement **non intégrée** à la version livrée, pour les raisons suivantes :

- cette fonctionnalité était explicitement marquée comme optionnelle dans les consignes du projet ;
- elle aurait nécessité des dépendances lourdes (`llama-index`, `sentence-transformers`, `torch`) pour un modèle d'embedding local, ce qui augmente sensiblement le temps de build et la consommation mémoire au runtime ;
- l'environnement de déploiement du backend (plan gratuit Railway) dispose de ressources limitées, et le risque de faire échouer le déploiement en production dépassait le bénéfice attendu pour ce projet ;
- la revue de presse actuelle (Étape 7), basée sur les titres et résumés obtenus via `search_news`, répond déjà au besoin principal sans cette complexité supplémentaire.

La génération de la revue de presse se base donc sur l'historique complet de la discussion, sans étape de recherche par similarité supplémentaire.

### 4.7 Frontend : Next.js + Tailwind CSS

- **Next.js (App Router, TypeScript)** pour une structure de projet standard et un bon support du rendu côté client pour une application très interactive (chat en temps réel).
- **Tailwind CSS** pour le style, avec le plugin `@tailwindcss/typography` pour le rendu des réponses de l'agent.
- Les réponses de l'agent étant écrites en Markdown, elles sont rendues avec **`react-markdown`** (+ `remark-gfm` pour les listes, tableaux, etc.) plutôt qu'affichées en texte brut.
- L'état de l'application (discussions, messages) est géré avec les hooks React standards (`useState`, `useEffect`, `useCallback`), sans librairie de gestion d'état supplémentaire, le besoin ne le justifiant pas à cette échelle.

### 4.8 Déploiement : Vercel + Railway

- Le **frontend** est déployé sur **Vercel**, qui offre un déploiement automatique à chaque push sur `main` et une intégration native avec Next.js.
  URL de production : [https://news-foundry-rose.vercel.app/](https://news-foundry-rose.vercel.app/)
- Le **backend et la base de données** sont déployés sur **Railway**, qui permet d'héberger à la fois l'API et une instance PostgreSQL managée dans le même projet.
- Les deux plateformes se redéploient automatiquement sur chaque push vers la branche `main` du dépôt GitHub. Les secrets (clés d'API, `CHAT_MODEL`, `GROQ_API_KEY`, `DATABASE_URL`, etc.) sont configurés séparément dans les variables d'environnement de chaque plateforme — jamais commités dans le dépôt (voir `.gitignore`).

### 4.9 Erreurs retournées par l'API backend

L'API utilise `HTTPException` de FastAPI pour renvoyer des erreurs explicites plutôt que de laisser remonter des erreurs serveur brutes.

| Endpoint | Code | Cas | Détail renvoyé |
|---|---|---|---|
| `POST /auth/register` | 400 | Email déjà utilisé | Message explicite indiquant que le compte existe déjà |
| `POST /auth/login` | 401 | Email ou mot de passe incorrect | Identifiants invalides |
| Tous les endpoints protégés | 401 | Token JWT manquant, invalide ou expiré | Authentification requise |
| `GET /chats/{chat_id}` | 404 | Discussion inexistante, ou appartenant à un autre utilisateur | `Discussion introuvable` |
| `POST /chats/{chat_id}/messages` | 404 | Idem (discussion non trouvée / non possédée) | `Discussion introuvable` |
| `POST /chats/{chat_id}/press-review` | 404 | Idem | `Discussion introuvable` |
| `POST /chats/{chat_id}/press-review` | 400 | Revue de presse demandée sur une discussion sans aucun message | `Cette discussion ne contient encore aucun message.` |
| `POST /chats/{chat_id}/messages` | 502 | Le fournisseur LLM (Groq) échoue ou est indisponible | `Le service de generation de reponse est momentanement indisponible. Reessayez dans quelques instants.` |
| `POST /chats/{chat_id}/press-review` | 502 | Idem, pendant la génération de la revue de presse | Même message |

> Le choix du code `404` (plutôt que `403 Forbidden`) pour une discussion appartenant à un autre utilisateur est volontaire : cela évite de confirmer à un utilisateur non autorisé que la ressource existe, en ne révélant pas la distinction entre "n'existe pas" et "ne vous appartient pas".

Les erreurs provenant de WorldNewsAPI (clé invalide, quota dépassé, timeout) ne sont pas remontées telles quelles à l'utilisateur : elles sont interceptées (`WorldNewsAPIError`) et transformées en un message neutre renvoyé à l'agent conversationnel, qui l'intègre naturellement dans sa réponse plutôt que de faire échouer toute la requête.

### 4.10 Choix des prompts

- **`BASE_SYSTEM_PROMPT` répond en français "sauf si l'utilisateur écrit dans une autre langue"** : l'application cible un public francophone (actualité française), mais cette règle évite de forcer une réponse en français à un utilisateur qui écrirait spontanément dans une autre langue.
- **Instruction explicite d'utiliser du Markdown** (titres, listes, gras) dans le prompt système : ce choix est fait en cohérence directe avec le frontend, qui rend ces réponses avec `react-markdown` (section 4.7) — le prompt et le rendu sont pensés ensemble, l'un n'a de sens qu'avec l'autre.
- **Le résumé d'actualité (digest) n'intègre que le titre et le résumé de chaque article, jamais le texte complet** : un prompt système trop long consomme plus de tokens à chaque message (donc plus de latence et, chez un fournisseur payant, plus de coût), pour un bénéfice marginal sur la qualité des réponses générales.
- **Le prompt système est généré une seule fois à la création de la discussion, puis figé dans `Chat.system_prompt`** : cela garantit que le contexte d'actualité ne change pas au milieu d'une conversation déjà entamée (cohérence), et évite un appel supplémentaire à WorldNewsAPI à chaque message.
- **La description du tool `search_news` précise explicitement quand l'utiliser** ("quand l'utilisateur demande plus de détails...") plutôt que de laisser l'agent libre de l'appeler à sa discrétion : cela limite les appels inutiles à WorldNewsAPI (latence, quota) sur des messages qui n'en ont pas besoin.
- **La génération de la revue de presse utilise un agent séparé (`press_review_agent`) avec une sortie structurée (`output_type=PressReviewOutput`)**, plutôt que de réutiliser l'agent de chat : la revue de presse a besoin d'un format de sortie fiable et prévisible (titre, synthèse, liste d'articles) pour être stockée et affichée côté frontend, ce qu'une réponse de chat en texte libre ne garantit pas.
- **Le prompt de revue de presse demande explicitement d'ignorer les parties de la discussion non liées au sujet demandé** : ajouté après avoir constaté qu'une discussion abordant plusieurs sujets pouvait, sans cette consigne, produire une revue mélangeant des éléments hors-sujet (voir aussi `AMELIORATIONS.md`, section 2.3, sur les limites de cette approche sans RAG).

---

## 5. Lancer le projet en local

### Backend

```bash
cd backend
uv run --env-file .env uvicorn src.main:app --reload
```

L'API est alors accessible sur `http://localhost:8000`, avec la documentation interactive sur `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm run dev
```

L'application est alors accessible sur `http://localhost:3000`.

---

## 6. Lancer les tests

Les tests backend utilisent `pytest`, avec le modèle `TestModel` de PydanticAI pour simuler les réponses de l'agent IA sans appeler de vraie API LLM (rapide, gratuit, déterministe), et des fixtures qui simulent les réponses de World News API.

```bash
cd backend
uv run pytest
```

Ces tests sont également exécutés automatiquement à chaque push via GitHub Actions (`.github/workflows/backend-tests.yml`).

---

## 7. Variables d'environnement (backend)

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | URL de connexion PostgreSQL |
| `JWT_SECRET` | Clé secrète pour signer les tokens JWT |
| `GROQ_API_KEY` | Clé d'API Groq (fournisseur du LLM) |
| `CHAT_MODEL` | Modèle utilisé par l'agent, ex. `groq:openai/gpt-oss-120b` |
| `WORLDNEWS_API_KEY` | Clé d'API World News API |

> Ces variables sont définies dans `backend/.env` en local (fichier non versionné, exclu via `.gitignore`), et dans l'onglet *Variables* du service correspondant sur Railway en production.
