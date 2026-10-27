"""Tests des fonctions essentielles : python -m unittest discover -s tests -v"""
import io
import os
import re
import sys
import tempfile
import unittest

TMP = tempfile.mkdtemp()
os.environ["DATABASE"] = os.path.join(TMP, "test.db")
os.environ["UPLOAD_DIR"] = os.path.join(TMP, "up")
os.makedirs(os.environ["UPLOAD_DIR"], exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A  # noqa: E402
import seed  # noqa: E402

PWD = seed.PASSWORD


def csrf_of(client):
    r = client.get("/connexion")
    return re.search(r'name="csrf" value="([0-9a-f]+)"', r.get_data(as_text=True)).group(1)


def login(email, pwd=PWD):
    c = A.app.test_client()
    tok = csrf_of(c)
    r = c.post("/connexion", data={"email": email, "password": pwd, "csrf": tok})
    assert r.status_code == 302, r.status_code
    return c


def tok(c, path="/projets"):
    return re.search(r'name="csrf" value="([0-9a-f]+)"', c.get(path).get_data(as_text=True)).group(1)


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed.run(reset=True)

    # ---- authentification et sécurité
    def test_01_login_wrong_password(self):
        c = A.app.test_client()
        r = c.post("/connexion", data={"email": "coordo@ciat.test", "password": "faux", "csrf": csrf_of(c)})
        self.assertEqual(r.status_code, 401)

    def test_02_csrf_required(self):
        c = A.app.test_client()
        r = c.post("/connexion", data={"email": "coordo@ciat.test", "password": PWD})
        self.assertEqual(r.status_code, 400)

    def test_03_protected_pages_redirect(self):
        r = A.app.test_client().get("/projets")
        self.assertEqual(r.status_code, 302)

    def test_04_register_creates_porteur_only(self):
        c = A.app.test_client()
        t = csrf_of(c)
        r = c.post("/inscription", data={"name": "Test Porteur", "email": "nouveau@x.sn", "password": "motdepasse1",
                                         "password2": "motdepasse1", "role": "coordonnateur", "csrf": t})
        self.assertEqual(r.status_code, 302)
        with A.app.app_context():
            self.assertEqual(A.q("SELECT role FROM users WHERE email='nouveau@x.sn'", one=True)["role"], "porteur")

    def test_05_register_short_password(self):
        c = A.app.test_client()
        r = c.post("/inscription", data={"name": "Test", "email": "a@b.sn", "password": "123", "password2": "123", "csrf": csrf_of(c)})
        self.assertEqual(r.status_code, 400)

    # ---- droits
    def test_10_porteur_cannot_see_other_project(self):
        c = login("porteur1@ciat.test")
        self.assertEqual(c.get("/projets/2").status_code, 403)
        self.assertEqual(c.get("/projets/1").status_code, 200)

    def test_11_porteur_cannot_open_dashboard_or_users(self):
        c = login("porteur1@ciat.test")
        self.assertEqual(c.get("/tableau-de-bord").status_code, 403)
        self.assertEqual(c.get("/utilisateurs").status_code, 403)
        self.assertEqual(c.get("/export/projets.xlsx").status_code, 403)

    def test_12_evaluateur_cannot_see_draft(self):
        c = login("comite1@ciat.test")
        self.assertEqual(c.get("/projets/14").status_code, 403)

    def test_13_mentor_sees_only_assigned(self):
        c = login("mentor1@ciat.test")
        with A.app.app_context():
            other = A.q("SELECT id FROM projects WHERE mentor_id != ? LIMIT 1", (A.q("SELECT id FROM users WHERE email='mentor1@ciat.test'", one=True)["id"],), one=True)["id"]
        self.assertEqual(c.get(f"/projets/{other}").status_code, 403)

    # ---- parcours complet porteur -> comité -> coordonnateur -> mentor
    def test_20_full_workflow(self):
        p = login("porteur14@ciat.test")  # sera propriétaire du nouveau projet
        t = tok(p)
        r = p.post("/projets/nouveau", data={"title": "Projet de test", "csrf": t})
        self.assertEqual(r.status_code, 302)
        pid = int(r.headers["Location"].rsplit("/", 1)[1])
        # soumission refusée : dossier incomplet
        r = p.post(f"/projets/{pid}/soumettre", data={"csrf": tok(p, f"/projets/{pid}")}, follow_redirects=True)
        self.assertIn("Dossier incomplet", r.get_data(as_text=True))
        # complétion
        p.post(f"/projets/{pid}/modifier", data={"csrf": tok(p, f"/projets/{pid}"), "title": "Projet de test", "domain": A.DOMAINES[0],
               "stage": A.STADES[1], "team_size": "3", "summary": "Résumé", "problem": "Problème", "solution": "Solution", "target": "Cible"})
        for dtp in A.DOC_REQUIRED:
            r = p.post(f"/projets/{pid}/documents", data={"csrf": tok(p, f"/projets/{pid}"), "doc_type": dtp,
                       "file": (io.BytesIO(b"%PDF-1.4 test"), "piece.pdf")}, content_type="multipart/form-data")
            self.assertEqual(r.status_code, 302)
        # fichier interdit
        p.post(f"/projets/{pid}/documents", data={"csrf": tok(p, f"/projets/{pid}"), "doc_type": "autre",
               "file": (io.BytesIO(b"MZ"), "virus.exe")}, content_type="multipart/form-data")
        with A.app.app_context():
            self.assertEqual(A.q("SELECT COUNT(*) c FROM documents WHERE project_id=? AND filename LIKE '%.exe'", (pid,), one=True)["c"], 0)
        r = p.post(f"/projets/{pid}/soumettre", data={"csrf": tok(p, f"/projets/{pid}")})
        self.assertEqual(r.status_code, 302)
        with A.app.app_context():
            self.assertEqual(A.q("SELECT status FROM projects WHERE id=?", (pid,), one=True)["status"], "soumis")
        # le porteur ne peut plus modifier
        self.assertEqual(p.get(f"/projets/{pid}/modifier").status_code, 302)
        # décision impossible sans évaluations
        co = login("coordo@ciat.test")
        r = co.post(f"/projets/{pid}/decision", data={"csrf": tok(co, f"/projets/{pid}"), "decision": "accepte",
                    "motivation": "Projet solide, équipe engagée et besoin avéré."}, follow_redirects=True)
        self.assertIn("au moins 2 évaluations", r.get_data(as_text=True))
        # évaluations du comité
        for email in ("comite1@ciat.test", "comite2@ciat.test"):
            ev = login(email)
            r = ev.post(f"/projets/{pid}/evaluer", data={"csrf": tok(ev, f"/projets/{pid}"), "innovation": 4, "faisabilite": 4,
                        "impact": 5, "equipe": 3, "marche": 4, "comment": "Bon dossier"})
            self.assertEqual(r.status_code, 302)
        with A.app.app_context():
            self.assertEqual(A.q("SELECT status FROM projects WHERE id=?", (pid,), one=True)["status"], "en_evaluation")
            ev = A.q("SELECT * FROM evaluations WHERE project_id=?", (pid,))
            self.assertEqual(A.weighted_score(ev[0]), 82.0)  # 20+16+25+9+12
        # motivation trop courte
        r = co.post(f"/projets/{pid}/decision", data={"csrf": tok(co, f"/projets/{pid}"), "decision": "accepte", "motivation": "ok"}, follow_redirects=True)
        self.assertIn("motivée", r.get_data(as_text=True))
        # décision valide
        r = co.post(f"/projets/{pid}/decision", data={"csrf": tok(co, f"/projets/{pid}"), "decision": "accepte", "cohort": "2026-B",
                    "motivation": "Projet solide, équipe engagée et besoin avéré."})
        self.assertEqual(r.status_code, 302)
        with A.app.app_context():
            row = A.q("SELECT status, cohort FROM projects WHERE id=?", (pid,), one=True)
            self.assertEqual((row["status"], row["cohort"]), ("incube", "2026-B"))
            self.assertEqual(A.q("SELECT COUNT(*) c FROM followups WHERE project_id=?", (pid,), one=True)["c"], 2)
            mid = A.q("SELECT id FROM users WHERE email='mentor2@ciat.test'", one=True)["id"]
        # mentor + objectifs + jalon
        co.post(f"/projets/{pid}/mentor", data={"csrf": tok(co, f"/projets/{pid}"), "mentor_id": mid})
        me = login("mentor2@ciat.test")
        self.assertEqual(me.get(f"/projets/{pid}").status_code, 200)
        me.post(f"/projets/{pid}/objectifs", data={"csrf": tok(me, f"/projets/{pid}"), "label": "Valider le prototype", "indicator": "10 tests"})
        me.post(f"/projets/{pid}/jalons", data={"csrf": tok(me, f"/projets/{pid}"), "title": "Prototype livré", "due_date": "2020-01-01"})
        with A.app.app_context():
            m = A.q("SELECT * FROM milestones WHERE project_id=?", (pid,), one=True)
            self.assertIsNotNone(m)
        # jalon en retard visible dans les alertes
        self.assertIn("Prototype livré", me.get("/alertes").get_data(as_text=True))
        # valider un jalon sans preuve : refusé
        r = me.post(f"/jalons/{m['id']}/statut", data={"csrf": tok(me, f"/projets/{pid}"), "status": "fait"}, follow_redirects=True)
        self.assertIn("preuve", r.get_data(as_text=True))
        # avec preuve : accepté
        me.post(f"/jalons/{m['id']}/statut", data={"csrf": tok(me, f"/projets/{pid}"), "status": "fait",
                "proof": (io.BytesIO(b"%PDF-1.4 preuve"), "preuve.pdf")}, content_type="multipart/form-data")
        with A.app.app_context():
            self.assertEqual(A.q("SELECT status FROM milestones WHERE id=?", (m["id"],), one=True)["status"], "fait")
        # le porteur voit la décision motivée
        self.assertIn("Projet solide", p.get(f"/projets/{pid}").get_data(as_text=True))

    def test_21_weighted_score(self):
        ev = {"innovation": 5, "faisabilite": 5, "impact": 5, "equipe": 5, "marche": 5}
        self.assertEqual(A.weighted_score(ev), 100.0)
        ev = {"innovation": 4, "faisabilite": 4, "impact": 5, "equipe": 3, "marche": 4}
        self.assertEqual(A.weighted_score(ev), 82.0)

    # ---- exports, tableau de bord, IA
    def test_30_dashboard_and_exports(self):
        co = login("coordo@ciat.test")
        self.assertEqual(co.get("/tableau-de-bord").status_code, 200)
        self.assertEqual(co.get("/tableau-de-bord?cohort=2025-A&domain=").status_code, 200)
        r = co.get("/export/projets.xlsx")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data[:2] == b"PK")
        r = co.get("/export/projets.pdf")
        self.assertTrue(r.data.startswith(b"%PDF"))
        r = co.get("/projets/2/compte-rendu.pdf")
        self.assertTrue(r.data.startswith(b"%PDF"))

    def test_31_ai_assistant_fallback(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        co = login("coordo@ciat.test")
        r = co.post("/projets/2/ia", data={"csrf": tok(co, "/projets/2"), "kind": "pitch"})
        html = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("gabarit local", html)
        self.assertIn("brouillon", html)
        r = co.post("/projets/2/ia", data={"csrf": tok(co, "/projets/2"), "kind": "inconnu"})
        self.assertEqual(r.status_code, 400)

    def test_32_evaluateur_has_no_ai_or_report(self):
        ev = login("comite1@ciat.test")
        self.assertEqual(ev.post("/projets/2/ia", data={"csrf": tok(ev, "/projets/2"), "kind": "pitch"}).status_code, 403)
        self.assertEqual(ev.get("/projets/2/compte-rendu.pdf").status_code, 403)

    def test_33_sql_injection_in_search(self):
        co = login("coordo@ciat.test")
        r = co.get("/projets?q=' OR 1=1 --")
        self.assertEqual(r.status_code, 200)

    def test_34_document_download_access(self):
        c = login("porteur1@ciat.test")
        with A.app.app_context():
            foreign = A.q("SELECT d.id FROM documents d JOIN projects p ON p.id=d.project_id WHERE p.owner_id != ? LIMIT 1",
                          (A.q("SELECT id FROM users WHERE email='porteur1@ciat.test'", one=True)["id"],), one=True)["id"]
        self.assertEqual(c.get(f"/documents/{foreign}").status_code, 403)

    def test_35_xss_escaped(self):
        p = login("porteur13@ciat.test")
        r = p.post("/projets/nouveau", data={"title": "<script>alert(1)</script>", "csrf": tok(p)}, follow_redirects=True)
        self.assertNotIn("<script>alert(1)</script>", r.get_data(as_text=True))

    def test_37_edit_form_opens_for_existing_draft(self):
        # régression : GET /projets/<id>/modifier renvoyait une erreur 500 (sqlite3.Row sans .get)
        p = login("porteur14@ciat.test")
        with A.app.app_context():
            pid = A.q("SELECT id FROM projects WHERE title LIKE 'MonCV%'", one=True)["id"]
        self.assertEqual(p.get(f"/projets/{pid}/modifier").status_code, 200)

    def test_36_health(self):
        self.assertEqual(A.app.test_client().get("/sante").json, {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
