---
title: "Journal des prompts"
subtitle: "Plateforme de gestion de l'incubateur du CIAT"
---

> **À compléter par l'équipe.** Le livrable attend les prompts réellement utilisés, les résultats obtenus et les corrections apportées. Les entrées 1 à 9 ci-dessous retracent le travail de conception et de développement de la plateforme ; elles sont à relire et à adapter. Ajoutez vos propres essais (maquettes, données, rapport, vidéo) dans le même format.

| N° | Date | Outil | Prompt (résumé fidèle) | Résultat obtenu | Vérification humaine / correction |
|---|---|---|---|---|---|
| 1 | 27/10/2026 | Claude | Joindre le sujet de l'évaluation et demander : « le sujet 2, aide-moi à le faire » | Choix du Projet 2 ; plan : application Flask + SQLite, 4 rôles, parcours dépôt → sélection → mentorat → suivi, exports, IA | Vérifier que chaque fonctionnalité attendue du sujet est couverte (voir matrice ci-dessous) |
| 2 | 27/10/2026 | Claude | Même demande ; le logo de l'ISEP est ajouté en pièce jointe | Application et PDF aux couleurs du logo (brun foncé, beige cuivré), logo intégré | Comparer avec le PDF du sujet ; l'infographe confirme la charte officielle (couleurs exactes, polices) |
| 3 | 27/10/2026 | Claude | Génération du schéma de base de données (9 tables) | `schema.sql` avec contraintes CHECK, clés étrangères, unicités | Relecture du modèle ; règle « une évaluation par évaluateur et par projet » ajoutée via UNIQUE |
| 4 | 27/10/2026 | Claude | Génération de l'application Flask (routes, droits, règles métier) | `app.py` : authentification, CSRF, droits par rôle, complétude, évaluation pondérée, décision motivée, jalons avec preuve, alertes | Un défaut de conception corrigé : l'export importait le module `app` deux fois quand on lançait `python app.py` ; le lancement est déplacé dans `run.py` |
| 5 | 27/10/2026 | Claude | Fonction d'IA générative avec repli hors ligne | `ai.py` : appel de l'API Claude si une clé existe, sinon gabarits locaux ; consigne « n'invente aucun chiffre » ; journalisation | Test sans clé API (mode gabarit) ; texte toujours présenté comme brouillon |
| 6 | 27/10/2026 | Claude | Génération des exports PDF / Excel | `exports.py` : compte rendu par projet, synthèse PDF, classeur Excel à 4 feuilles | Ouverture des fichiers produits ; accents et mise en page vérifiés |
| 7 | 27/10/2026 | Claude | Génération du jeu de données fictif | `seed.py` : 20 comptes, 14 projets, tous statuts, retards visibles | Vérifier que rien ne ressemble à des données réelles |
| 8 | 27/10/2026 | Claude | Écriture des tests automatiques | 18 tests (droits, CSRF, XSS, injection SQL, parcours complet, exports) | **Erreur de l'IA détectée par le test** : note attendue 80 au lieu de 82 (20+16+25+9+12). Le calcul de l'application était juste ; le test a été corrigé |
| 9 | 27/10/2026 | Claude | Rédaction du cahier des charges, du dictionnaire de données, du guide | Documents dans `docs/` | Les entretiens utilisateurs ne peuvent pas être inventés : tableau laissé à compléter |

# Limites rencontrées avec l'IA

- L'IA ne peut pas mener les entretiens ni connaître les procédures réelles du CIAT : à compléter par l'équipe.
- Le déploiement en ligne n'a pas été réalisé par l'IA : il doit être fait avec les identifiants de l'équipe.
- Sans clé d'API, la fonction d'IA utilise des gabarits : vérifier avant la démonstration quel mode est actif.

# Matrice de couverture du sujet (Projet 2)

| Fonctionnalité attendue | Où la trouver |
|---|---|
| Compte du porteur et profil | Inscription, « Mon profil » |
| Dépôt, complétude, documents | Fiche projet : barre de complétude, pièces |
| Grille d'évaluation, comité, décision motivée | Fiche projet : évaluation et décision |
| Mentor et objectifs | Fiche projet : mentorat, objectifs |
| Calendrier, jalons, preuves, commentaires, alertes | Fiche projet, « Alertes » |
| Tableau de bord, suivi à 3 et 6 mois | « Tableau de bord », fiche projet |
| Comptes rendus, export PDF / Excel | « Compte rendu PDF », « Export Excel » |
