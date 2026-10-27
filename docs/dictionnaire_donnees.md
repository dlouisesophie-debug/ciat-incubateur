---
title: "Base de données - Schéma et dictionnaire des données"
subtitle: "Plateforme de gestion de l'incubateur du CIAT"
---

# 1. Schéma relationnel

SQLite 3, clés étrangères activées. Le script de création est `schema.sql`.

```
users ──< projects >── users (mentor)
            │
            ├──< documents
            ├──< evaluations >── users (évaluateur)
            ├──< decisions   >── users (décideur)
            ├──< objectives ──< milestones
            ├──< comments    >── users (auteur)
            ├──< followups
            └──< ai_logs     >── users
```

Relations : un porteur possède plusieurs projets ; un projet a au plus un mentor ; une évaluation est unique par couple (projet, évaluateur) ; un suivi est unique par couple (projet, type).

# 2. Dictionnaire

## users - Comptes
| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | entier | clé primaire | Identifiant |
| email | texte | unique, obligatoire | Identifiant de connexion (minuscules) |
| name | texte | obligatoire | Nom complet |
| role | texte | porteur, evaluateur, mentor, coordonnateur | Rôle |
| password_hash | texte | obligatoire | Mot de passe haché (jamais en clair) |
| phone, organisation, bio | texte | facultatif | Informations de profil |
| created_at | texte | AAAA-MM-JJ HH:MM | Création du compte |

## projects - Projets
| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | entier | clé primaire | Identifiant |
| owner_id | entier | clé étrangère users | Porteur |
| title | texte | obligatoire | Titre |
| domain | texte | liste des 7 domaines du CIAT | Domaine d'application |
| stage | texte | liste (idée … premiers clients) | Stade d'avancement |
| team_size | entier | facultatif | Taille de l'équipe |
| summary, problem, solution, target | texte | champs obligatoires pour la soumission | Contenu du dossier |
| cohort | texte | ex. 2026-A | Cohorte, fixée à l'acceptation |
| status | texte | brouillon, a_completer, soumis, en_evaluation, liste_attente, refuse, incube, post_incubation | État dans le parcours |
| mentor_id | entier | clé étrangère users, nulle si non affecté | Mentor |
| created_at, submitted_at | texte | dates | Création, soumission |

## documents - Pièces jointes
`id`, `project_id` (FK), `doc_type` (fiche_projet, cv, budget, pitch, autre), `filename` (nom d'origine), `stored_name` (nom aléatoire sur disque), `uploaded_at`. Pièces obligatoires : fiche_projet, cv, budget.

## evaluations - Notes du comité
`id`, `project_id`, `evaluator_id`, cinq notes entières de 0 à 5 (`innovation`, `faisabilite`, `impact`, `equipe`, `marche`), `comment`, `created_at`. Unique (projet, évaluateur).

## decisions - Décisions motivées
`id`, `project_id`, `decision` (accepte, refuse, liste_attente), `motivation` (obligatoire, 20 caractères minimum), `decided_by`, `decided_at`.

## objectives - Objectifs
`id`, `project_id`, `label`, `indicator` (indicateur de réussite), `due_date`, `created_by`.

## milestones - Jalons
`id`, `project_id`, `objective_id` (facultatif), `title`, `description`, `due_date`, `status` (a_faire, en_cours, fait), `proof_name`, `proof_stored`, `completed_at`, `created_by`. Règle : le passage à « fait » exige une preuve.

## comments - Commentaires
`id`, `project_id`, `milestone_id` (facultatif), `author_id`, `body`, `created_at`.

## followups - Suivis à 3 et 6 mois
`id`, `project_id`, `kind` (3_mois, 6_mois), `due_date`, `done_date`, `status`, `notes`, `jobs` (emplois), `revenue` et `funding` (en FCFA). Créés automatiquement à l'acceptation.

## ai_logs - Journal de l'IA
`id`, `user_id`, `project_id`, `purpose` (pitch, swot, modele_eco, plan_action, compte_rendu), `mode` (claude ou gabarit), `output`, `created_at`.

# 3. Indicateurs

| Indicateur | Définition précise |
|---|---|
| Projets déposés | Nombre de lignes de `projects` (hors filtre éventuel) |
| Dossiers soumis | Projets dont le statut n'est ni brouillon ni à compléter |
| Dossiers décidés | Statuts liste_attente, refuse, incube, post_incubation |
| Taux d'acceptation | (incube + post_incubation) ÷ dossiers décidés |
| Note d'une évaluation | Somme des notes ÷ 5 × pondération : innovation 25, faisabilité 20, impact 25, équipe 15, marché 15 (total 100) |
| Note d'un projet | Moyenne des notes de ses évaluations |
| Jalon en retard | statut ≠ fait et échéance < date du jour |
| Taux d'avancement | Jalons « fait » ÷ jalons créés |

# 4. Jeu de données de démonstration

`python seed.py --reset` charge **20 comptes** et **14 projets** répartis sur les huit statuts, trois cohortes (2025-A, 2025-B, 2026-A) et les sept domaines, avec évaluations, décisions, objectifs, jalons (dont certains en retard) et suivis.

- **Nature :** entièrement fictif, généré par script (graine aléatoire fixe : résultats reproductibles). Aucun nom, chiffre ou entreprise ne correspond à des données réelles du CIAT.
- **Dates :** calculées par rapport au jour d'exécution pour que les alertes soient visibles.
- **Contrôles de qualité :** contraintes CHECK sur les valeurs énumérées et les notes (0 à 5), clés étrangères, unicité (e-mail, évaluation, suivi), validation des formulaires côté serveur.
- **Limites :** petit échantillon (14 projets) ; les moyennes et taux affichés illustrent le fonctionnement et n'ont aucune valeur statistique. Les montants de chiffre d'affaires et de financement sont tirés au hasard.
- **Données personnelles :** adresses en `@ciat.test`, mot de passe de démonstration commun à tous les comptes - **à supprimer avant toute utilisation réelle**.
