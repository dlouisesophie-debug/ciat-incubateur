# Plateforme de gestion de l'incubateur du CIAT

Évaluation pratique en IA générative - ISEP Amadou Trawaré de Diamniadio - **Projet 2**.

Application web (Flask + SQLite) qui gère le parcours d'un projet : dépôt → complétude → évaluation du comité → décision motivée → mentor, objectifs, jalons et preuves → alertes → suivi à 3 et 6 mois, avec tableau de bord, exports PDF / Excel et assistant d'écriture IA.

## Lancement local

```bash
python -m venv .venv && source .venv/bin/activate     # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python seed.py --reset        # crée la base et les données de démonstration (fictives)
python run.py                 # http://localhost:5000
```

Comptes de démonstration (mot de passe `Ciat2026!`) : `coordo@ciat.test`, `comite1@ciat.test`, `mentor1@ciat.test`, `porteur1@ciat.test` (voir `docs/guide_utilisateur.md`).

## Variables d'environnement

| Variable | Rôle | Défaut |
|---|---|---|
| `SECRET_KEY` | Clé de session (**obligatoire en production**) | valeur de développement |
| `PRODUCTION` | `1` : cookies de session en mode sécurisé (HTTPS) | `0` |
| `DATABASE`, `UPLOAD_DIR` | Emplacement de la base et des fichiers | `instance/` |
| `ANTHROPIC_API_KEY` | Active l'IA via l'API Claude ; sinon gabarits locaux | vide |
| `ANTHROPIC_MODEL` | Modèle utilisé | `claude-sonnet-5-5` |
| `MIN_EVALUATIONS` | Évaluations minimales avant décision | `2` |

## Déploiement

- **Render** : déposer le projet sur GitHub, créer un « Blueprint » depuis `render.yaml`. Ajouter un disque persistant monté sur `instance/` (sinon base et fichiers sont perdus à chaque redéploiement sur l'offre gratuite).
- **Docker** : `docker build -t ciat . && docker run -p 8000:8000 -e SECRET_KEY=... -v ciat-data:/app/instance ciat`.
- Avant de donner l'adresse au jury, ouvrez `/sante` (doit répondre `{"status":"ok"}`) et connectez-vous avec un compte de démonstration.
- **Avant tout usage réel** : supprimer les comptes de démonstration (`@ciat.test`) et définir un `SECRET_KEY` aléatoire.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Organisation du code

| Fichier | Contenu |
|---|---|
| `app.py` | Routes, droits, règles métier, sécurité |
| `ai.py` | Assistant IA (API Claude ou gabarits) |
| `exports.py` | Exports Excel et PDF |
| `schema.sql` | Schéma de la base |
| `seed.py` | Jeu de données fictif |
| `templates/`, `static/` | Interface (HTML, CSS, JS) |
| `tests/` | Tests automatiques |
| `docs/` | Cahier des charges, dictionnaire, guide, rapport, journal des prompts, maquettes, script vidéo |

## Limites connues

Voir `docs/cahier_des_charges.md`, section 7.
