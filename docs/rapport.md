---
title: "Rapport - Plateforme de gestion de l'incubateur du CIAT"
subtitle: "Évaluation pratique du cours d'intelligence artificielle générative - ISEP Amadou Trawaré de Diamniadio"
author: "[Noms des trois membres de l'équipe]"
date: "Octobre 2026"
---

# 1. Contexte et besoin

Le CIAT accueille des porteurs de projets et les accompagne dans son incubateur. Ce suivi implique plusieurs acteurs et plusieurs étapes (dépôt, sélection, mentorat, suivi). Sans outil dédié, l'information se disperse entre messages, tableurs et documents, ce qui rend difficiles la traçabilité des décisions, la détection des retards et le pilotage.

Nous avons choisi le **Projet 2 : plateforme de gestion de l'incubateur**. Son objectif : gérer le parcours complet d'un projet, de la soumission de l'idée au suivi après incubation, avec un tableau de bord pour le coordonnateur.

> **À compléter :** résultats des entretiens menés avec au moins deux utilisateurs (nom, rôle, date, constats), voir le cahier des charges, section 3.

# 2. Démarche et organisation

| Membre | Profil | Contribution |
|---|---|---|
| [Nom 1] | Développeur | [à compléter] |
| [Nom 2] | Data analyst | [à compléter] |
| [Nom 3] | Infographe | [à compléter] |

Étapes : analyse du besoin, cahier des charges, modèle de données, maquettes, développement, jeu de données, intégration de l'IA, tests, déploiement, documentation.

# 3. Solution réalisée

## 3.1 Fonctionnalités

- **Comptes et droits** : quatre rôles (porteur, membre du comité, mentor, coordonnateur) ; chaque page et chaque fichier est protégé par un contrôle d'accès.
- **Dépôt et complétude** : le dossier compte huit champs et trois pièces obligatoires ; la soumission est bloquée tant que la complétude n'atteint pas 100 %.
- **Sélection** : grille de cinq critères pondérés (innovation 25, faisabilité 20, impact 25, équipe 15, marché 15), note sur 100 ; au moins deux évaluations avant décision ; décision motivée (20 caractères minimum) communiquée au porteur.
- **Accompagnement** : affectation d'un mentor, objectifs avec indicateur, jalons avec échéance ; un jalon ne peut être déclaré « fait » sans preuve jointe ; commentaires.
- **Alertes** : jalons en retard et suivis à réaliser, avec compteur dans le menu.
- **Suivi à 3 et 6 mois** : créés automatiquement à l'acceptation ; emplois, chiffre d'affaires et financements.
- **Pilotage** : tableau de bord filtrable (cohorte, domaine), exports Excel (4 feuilles), synthèse PDF et compte rendu PDF par projet.

## 3.2 Architecture et choix techniques

| Élément | Choix | Justification |
|---|---|---|
| Langage et cadre | Python, Flask | Rapide à développer, lisible, bien documenté |
| Base de données | SQLite | Persistante, sans serveur, adaptée à un incubateur de petite taille ; migration possible vers PostgreSQL |
| Interface | HTML rendu côté serveur, CSS responsive | Sans dépendance externe, léger, accessible |
| Exports | openpyxl, reportlab | Excel et PDF générés côté serveur |
| Déploiement | gunicorn, Dockerfile, `render.yaml` | Hébergement gratuit possible |

Le code est organisé en `app.py` (routes et règles métier), `ai.py`, `exports.py`, `schema.sql`, `seed.py`, `templates/`, `static/`, `tests/`.

## 3.3 Sécurité

Mots de passe hachés ; jeton CSRF sur tous les formulaires ; requêtes SQL paramétrées ; échappement automatique des gabarits ; politique CSP et en-têtes de protection ; cookies HttpOnly et SameSite ; fichiers renommés avec un nom aléatoire, extensions filtrées, taille limitée à 5 Mo ; le rôle choisi à l'inscription est toujours « porteur ».

