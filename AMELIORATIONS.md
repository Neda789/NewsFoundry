# NewsFoundry — Bilan critique et pistes d'amélioration

Ce document formule un regard critique sur la version actuelle de NewsFoundry, sur deux axes : la **qualité des résultats** retournés par l'agent, et la **fluidité des interactions** côté utilisateur. Chaque piste est justifiée par un exemple concret rencontré durant le développement, et accompagnée des grandes lignes de sa réalisation.

---

## 1. Fluidité des interactions

### 1.1 Absence de streaming des réponses

**Constat.** Le endpoint `POST /chats/{chat_id}/messages` attend que `agent.run()` se termine entièrement avant de renvoyer quoi que ce soit au frontend. L'utilisateur voit donc un écran figé (aucun indicateur de chargement dans la version actuelle) jusqu'à ce que la réponse complète arrive d'un coup.

**Exemple concret.** Lors des tests, une réponse portant sur plusieurs catégories d'actualité (TV, radio, podcasts, avec plusieurs sections Markdown) a mis plusieurs secondes à apparaître intégralement, sans aucun retour visuel entre-temps. Selon les repères d'utilisabilité couramment admis (cf. l'article NNGroup cité dans les ressources de l'étape), au-delà d'une seconde l'utilisateur perd le sentiment d'interagir directement avec le système, et au-delà de 10 secondes il risque de décrocher complètement — or une réponse de plusieurs centaines de mots générée token par token dépasse très régulièrement ce premier seuil.

**Piste d'amélioration.** Utiliser le mode streaming de PydanticAI (`agent.run_stream()`, qui expose les tokens au fur et à mesure de leur génération) et transmettre ce flux au frontend via une réponse HTTP en *chunked transfer* ou en *Server-Sent Events*. Côté frontend, remplacer l'appel `fetch` classique par une lecture incrémentale du flux (`ReadableStream`, ou `EventSource`) et mettre à jour `messages` au fur et à mesure que le texte arrive, comme le fait la quasi-totalité des interfaces de chat IA actuelles. Cela ne réduit pas le temps total de génération, mais réduit le temps perçu avant la première information utile à moins d'une seconde.

**Objectif mesurable.** Délai entre l'envoi du message et l'affichage du premier mot de la réponse inférieur à 1 seconde (seuil de "flux ininterrompu" selon NNGroup), contre plusieurs secondes actuellement pour une réponse complète.

### 1.2 Aucun indicateur de chargement visible pendant l'attente

**Constat.** L'état `sending` existe déjà côté frontend (désactive le champ de saisie), mais rien n'indique visuellement à l'utilisateur qu'une réponse est en cours de génération — pas de spinner, pas de "..." animé. Le bouton "Générer une revue de presse" a le même problème : aucun retour pendant les quelques secondes de génération.

**Exemple concret.** Pendant les tests de la revue de presse, l'absence de retour visuel donnait l'impression que le clic n'avait pas été pris en compte, avec un risque réel de double-clic (et donc de génération de deux revues de presse pour la même demande).

**Piste d'amélioration.** Ajouter un indicateur de chargement simple (icône animée ou texte "L'assistant rédige une réponse...") tant que `sending` est `true`, et désactiver le bouton de génération de revue de presse pendant l'appel réseau correspondant. ✅ *Mis en œuvre depuis la rédaction de ce bilan* : un indicateur "L'assistant rédige une réponse..." s'affiche désormais pendant l'attente, et le bouton de génération de revue de presse se désactive avec un texte "Génération en cours...". Reste à faire : remplacer `window.prompt`/`alert` — qui bloquent l'interface et ne sont pas personnalisables — par une vraie modale.

**Objectif mesurable.** 100 % des appels API lents (envoi de message, génération de revue) affichent un indicateur de chargement — objectif atteint pour ces deux fonctionnalités ; reste à étendre à une modale dédiée pour la revue de presse.

### 1.3 Pas de reprise automatique en cas d'erreur transitoire du fournisseur LLM

