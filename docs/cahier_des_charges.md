---
title: "Cahier des charges - Plateforme de gestion de l'incubateur du CIAT"
subtitle: "Évaluation pratique en IA générative - Projet 2 - ISEP Amadou Trawaré de Diamniadio"
---

# 1. Contexte

Le Centre d'Innovation, d'Application et de Transfert (CIAT) de l'ISEP Amadou Trawaré accueille des porteurs de projets et les accompagne au sein de son incubateur. Le suivi d'un projet, de la soumission de l'idée jusqu'à l'après-incubation, mobilise plusieurs acteurs (porteur, comité de sélection, mentor, coordonnateur).

> **À valider avec le CIAT.** Les constats ci-dessous décrivent les difficultés *typiques* d'un suivi manuel (courriels, tableurs, documents dispersés). Ils doivent être confirmés par les entretiens décrits à la section 3 avant la remise du cahier des charges.

**Besoin identifié :** disposer d'un outil unique qui trace le parcours complet d'un projet, rend la sélection transparente et reproductible (grille d'évaluation, décision motivée) et alerte sur les retards, afin que le coordonnateur pilote l'incubateur avec des données fiables.

# 2. Objectifs

1. Centraliser le dossier, les pièces et l'historique de chaque projet.
2. Standardiser l'évaluation par une grille pondérée et exiger une décision motivée.
3. Organiser l'accompagnement : mentor, objectifs, jalons, preuves, commentaires.
4. Détecter automatiquement les retards et les suivis à réaliser (3 et 6 mois).
5. Fournir au coordonnateur un tableau de bord et des exports (PDF, Excel).
6. Aider les porteurs à rédiger (pitch, SWOT, modèle économique) grâce à l'IA générative, sous contrôle humain.

# 3. Utilisateurs et scénarios

| Profil | Besoin principal |
|---|---|
| Porteur de projet | Déposer son dossier, savoir ce qui manque, suivre la décision et ses jalons |
| Membre du comité | Évaluer les dossiers avec une grille commune |
| Mentor | Suivre les projets affectés, fixer objectifs et jalons, consigner les suivis |
| Coordonnateur | Piloter : décisions, affectations, alertes, indicateurs, comptes rendus |

**Entretiens utilisateurs (à renseigner par l'équipe, au moins deux) :**

| Interlocuteur | Rôle | Date | Principaux constats | Exigence en découlant |
|---|---|---|---|---|
| [à compléter] | [ex. coordonnateur du CIAT] | [date] | [à compléter] | [à compléter] |
| [à compléter] | [ex. porteur de projet] | [date] | [à compléter] | [à compléter] |

**Scénarios utilisateurs (à faire valider par les deux interlocuteurs) :**

- *S1 - Dépôt.* Un porteur crée un compte, saisit son idée, joint trois pièces, constate que le dossier est complet à 100 % et le soumet.
- *S2 - Sélection.* Deux membres du comité notent le dossier ; le coordonnateur vérifie la note moyenne et enregistre une décision motivée.
- *S3 - Accompagnement.* Le coordonnateur affecte un mentor, qui définit deux objectifs et quatre jalons ; le porteur joint une preuve pour valider un jalon.
- *S4 - Retard.* Un jalon dépasse son échéance : une alerte apparaît pour le porteur, le mentor et le coordonnateur.
- *S5 - Pilotage.* Le coordonnateur filtre par cohorte, compare les cohortes et exporte la synthèse en PDF et Excel.

# 4. Exigences fonctionnelles

Priorités : **P1** indispensable, **P2** important, **P3** souhaitable.

| Réf. | Exigence | Priorité |
|---|---|---|
| F1 | Inscription et connexion sécurisées ; profil modifiable | P1 |
| F2 | Rôles et droits (porteur, comité, mentor, coordonnateur) | P1 |
| F3 | Dépôt et modification du dossier (brouillon) | P1 |
| F4 | Ajout et suppression de pièces (PDF, Office, images, 5 Mo max) | P1 |
| F5 | Contrôle de complétude (champs + pièces obligatoires) bloquant la soumission | P1 |
| F6 | Renvoi du dossier pour complément avec motif | P2 |
| F7 | Grille d'évaluation pondérée (5 critères, note sur 100) par membre du comité | P1 |
| F8 | Décision motivée (accepté, liste d'attente, refusé), après un minimum d'évaluations | P1 |
| F9 | Affectation d'un mentor et définition d'objectifs | P1 |
| F10 | Jalons avec échéance, statut, preuve obligatoire pour valider | P1 |
| F11 | Commentaires sur le dossier | P2 |
| F12 | Alertes de retard (jalons) et de suivi à réaliser | P1 |
| F13 | Suivis à 3 et 6 mois (emplois, chiffre d'affaires, financements) créés à l'acceptation | P1 |
| F14 | Tableau de bord : entonnoir, statuts, domaines, cohortes, jalons, filtres | P1 |
| F15 | Compte rendu PDF par projet ; export Excel et synthèse PDF | P1 |
| F16 | Assistant IA : pitch, SWOT, modèle économique, plan d'action, brouillon de compte rendu | P1 |
| F17 | Gestion des comptes par le coordonnateur | P2 |
| F18 | Notifications par courriel | P3 *(hors périmètre de cette version)* |

# 5. Exigences non fonctionnelles

- **Sécurité :** mots de passe hachés, protection CSRF, requêtes SQL paramétrées, échappement HTML, en-têtes de sécurité (CSP), contrôle d'accès à chaque route et à chaque fichier, validation des fichiers téléversés.
- **Ergonomie :** interface en français, responsive (ordinateur et téléphone), contrastes lisibles, champs étiquetés.
- **Fiabilité :** base persistante (SQLite), messages d'erreur explicites, pages d'erreur dédiées.
- **Traçabilité de l'IA :** chaque génération est journalisée ; texte présenté comme brouillon.
- **Protection des données :** minimisation (nom, e-mail, téléphone), accès restreint par rôle.

# 6. Droits par rôle

| Action | Porteur | Comité | Mentor | Coordonnateur |
|---|:-:|:-:|:-:|:-:|
| Déposer / modifier son dossier (brouillon) | ✔ | | | |
| Voir un projet | les siens | soumis et suivants | affectés | tous |
| Évaluer | | ✔ | | |
| Décider / renvoyer | | | | ✔ |
| Affecter un mentor, clôturer l'incubation | | | | ✔ |
| Objectifs, jalons, suivis | | | ✔ (siens) | ✔ |
| Mettre à jour un jalon (avec preuve) | ✔ (siens) | | ✔ | ✔ |
| Tableau de bord, exports, comptes | | | | ✔ |
| Assistant IA | ✔ | | ✔ | ✔ |

# 7. Limites de cette version

- Pas de notification par courriel (les alertes sont affichées dans l'application).
- Pas de réinitialisation de mot de passe par courriel (le coordonnateur peut recréer un compte).
- Pas de limitation du nombre de tentatives de connexion.
- Stockage local des fichiers : sur un hébergement gratuit, prévoir un disque persistant ou un stockage externe.
- Le comité est modélisé par des évaluations individuelles puis une décision du coordonnateur ; il n'y a pas de vote en séance.
- Les données de démonstration sont fictives.

# 8. Critères d'acceptation

Le parcours S1 à S5 s'exécute de bout en bout sans erreur, les droits sont respectés (tests automatiques), les données persistent après redémarrage, et un jury peut se connecter avec les comptes de démonstration.
