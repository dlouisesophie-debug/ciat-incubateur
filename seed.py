"""
Jeu de données de démonstration (FICTIF) : python seed.py [--reset]

Toutes les personnes, entreprises et chiffres sont inventés pour la démonstration.
Les dates sont calculées par rapport au jour d'exécution afin que les alertes de retard soient visibles.
Voir docs/dictionnaire_donnees.md pour la description du jeu de données.
"""
import datetime as dt
import os
import random
import sys

from werkzeug.security import generate_password_hash

import app as A

PASSWORD = "Ciat2026!"
random.seed(42)

USERS = [
    ("coordo@ciat.test", "Awa Ndiaye (coordonnatrice)", "coordonnateur"),
    ("comite1@ciat.test", "Dr Ibrahima Sarr (comité)", "evaluateur"),
    ("comite2@ciat.test", "Fatou Ba (comité)", "evaluateur"),
    ("comite3@ciat.test", "Moussa Faye (comité)", "evaluateur"),
    ("mentor1@ciat.test", "Cheikh Diallo (mentor)", "mentor"),
    ("mentor2@ciat.test", "Mariama Sow (mentor)", "mentor"),
]
PORTEURS = ["Aminata Gueye", "Oumar Thiam", "Khadija Mbaye", "Pape Samb", "Ndeye Fall", "Abdou Sy", "Rokhaya Cissé",
            "Samba Ndoye", "Bineta Kane", "Mamadou Seck", "Astou Diop", "Lamine Badji", "Seynabou Niang", "Ousmane Dione"]

# (titre, domaine, stade, problème, solution, cible, statut, cohorte)
PROJETS = [
    ("AgriSMS - conseils agricoles par SMS", 2, 3, "Les petits producteurs manquent d'informations météo et de prix.", "Un service de conseils par SMS en wolof et français.", "Producteurs de la vallée et des Niayes", "post_incubation", "2025-A"),
    ("SolarKiosk - recharge solaire de quartier", 3, 2, "Coupures d'électricité fréquentes dans les quartiers périphériques.", "Des kiosques solaires de recharge de téléphones et de lampes.", "Ménages et petits commerces", "incube", "2025-A"),
    ("MediStock - suivi des médicaments", 4, 2, "Ruptures de stock dans les petites pharmacies.", "Application de suivi de stock avec alertes de péremption.", "Pharmacies de proximité", "incube", "2025-B"),
    ("EduJang - soutien scolaire en ligne", 5, 3, "Manque de soutien scolaire accessible hors des grandes villes.", "Cours courts en vidéo basse consommation de données.", "Élèves du collège", "incube", "2025-B"),
    ("TeranGa Maintenance - GMAO pour PME", 1, 2, "Les ateliers n'ont pas de suivi de leurs pannes.", "Un outil de maintenance préventive simple d'usage.", "Ateliers et petites usines", "incube", "2026-A"),
    ("FarmDry - séchoir solaire de fruits", 2, 2, "Fortes pertes post-récolte de mangues.", "Séchoir solaire abordable à construire localement.", "Coopératives de transformation", "incube", "2026-A"),
    ("CollectePlus - tri des déchets", 6, 1, "Déchets non collectés dans certains quartiers.", "Plateforme de signalement et de collecte par des jeunes.", "Collectivités locales", "incube", "2026-A"),
    ("DiagnoVoix - aide au diagnostic", 0, 0, "Accès limité aux spécialistes.", "Pré-diagnostic assisté par IA à partir de questionnaires.", "Centres de santé", "en_evaluation", None),
    ("BoutiqueLink - gestion de petites boutiques", 6, 1, "Les boutiquiers tiennent leurs comptes sur papier.", "Application mobile de caisse et de crédits clients.", "Boutiquiers", "en_evaluation", None),
    ("FormaPro - orientation professionnelle", 5, 1, "Les jeunes connaissent mal les filières porteuses.", "Parcours d'orientation interactif.", "Lycéens", "soumis", None),
    ("EauClaire - capteurs de qualité de l'eau", 3, 2, "Eau de puits non contrôlée.", "Capteurs bon marché reliés à une alerte SMS.", "Villages", "refuse", "2026-A"),
    ("RecyPlast - briques en plastique recyclé", 1, 2, "Accumulation de déchets plastiques.", "Briques de pavage à base de plastique recyclé.", "Communes", "liste_attente", "2026-A"),
    ("AgroDrone - cartographie de parcelles", 2, 0, "Estimation difficile des surfaces cultivées.", "Cartographie par drone et IA.", "Agriculteurs", "a_completer", None),
    ("MonCV Sénégal - aide à l'insertion", 5, 0, "", "", "", "brouillon", None),
]
DOMS = A.DOMAINES
STAGES = A.STADES