# 4. Intégration de l'IA générative

**Fonction :** assistant d'écriture (pitch, SWOT, modèle économique, plan d'action, brouillon de compte rendu) à partir du dossier.

**Justification :** les porteurs d'idées ont souvent du mal à structurer un pitch ou une analyse SWOT ; le mentor gagne du temps sur les comptes rendus.

**Garde-fous (vérification humaine)** :

1. consigne donnée au modèle de ne rien inventer et d'écrire « [à compléter] » en cas d'information manquante ;
2. texte affiché comme brouillon, jamais enregistré automatiquement dans le dossier ;
3. journalisation de chaque génération (table `ai_logs`) ;
4. repli sur des gabarits locaux si aucune clé API n'est configurée, ce qui garantit une démonstration sans réseau ;
5. l'assistant n'est pas ouvert au comité d'évaluation, pour ne pas influencer les notes.

L'IA a aussi servi à produire le code et la documentation. Le journal des prompts consigne les corrections : par exemple, un test généré attendait une note de 80 là où le calcul correct donne 82 ; l'application était juste, le test a été corrigé.

# 5. Données et indicateurs

Le jeu de données de démonstration (20 comptes, 14 projets, trois cohortes, sept domaines) est **fictif** et documenté dans le dictionnaire de données. Les indicateurs sont définis précisément (taux d'acceptation = acceptés ÷ dossiers décidés ; jalon en retard = non réalisé et échéance dépassée ; etc.).

> **À compléter par le data analyst après la dernière exécution :** lecture des indicateurs affichés par le tableau de bord (cohorte la plus acceptée, domaines les plus représentés, taux de jalons réalisés) et deux ou trois recommandations. Avec 14 projets fictifs, ces chiffres illustrent le fonctionnement mais ne permettent aucune conclusion statistique ; il faut le dire explicitement.

**Pistes de recommandations à confirmer avec de vraies données :** suivre le délai entre soumission et décision ; fixer un seuil de note indicatif ; relancer les porteurs dont les jalons dépassent l'échéance depuis plus de deux semaines.

# 6. Tests

18 tests automatiques (`python -m unittest discover -s tests -v`), tous réussis lors de la dernière exécution. Ils couvrent : connexion et mauvais mot de passe, CSRF, redirection des pages protégées, attribution du rôle à l'inscription, droits par rôle, accès aux fichiers, parcours complet (création, complétude, pièces, soumission, évaluations, décision, mentor, objectifs, jalons, preuve, alertes), calcul de la note pondérée, tableau de bord, exports PDF et Excel, assistant IA, injection SQL, injection de script.

| Anomalie | Gravité | État |
|---|---|---|
| Test mal calibré (note attendue 80 au lieu de 82) | Faible | Corrigé |
| Double import du module à cause du lancement par `python app.py` | Moyenne | Corrigé (lancement par `run.py`) |
| [anomalies relevées lors des tests manuels sur téléphone] | [à compléter] | [à compléter] |

Des tests manuels sur ordinateur et téléphone, ainsi qu'un test de l'assistant avec une vraie clé API, restent à consigner par l'équipe.

# 7. Déploiement

Lien de la solution : **[à compléter après déploiement]**. Procédure dans le fichier `README.md` (Render, Docker ou lancement local). Comptes de démonstration dans le guide utilisateur.

# 8. Limites et perspectives

**Limites :** pas de notification par courriel ni de réinitialisation de mot de passe ; pas de limitation des tentatives de connexion ; fichiers stockés localement (prévoir un disque persistant) ; décision prise par le coordonnateur après évaluations individuelles, sans vote en séance ; données de démonstration fictives ; pas de test de charge.

**Perspectives :** notifications par courriel, réinitialisation de mot de passe, authentification à deux facteurs, PostgreSQL et stockage objet, recherche dans les documents du CIAT pour l'assistant, graphiques interactifs, intégration avec le portail du CIAT (Projet 1).