**Constat.** Le projet est passé de Google Gemini à Groq en cours de développement, après avoir rencontré de façon répétée, sur plusieurs jours distincts, des erreurs `503 UNAVAILABLE` ("high demand") ainsi que plusieurs dépréciations de modèles (404 "model no longer available"). Ces erreurs étaient **transitoires** dans le cas du 503 : une nouvelle tentative quelques secondes plus tard aurait souvent suffi. Or, dans le code actuel, la moindre erreur du fournisseur LLM remonte directement à l'utilisateur sous la forme d'un message générique ("Désolé, une erreur est survenue"), sans aucune tentative de nouvelle requête.

**Piste d'amélioration.** Ajouter une politique de nouvelle tentative avec backoff exponentiel (2–3 tentatives maximum, délai croissant) autour de l'appel `agent.run(...)`, par exemple avec la librairie `tenacity`, limitée aux erreurs reconnues comme transitoires (503, timeout réseau). Cela aurait évité une partie des interruptions de service rencontrées avec Gemini, sans attendre une migration complète de fournisseur. *Première étape déjà en place* : les erreurs du LLM sont désormais interceptées et renvoient une erreur `502` claire à l'utilisateur au lieu d'un crash brut ; la nouvelle tentative automatique reste à ajouter par-dessus.

**Objectif mesurable.** Réduire d'au moins 50 % le nombre d'échecs définitifs remontés à l'utilisateur pour une cause transitoire (503, timeout), mesuré sur les traces MLflow une fois la section 2.1 en place.

---

## 2. Qualité des résultats

### 2.1 Observabilité quasi nulle du comportement de l'agent

**Constat.** Le débogage des incidents LLM pendant ce projet (erreurs 503 répétées, changements de nom de modèle, puis 404 sur Groq) s'est fait entièrement manuellement : relecture de tracebacks collés dans un terminal, sans aucune donnée agrégée sur la fréquence des erreurs, le temps de réponse moyen, ou le nombre d'appels d'outils (`search_news`) par échange.

**Exemple concret.** Il a fallu plusieurs allers-retours, étalés sur plusieurs jours, pour identifier que le modèle Gemini utilisé n'était simplement plus disponible — une information qu'un tableau de bord de suivi des erreurs aurait fait apparaître immédiatement.

**Piste d'amélioration.** Intégrer MLflow Tracing à l'agent PydanticAI, via l'intégration officielle (`mlflow.pydantic_ai.autolog()`). Cela fournit, sans changement de logique métier, une trace détaillée de chaque appel : prompt envoyé, outils appelés, temps de réponse, tokens consommés, et erreurs levées. Utile en particulier pour objectiver la section suivante (temps de génération de la revue de presse) plutôt que de se fier à une impression.

**Objectif mesurable.** 100 % des appels à `agent.run()` et `press_review_agent.run()` visibles dans un dashboard de traces (latence, tokens, erreurs), contre 0 % actuellement.

### 2.2 Temps de génération de la revue de presse — non mesuré à ce stade

**Constat.** Aucune mesure précise du temps de génération d'une revue de presse n'a été réalisée à ce jour ; il s'agit d'une limite honnête de ce bilan plutôt que d'un résultat chiffré. On peut cependant raisonner sur ce qui influence ce temps : `generate_press_review` transmet tout l'historique de la discussion (`message_history`) en entrée de `press_review_agent.run(...)` — plus une discussion est longue (plus de messages, plus d'appels à `search_news` dans l'historique), plus le nombre de tokens envoyés au modèle est important, ce qui augmente mécaniquement le temps de traitement côté LLM.

**Piste d'amélioration.** Ajouter une instrumentation minimale (mesure du temps avant/après l'appel à `press_review_agent.run(...)`, journalisée ou — mieux — capturée via les traces MLflow de la section précédente), puis collecter ces temps sur un panel de discussions de longueurs variées pour objectiver la question posée par l'énoncé : le temps est-il satisfaisant, et comment varie-t-il avec la longueur de la discussion ? Si la mesure confirme une dégradation nette sur les discussions longues, une piste concrète serait de ne transmettre à l'agent que les N derniers messages pertinents (ou un résumé des échanges plus anciens) plutôt que l'historique complet.