def run(reset=False):
    if reset and os.path.exists(A.app.config["DATABASE"]):
        os.remove(A.app.config["DATABASE"])
    A.init_db()
    with A.app.app_context(), A.app.test_request_context():
        db = A.get_db()
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            print("La base contient déjà des données ; utilisez --reset pour repartir de zéro.")
            return
        ph = generate_password_hash(PASSWORD)
        stamp = A.now()
        uid = {}
        for email, name, role in USERS:
            uid[email] = A.ex("INSERT INTO users(email,name,role,password_hash,organisation,created_at) VALUES (?,?,?,?,?,?)",
                              (email, name, role, ph, "ISEP-AT Diamniadio", stamp))
        owners = []
        for i, name in enumerate(PORTEURS, 1):
            owners.append(A.ex("INSERT INTO users(email,name,role,password_hash,phone,created_at) VALUES (?,?,?,?,?,?)",
                               (f"porteur{i}@ciat.test", name, "porteur", ph, f"77 000 00 {i:02d}", stamp)))
        evals = [uid["comite1@ciat.test"], uid["comite2@ciat.test"], uid["comite3@ciat.test"]]
        mentors = [uid["mentor1@ciat.test"], uid["mentor2@ciat.test"]]
        coordo = uid["coordo@ciat.test"]
        today = dt.date.today()

        for i, (title, dom, stage, prob, sol, tgt, status, cohort) in enumerate(PROJETS):
            created = today - dt.timedelta(days=random.randint(40, 400))
            has_content = bool(prob)
            pid = A.ex("""INSERT INTO projects(owner_id,title,domain,stage,team_size,summary,problem,solution,target,cohort,status,created_at,submitted_at)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (owners[i], title, DOMS[dom] if has_content else None, STAGES[stage] if has_content else None,
                        random.randint(2, 5) if has_content else None, f"{sol} {prob}"[:200] if has_content else None,
                        prob or None, sol or None, tgt or None, cohort, status, created.isoformat(),
                        (created + dt.timedelta(days=5)).isoformat() if status not in ("brouillon", "a_completer") else None))
            # pièces jointes (PDF de démonstration)
            doc_types = A.DOC_REQUIRED if status != "a_completer" else ["fiche_projet"]
            if status == "brouillon":
                doc_types = []
            for dtp in doc_types:
                stored = f"demo_{pid}_{dtp}.pdf"
                _make_pdf(os.path.join(A.app.config["UPLOAD_DIR"], stored), f"{A.DOC_TYPES[dtp]} - {title} (document de démonstration)")
                A.ex("INSERT INTO documents(project_id,doc_type,filename,stored_name,uploaded_at) VALUES (?,?,?,?,?)",
                     (pid, dtp, f"{dtp}.pdf", stored, created.isoformat()))
            # évaluations
            if status in ("en_evaluation", "refuse", "liste_attente", "incube", "post_incubation"):
                n = 1 if status == "en_evaluation" and i % 2 else 3
                base = {"refuse": 1.8, "liste_attente": 2.8}.get(status, 3.8)
                for ev in evals[:n]:
                    vals = [max(0, min(5, round(random.gauss(base, 0.7)))) for _ in range(5)]
                    A.ex("""INSERT INTO evaluations(project_id,evaluator_id,innovation,faisabilite,impact,equipe,marche,comment,created_at)
                            VALUES (?,?,?,?,?,?,?,?,?)""",
                         (pid, ev, *vals, "Évaluation de démonstration.", (created + dt.timedelta(days=12)).isoformat()))
            # décision, mentor, objectifs, jalons, suivis
            if status in ("refuse", "liste_attente", "incube", "post_incubation"):
                dec = {"refuse": "refuse", "liste_attente": "liste_attente"}.get(status, "accepte")
                texts = {"accepte": "Besoin avéré, équipe motivée et prototype réaliste : accepté en incubation.",
                         "refuse": "Solution insuffisamment différenciée et faisabilité technique non démontrée à ce stade.",
                         "liste_attente": "Idée intéressante mais capacité d'accueil atteinte pour cette cohorte."}
                decided = created + dt.timedelta(days=20)
                A.ex("INSERT INTO decisions(project_id,decision,motivation,decided_by,decided_at) VALUES (?,?,?,?,?)",
                     (pid, dec, texts[dec], coordo, decided.isoformat()))
                if dec == "accepte":
                    A.ex("UPDATE projects SET mentor_id=? WHERE id=?", (mentors[i % 2], pid))
                    oid = A.ex("INSERT INTO objectives(project_id,label,indicator,due_date,created_by) VALUES (?,?,?,?,?)",
                               (pid, "Valider le prototype auprès d'utilisateurs réels", "10 utilisateurs ayant testé", (decided + dt.timedelta(days=90)).isoformat(), coordo))
                    A.ex("INSERT INTO objectives(project_id,label,indicator,due_date,created_by) VALUES (?,?,?,?,?)",
                         (pid, "Obtenir un premier financement ou client", "1 contrat ou 1 financement", (decided + dt.timedelta(days=180)).isoformat(), coordo))
                    titles = ["Étude de marché terminée", "Prototype fonctionnel", "Tests utilisateurs", "Premier client ou financement"]
                    for k, t in enumerate(titles):
                        due = decided + dt.timedelta(days=30 * (k + 1))
                        if status == "post_incubation":
                            st = "fait"
                        else:
                            st = "fait" if due < today - dt.timedelta(days=10) and random.random() > 0.25 else \
                                 ("en_cours" if due >= today and k and random.random() > 0.5 else "a_faire")
                        proof = None
                        if st == "fait":
                            proof = f"demo_proof_{pid}_{k}.pdf"
                            _make_pdf(os.path.join(A.app.config["UPLOAD_DIR"], proof), f"Preuve : {t} - {title}")
                        A.ex("""INSERT INTO milestones(project_id,objective_id,title,due_date,status,proof_name,proof_stored,completed_at,created_by)
                                VALUES (?,?,?,?,?,?,?,?,?)""",
                             (pid, oid if k < 3 else None, t, due.isoformat(), st, "preuve.pdf" if proof else None, proof,
                              due.isoformat() if st == "fait" else None, mentors[i % 2]))
                    for kind, months in (("3_mois", 3), ("6_mois", 6)):
                        due = A.add_months(decided, months)
                        done = status == "post_incubation" or (due < today and random.random() > 0.4)
                        A.ex("""INSERT INTO followups(project_id,kind,due_date,done_date,status,notes,jobs,revenue,funding)
                                VALUES (?,?,?,?,?,?,?,?,?)""",
                             (pid, kind, due.isoformat(), due.isoformat() if done else None, "fait" if done else "a_faire",
                              "Suivi de démonstration." if done else None, random.randint(1, 6) if done else None,
                              random.randint(0, 3_000_000) if done else None, random.randint(0, 5_000_000) if done and kind == "6_mois" else None))
                    A.ex("INSERT INTO comments(project_id,author_id,body,created_at) VALUES (?,?,?,?)",
                         (pid, mentors[i % 2], "Bon démarrage. Priorité : tests auprès d'utilisateurs réels avant le prochain jalon.", (decided + dt.timedelta(days=8)).isoformat()))
            if status == "a_completer":
                A.ex("INSERT INTO comments(project_id,author_id,body,created_at) VALUES (?,?,?,?)",
                     (pid, coordo, "Dossier renvoyé pour complément : ajoutez le CV et le budget prévisionnel.", stamp))
        db.commit()
        print(f"Base initialisée : {len(USERS) + len(PORTEURS)} comptes, {len(PROJETS)} projets. Mot de passe de démonstration : {PASSWORD}")


def _make_pdf(path, text):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(60, 780, text[:90])
    c.drawString(60, 760, "Document fictif généré pour la démonstration de la plateforme.")
    c.save()


if __name__ == "__main__":
    run(reset="--reset" in sys.argv)