**Objectif mesurable.** Temps de génération moyen mesuré sur au moins 10 discussions de longueurs variées, documenté dans ce fichier ; si la moyenne dépasse 10 secondes (seuil au-delà duquel l'utilisateur décroche selon NNGroup) sur les discussions longues, réduire ce temps d'au moins 30 % via la troncature de l'historique.

### 2.3 Pertinence limitée de la revue de presse sur une discussion à sujets multiples

**Constat.** La génération actuelle de la revue de presse (Étape 7) se base sur l'historique complet de la discussion, sans filtrage par pertinence : si une même discussion aborde plusieurs sujets distincts (ex. sport puis politique), rien n'empêche l'agent de mélanger des éléments non liés au sujet demandé, au-delà de la seule consigne donnée dans le prompt système de l'agent de revue de presse.

**Piste d'amélioration.** Une implémentation de RAG (Retrieval Augmented Generation) avec LlamaIndex a été prototypée durant ce projet (Étape 8, optionnelle) : un outil `load_article_content` permettant de charger le texte complet d'un article, indexé ensuite via des embeddings locaux (`HuggingFaceEmbedding`) pour ne retenir, au moment de la génération, que les articles réellement pertinents par rapport au sujet demandé. Cette implémentation a été mise de côté pour la livraison (voir `ARCHITECTURE.md`, section 4.6) en raison du poids des dépendances et des contraintes mémoire de l'hébergement actuel (plan gratuit Railway), mais le code existe et reste réactivable si l'application est hébergée sur un plan disposant de plus de ressources, ou si le modèle d'embedding est remplacé par un service externe léger plutôt qu'un modèle local.

**Objectif mesurable.** Sur un panel de discussions couvrant au moins deux sujets distincts, 0 article hors-sujet référencé dans la revue de presse générée (contre une présence possible aujourd'hui, non quantifiée faute de l'instrumentation décrite en 2.1).

### 2.4 Erreurs de l'API d'actualités invisibles en cas d'échec

**Constat.** Le tool `search_news` (et `get_top_news`) renvoie un message générique en français ("Aucun article n'a pu être trouvé...") dès que `WorldNewsAPIError` est levée, quelle qu'en soit la cause réelle (clé API invalide, quota dépassé, timeout réseau). Ce choix est volontaire pour l'agent — qui n'a pas besoin de ce détail — mais rien n'en garde non plus de trace côté serveur. Un cas réel rencontré durant le projet : une erreur de format sur `WORLDNEWS_API_KEY` dans le fichier `.env` (guillemets manquants) a nécessité plusieurs échanges pour être identifiée, faute de journal clair indiquant la cause exacte de l'échec.

**Piste d'amélioration.** Journaliser (côté serveur uniquement, via le module `logging` standard ou les traces MLflow déjà proposées en 2.1) l'exception complète à chaque échec d'appel à WorldNewsAPI, sans changer le message simplifié renvoyé à l'agent. Cela permettrait de distinguer immédiatement une panne du fournisseur externe d'une erreur de configuration locale.

**Objectif mesurable.** 100 % des échecs WorldNewsAPI journalisés avec leur cause exacte (code HTTP, type d'exception) ; temps de diagnostic d'une panne de configuration réduit à moins de 5 minutes, contre plusieurs jours pour l'incident `WORLDNEWS_API_KEY` rencontré durant ce projet.

---

## 3. Synthèse

| Piste | Axe | Effort estimé | Statut |
|---|---|---|---|
| Streaming des réponses | Fluidité | Moyen (backend + frontend) | À faire |
| Indicateur de chargement | Fluidité | Faible | ✅ Réalisé |
| Gestion propre des erreurs LLM (502 au lieu d'un crash) | Fluidité / fiabilité | Faible | ✅ Réalisé |
| Retry avec backoff sur le LLM | Fluidité / fiabilité | Faible | À faire |
| Tracing MLflow | Qualité / observabilité | Faible (intégration clé en main) | À faire |
| Mesure du temps de génération des revues | Qualité | Faible (dépend du tracing ci-dessus) | À faire |
| Réactivation du RAG (Étape 8) | Qualité | Déjà prototypé, dépend des ressources d'hébergement | Prototypé, non activé |
| Journalisation des erreurs WorldNewsAPI | Qualité / maintenabilité | Faible | À faire |

Les pistes à effort faible (indicateur de chargement, retry, tracing, journalisation) sont les plus immédiatement réalisables et apporteraient un gain disproportionné par rapport à leur coût d'implémentation, en particulier le tracing MLflow qui conditionne une mesure objective des autres pistes.
