"""
Plateforme de gestion de l'incubateur du CIAT - ISEP Amadou Trawaré de Diamniadio.

Application Flask + SQLite. Parcours couvert : dépôt de l'idée -> contrôle de complétude ->
évaluation par le comité -> décision motivée -> mentorat, objectifs, jalons -> suivi à 3 et 6 mois.

Lancement : voir README.md
"""
import datetime as dt
import io
import os
import secrets
import sqlite3
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   send_file, send_from_directory, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

app = Flask(__name__, instance_path=INSTANCE_DIR)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    DATABASE=os.environ.get("DATABASE", os.path.join(INSTANCE_DIR, "incubateur.db")),
    UPLOAD_DIR=os.environ.get("UPLOAD_DIR", os.path.join(INSTANCE_DIR, "uploads")),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # 5 Mo par requête
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("PRODUCTION") == "1",
    PERMANENT_SESSION_LIFETIME=dt.timedelta(hours=8),
)
os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)

MIN_EVALUATIONS = int(os.environ.get("MIN_EVALUATIONS", "2"))
ALLOWED_EXT = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "png", "jpg", "jpeg"}

ROLES = {
    "porteur": "Porteur de projet",
    "evaluateur": "Membre du comité",
    "mentor": "Mentor",
    "coordonnateur": "Coordonnateur",
}
STATUTS = {
    "brouillon": "Brouillon",
    "a_completer": "À compléter",
    "soumis": "Soumis",
    "en_evaluation": "En évaluation",
    "liste_attente": "Liste d'attente",
    "refuse": "Refusé",
    "incube": "En incubation",
    "post_incubation": "Post-incubation",
}
DOMAINES = [
    "TIC, numérique, IA et données",
    "Mécanique, fabrication et maintenance",
    "Agriculture, transformation et environnement",
    "Énergie et énergies renouvelables",
    "Pharmaceutique et biomédical",
    "Éducation, formation et insertion",
    "Services aux collectivités et entrepreneuriat",
]
STADES = ["Idée", "Étude de faisabilité", "Prototype", "Produit minimum viable", "Premiers clients"]
DOC_TYPES = {
    "fiche_projet": "Fiche de projet",
    "cv": "CV du porteur",
    "budget": "Budget prévisionnel",
    "pitch": "Présentation / pitch (facultatif)",
    "autre": "Autre pièce (facultatif)",
}
DOC_REQUIRED = ["fiche_projet", "cv", "budget"]
CRITERES = [  # (clé, libellé, pondération sur 100)
    ("innovation", "Caractère innovant", 25),
    ("faisabilite", "Faisabilité technique", 20),
    ("impact", "Impact économique et social", 25),
    ("equipe", "Qualité de l'équipe", 15),
    ("marche", "Potentiel de marché", 15),
]
FIELDS_REQUIRED = [
    ("title", "Titre"), ("domain", "Domaine"), ("stage", "Stade d'avancement"),
    ("team_size", "Taille de l'équipe"), ("summary", "Résumé"), ("problem", "Problème visé"),
    ("solution", "Solution proposée"), ("target", "Public cible"),
]
MILESTONE_STATUS = {"a_faire": "À faire", "en_cours": "En cours", "fait": "Fait"}


# --------------------------------------------------------------------------- base de données
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(app.config["DATABASE"]) as con:
        with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
            con.executescript(f.read())


def q(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def ex(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def today():
    return dt.date.today().isoformat()


# --------------------------------------------------------------------------- sécurité
@app.before_request
def load_user_and_csrf():
    g.user = None
    uid = session.get("uid")
    if uid:
        g.user = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
        if g.user is None:
            session.clear()
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    if request.method == "POST":
        sent = request.form.get("csrf", "")
        if not secrets.compare_digest(sent, session["csrf"]):
            abort(400)


@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "script-src 'self'; form-action 'self'; frame-ancestors 'none'")
    return resp


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if g.user is None:
            flash("Veuillez vous connecter.", "warn")
            return redirect(url_for("login", next=request.path))
        return f(*a, **kw)
    return wrapper


def roles_required(*roles):
    def deco(f):
        @wraps(f)
        @login_required
        def wrapper(*a, **kw):
            if g.user["role"] not in roles:
                abort(403)
            return f(*a, **kw)
        return wrapper
    return deco


@app.context_processor
def inject_globals():
    return dict(
        csrf=lambda: session.get("csrf", ""), ROLES=ROLES, STATUTS=STATUTS, DOC_TYPES=DOC_TYPES,
        MILESTONE_STATUS=MILESTONE_STATUS, CRITERES=CRITERES, DOMAINES=DOMAINES, STADES=STADES,
        today=today(), nb_alertes=count_alerts() if g.get("user") else 0)


@app.template_filter("fr_date")
def fr_date(value):
    if not value:
        return "—"
    try:
        return dt.datetime.strptime(value[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return value


# --------------------------------------------------------------------------- règles métier
def weighted_score(ev):
    """Note pondérée sur 100 pour une évaluation."""
    return round(sum(ev[k] / 5 * w for k, _l, w in CRITERES), 1)


def project_scores(project_id):
    evs = q("""SELECT e.*, u.name AS evaluator FROM evaluations e
               JOIN users u ON u.id=e.evaluator_id WHERE project_id=? ORDER BY e.created_at""", (project_id,))
    scores = [weighted_score(e) for e in evs]
    avg = round(sum(scores) / len(scores), 1) if scores else None
    return evs, scores, avg


def completeness(project):
    """Contrôle de complétude : champs obligatoires + pièces obligatoires."""
    missing_fields = [lab for key, lab in FIELDS_REQUIRED if not str(project[key] or "").strip()]
    have = {r["doc_type"] for r in q("SELECT DISTINCT doc_type FROM documents WHERE project_id=?", (project["id"],))}
    missing_docs = [DOC_TYPES[d] for d in DOC_REQUIRED if d not in have]
    total = len(FIELDS_REQUIRED) + len(DOC_REQUIRED)
    done = total - len(missing_fields) - len(missing_docs)
    return dict(pct=round(done / total * 100), missing_fields=missing_fields,
                missing_docs=missing_docs, complete=not missing_fields and not missing_docs)


def can_view(p):
    u = g.user
    if u["role"] == "coordonnateur":
        return True
    if u["role"] == "porteur":
        return p["owner_id"] == u["id"]
    if u["role"] == "evaluateur":
        return p["status"] != "brouillon"
    if u["role"] == "mentor":
        return p["mentor_id"] == u["id"]
    return False


def get_project(pid):
    p = q("""SELECT p.*, o.name AS owner_name, o.email AS owner_email, m.name AS mentor_name
             FROM projects p JOIN users o ON o.id=p.owner_id LEFT JOIN users m ON m.id=p.mentor_id
             WHERE p.id=?""", (pid,), one=True)
    if p is None:
        abort(404)
    if not can_view(p):
        abort(403)
    return p


def can_edit(p):
    return (g.user["role"] == "porteur" and p["owner_id"] == g.user["id"]
            and p["status"] in ("brouillon", "a_completer"))


def can_manage(p):
    """Coordonnateur, ou mentor affecté, pour le suivi."""
    return g.user["role"] == "coordonnateur" or (g.user["role"] == "mentor" and p["mentor_id"] == g.user["id"])


def late_milestones_sql():
    return ("m.status != 'fait' AND m.due_date < date('now')")


def count_alerts():
    u = g.user
    base = f"SELECT COUNT(*) c FROM milestones m JOIN projects p ON p.id=m.project_id WHERE {late_milestones_sql()}"
    if u["role"] == "coordonnateur":
        return q(base, one=True)["c"]
    if u["role"] == "mentor":
        return q(base + " AND p.mentor_id=?", (u["id"],), one=True)["c"]
    if u["role"] == "porteur":
        return q(base + " AND p.owner_id=?", (u["id"],), one=True)["c"]
    return 0


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return dt.date(year, month, day)


def save_upload(file_storage):
    """Valide et enregistre un fichier ; retourne (nom_original, nom_stocké) ou None."""
    if not file_storage or not file_storage.filename:
        return None
    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED_EXT:
        flash("Format de fichier non autorisé (PDF, Office, PNG, JPG).", "error")
        return None
    stored = f"{secrets.token_hex(12)}.{ext}"
    file_storage.save(os.path.join(app.config["UPLOAD_DIR"], stored))
    return original, stored


# --------------------------------------------------------------------------- authentification
@app.route("/")
def index():
    if g.user:
        return redirect(url_for("dashboard") if g.user["role"] == "coordonnateur" else url_for("projects"))
    return render_template("index.html")


@app.route("/inscription", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        name, email, pwd = f.get("name", "").strip(), f.get("email", "").strip().lower(), f.get("password", "")
        errors = []
        if len(name) < 3:
            errors.append("Le nom est trop court.")
        if "@" not in email or "." not in email.split("@")[-1]:
            errors.append("Adresse e-mail invalide.")
        if len(pwd) < 8:
            errors.append("Le mot de passe doit contenir au moins 8 caractères.")
        if pwd != f.get("password2"):
            errors.append("Les mots de passe ne correspondent pas.")
        if q("SELECT 1 FROM users WHERE email=?", (email,), one=True):
            errors.append("Un compte existe déjà avec cet e-mail.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", form=f), 400
        # Seul le rôle « porteur » est auto-attribué ; les autres rôles sont créés par le coordonnateur.
        ex("INSERT INTO users(email,name,role,password_hash,phone,organisation,created_at) VALUES (?,?,?,?,?,?,?)",
           (email, name, "porteur", generate_password_hash(pwd), f.get("phone", "").strip(),
            f.get("organisation", "").strip(), now()))
        flash("Compte créé. Vous pouvez vous connecter.", "ok")
        return redirect(url_for("login"))
    return render_template("register.html", form={})


@app.route("/connexion", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        u = q("SELECT * FROM users WHERE email=?", (email,), one=True)
        if u and check_password_hash(u["password_hash"], request.form.get("password", "")):
            session.clear()
            session.permanent = True
            session["uid"] = u["id"]
            session["csrf"] = secrets.token_hex(16)
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("index"))
        flash("Identifiants incorrects.", "error")
        return render_template("login.html"), 401
    return render_template("login.html")


@app.route("/deconnexion", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/profil", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        f = request.form
        name = f.get("name", "").strip()
        if len(name) < 3:
            flash("Le nom est trop court.", "error")
        else:
            ex("UPDATE users SET name=?, phone=?, organisation=?, bio=? WHERE id=?",
               (name, f.get("phone", "").strip(), f.get("organisation", "").strip(),
                f.get("bio", "").strip(), g.user["id"]))
            new = f.get("new_password", "")
            if new:
                if len(new) < 8 or not check_password_hash(g.user["password_hash"], f.get("old_password", "")):
                    flash("Mot de passe inchangé : ancien mot de passe incorrect ou nouveau trop court.", "error")
                    return redirect(url_for("profile"))
                ex("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new), g.user["id"]))
            flash("Profil mis à jour.", "ok")
        return redirect(url_for("profile"))
    return render_template("profile.html")


# --------------------------------------------------------------------------- projets
@app.route("/projets")
@login_required
def projects():
    u = g.user
    where, args = [], []
    if u["role"] == "porteur":
        where.append("p.owner_id=?"); args.append(u["id"])
    elif u["role"] == "evaluateur":
        where.append("p.status != 'brouillon'")
    elif u["role"] == "mentor":
        where.append("p.mentor_id=?"); args.append(u["id"])
    for key in ("status", "domain", "cohort"):
        v = request.args.get(key, "")
        if v:
            where.append(f"p.{key}=?"); args.append(v)
    s = request.args.get("q", "").strip()
    if s:
        where.append("(p.title LIKE ? OR o.name LIKE ?)"); args += [f"%{s}%", f"%{s}%"]
    sql = f"""SELECT p.*, o.name AS owner_name, m.name AS mentor_name,
              (SELECT ROUND(AVG((e.innovation*25.0+e.faisabilite*20+e.impact*25+e.equipe*15+e.marche*15)/5),1)
                 FROM evaluations e WHERE e.project_id=p.id) AS avg_score,
              (SELECT COUNT(*) FROM milestones m2 WHERE m2.project_id=p.id AND m2.status!='fait'
                 AND m2.due_date < date('now')) AS late
              FROM projects p JOIN users o ON o.id=p.owner_id LEFT JOIN users m ON m.id=p.mentor_id
              {'WHERE ' + ' AND '.join(where) if where else ''} ORDER BY p.created_at DESC"""
    rows = q(sql, args)
    cohorts = [r["cohort"] for r in q("SELECT DISTINCT cohort FROM projects WHERE cohort IS NOT NULL ORDER BY cohort")]
    return render_template("projects.html", projects=rows, cohorts=cohorts, filters=request.args)


@app.route("/projets/nouveau", methods=["GET", "POST"])
@roles_required("porteur")
def project_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if len(title) < 3:
            flash("Donnez un titre au projet.", "error")
            return render_template("project_form.html", p=request.form, new=True), 400
        pid = ex("INSERT INTO projects(owner_id,title,created_at) VALUES (?,?,?)", (g.user["id"], title, now()))
        _update_project_fields(pid, request.form)
        flash("Brouillon créé. Complétez le dossier puis ajoutez les pièces.", "ok")
        return redirect(url_for("project_detail", pid=pid))
    return render_template("project_form.html", p={}, new=True)


def _update_project_fields(pid, f):
    try:
        team = int(f.get("team_size") or 0) or None
    except ValueError:
        team = None
    domain = f.get("domain") if f.get("domain") in DOMAINES else None
    stage = f.get("stage") if f.get("stage") in STADES else None
    ex("""UPDATE projects SET title=?, domain=?, stage=?, team_size=?, summary=?, problem=?, solution=?, target=?
           WHERE id=?""",
       (f.get("title", "").strip(), domain, stage, team, f.get("summary", "").strip(),
        f.get("problem", "").strip(), f.get("solution", "").strip(), f.get("target", "").strip(), pid))


@app.route("/projets/<int:pid>/modifier", methods=["GET", "POST"])
@roles_required("porteur")
def project_edit(pid):
    p = get_project(pid)
    if not can_edit(p):
        flash("Ce dossier n'est plus modifiable.", "warn")
        return redirect(url_for("project_detail", pid=pid))
    if request.method == "POST":
        if len(request.form.get("title", "").strip()) < 3:
            flash("Le titre est obligatoire.", "error")
            return render_template("project_form.html", p=request.form, new=False, pid=pid), 400
        _update_project_fields(pid, request.form)
        flash("Dossier enregistré.", "ok")
        return redirect(url_for("project_detail", pid=pid))
    return render_template("project_form.html", p=dict(p), new=False, pid=pid)


@app.route("/projets/<int:pid>")
@login_required
def project_detail(pid, ai_output=None, ai_kind=None):
    p = get_project(pid)
    evs, scores, avg = project_scores(pid)
    ctx = dict(
        p=p, comp=completeness(p), editable=can_edit(p), manage=can_manage(p),
        docs=q("SELECT * FROM documents WHERE project_id=? ORDER BY uploaded_at", (pid,)),
        evs=evs, scores=scores, avg=avg,
        my_eval=q("SELECT * FROM evaluations WHERE project_id=? AND evaluator_id=?", (pid, g.user["id"]), one=True),
        decision=q("""SELECT d.*, u.name AS by FROM decisions d JOIN users u ON u.id=d.decided_by
                      WHERE project_id=? ORDER BY d.id DESC LIMIT 1""", (pid,), one=True),
        objectives=q("SELECT * FROM objectives WHERE project_id=? ORDER BY due_date", (pid,)),
        milestones=q("""SELECT m.*, o.label AS objective FROM milestones m
                        LEFT JOIN objectives o ON o.id=m.objective_id
                        WHERE m.project_id=? ORDER BY m.due_date""", (pid,)),
        comments=q("""SELECT c.*, u.name AS author, u.role FROM comments c JOIN users u ON u.id=c.author_id
                      WHERE c.project_id=? ORDER BY c.created_at""", (pid,)),
        followups=q("SELECT * FROM followups WHERE project_id=? ORDER BY due_date", (pid,)),
        mentors=q("SELECT id,name FROM users WHERE role='mentor' ORDER BY name") if g.user["role"] == "coordonnateur" else [],
        min_evals=MIN_EVALUATIONS, ai_output=ai_output, ai_kind=ai_kind,
        ai_enabled=g.user["role"] in ("porteur", "mentor", "coordonnateur"))
    return render_template("project_detail.html", **ctx)


@app.route("/projets/<int:pid>/documents", methods=["POST"])
@roles_required("porteur")
def document_upload(pid):
    p = get_project(pid)
    if not can_edit(p):
        abort(403)
    doc_type = request.form.get("doc_type")
    if doc_type not in DOC_TYPES:
        flash("Type de pièce inconnu.", "error")
        return redirect(url_for("project_detail", pid=pid))
    saved = save_upload(request.files.get("file"))
    if saved:
        ex("INSERT INTO documents(project_id,doc_type,filename,stored_name,uploaded_at) VALUES (?,?,?,?,?)",
           (pid, doc_type, saved[0], saved[1], now()))
        flash("Pièce ajoutée.", "ok")
    elif not request.files.get("file") or not request.files["file"].filename:
        flash("Choisissez un fichier.", "error")
    return redirect(url_for("project_detail", pid=pid))


@app.route("/documents/<int:did>")
@login_required
def document_download(did):
    d = q("SELECT * FROM documents WHERE id=?", (did,), one=True)
    if d is None:
        abort(404)
    get_project(d["project_id"])  # contrôle d'accès
    return send_from_directory(app.config["UPLOAD_DIR"], d["stored_name"], as_attachment=True,
                               download_name=d["filename"])


@app.route("/documents/<int:did>/supprimer", methods=["POST"])
@roles_required("porteur")
def document_delete(did):
    d = q("SELECT * FROM documents WHERE id=?", (did,), one=True)
    if d is None:
        abort(404)
    p = get_project(d["project_id"])
    if not can_edit(p):
        abort(403)
    ex("DELETE FROM documents WHERE id=?", (did,))
    try:
        os.remove(os.path.join(app.config["UPLOAD_DIR"], d["stored_name"]))
    except OSError:
        pass
    flash("Pièce supprimée.", "ok")
    return redirect(url_for("project_detail", pid=p["id"]))


@app.route("/projets/<int:pid>/soumettre", methods=["POST"])
@roles_required("porteur")
def project_submit(pid):
    p = get_project(pid)
    if not can_edit(p):
        abort(403)
    c = completeness(p)
    if not c["complete"]:
        flash("Dossier incomplet : " + ", ".join(c["missing_fields"] + c["missing_docs"]) + ".", "error")
        return redirect(url_for("project_detail", pid=pid))
    ex("UPDATE projects SET status='soumis', submitted_at=? WHERE id=?", (now(), pid))
    flash("Dossier soumis au comité. Vous serez informé de la décision sur cette page.", "ok")
    return redirect(url_for("project_detail", pid=pid))


@app.route("/projets/<int:pid>/renvoyer", methods=["POST"])
@roles_required("coordonnateur")
def project_return(pid):
    p = get_project(pid)
    if p["status"] not in ("soumis", "en_evaluation"):
        abort(400)
    motif = request.form.get("motif", "").strip()
    if len(motif) < 10:
        flash("Précisez ce qui doit être complété (10 caractères minimum).", "error")
        return redirect(url_for("project_detail", pid=pid))
    ex("UPDATE projects SET status='a_completer' WHERE id=?", (pid,))
    ex("INSERT INTO comments(project_id,author_id,body,created_at) VALUES (?,?,?,?)",
       (pid, g.user["id"], "Dossier renvoyé pour complément : " + motif, now()))
    flash("Dossier renvoyé au porteur.", "ok")
    return redirect(url_for("project_detail", pid=pid))


# --------------------------------------------------------------------------- évaluation et décision
@app.route("/projets/<int:pid>/evaluer", methods=["POST"])
@roles_required("evaluateur")
def project_evaluate(pid):
    p = get_project(pid)
    if p["status"] not in ("soumis", "en_evaluation", "liste_attente"):
        flash("Ce dossier n'est pas évaluable dans son état actuel.", "warn")
        return redirect(url_for("project_detail", pid=pid))
    vals = {}
    for key, _lab, _w in CRITERES:
        try:
            v = int(request.form.get(key, ""))
        except ValueError:
            v = -1
        if not 0 <= v <= 5:
            flash("Chaque critère doit être noté de 0 à 5.", "error")
            return redirect(url_for("project_detail", pid=pid))
        vals[key] = v
    comment = request.form.get("comment", "").strip()
    existing = q("SELECT id FROM evaluations WHERE project_id=? AND evaluator_id=?", (pid, g.user["id"]), one=True)
    if existing:
        ex("""UPDATE evaluations SET innovation=?,faisabilite=?,impact=?,equipe=?,marche=?,comment=?,created_at=?
              WHERE id=?""", (*[vals[k] for k, _l, _w in CRITERES], comment, now(), existing["id"]))
    else:
        ex("""INSERT INTO evaluations(project_id,evaluator_id,innovation,faisabilite,impact,equipe,marche,comment,created_at)
              VALUES (?,?,?,?,?,?,?,?,?)""", (pid, g.user["id"], *[vals[k] for k, _l, _w in CRITERES], comment, now()))
    if p["status"] == "soumis":
        ex("UPDATE projects SET status='en_evaluation' WHERE id=?", (pid,))
    flash("Votre évaluation est enregistrée.", "ok")
    return redirect(url_for("project_detail", pid=pid))


@app.route("/projets/<int:pid>/decision", methods=["POST"])
@roles_required("coordonnateur")
def project_decide(pid):
    p = get_project(pid)
    if p["status"] not in ("soumis", "en_evaluation", "liste_attente"):
        abort(400)
    decision = request.form.get("decision")
    motivation = request.form.get("motivation", "").strip()
    if decision not in ("accepte", "refuse", "liste_attente"):
        abort(400)
    if len(motivation) < 20:
        flash("La décision doit être motivée (20 caractères minimum).", "error")
        return redirect(url_for("project_detail", pid=pid))
    n = q("SELECT COUNT(*) c FROM evaluations WHERE project_id=?", (pid,), one=True)["c"]
    if n < MIN_EVALUATIONS:
        flash(f"Il faut au moins {MIN_EVALUATIONS} évaluations avant de décider ({n} reçue(s)).", "error")
        return redirect(url_for("project_detail", pid=pid))
    ex("INSERT INTO decisions(project_id,decision,motivation,decided_by,decided_at) VALUES (?,?,?,?,?)",
       (pid, decision, motivation, g.user["id"], now()))
    new_status = {"accepte": "incube", "refuse": "refuse", "liste_attente": "liste_attente"}[decision]
    ex("UPDATE projects SET status=? WHERE id=?", (new_status, pid))
    if decision == "accepte":
        cohort = request.form.get("cohort", "").strip() or f"{dt.date.today().year}-A"
        ex("UPDATE projects SET cohort=? WHERE id=?", (cohort, pid))
        start = dt.date.today()
        for kind, months in (("3_mois", 3), ("6_mois", 6)):
            ex("INSERT OR IGNORE INTO followups(project_id,kind,due_date) VALUES (?,?,?)",
               (pid, kind, add_months(start, months).isoformat()))
    flash("Décision enregistrée.", "ok")
    return redirect(url_for("project_detail", pid=pid))


@app.route("/projets/<int:pid>/cloturer", methods=["POST"])
@roles_required("coordonnateur")
def project_close(pid):
    p = get_project(pid)
    if p["status"] != "incube":
        abort(400)
    ex("UPDATE projects SET status='post_incubation' WHERE id=?", (pid,))
    flash("Incubation clôturée : le projet passe en suivi post-incubation.", "ok")
    return redirect(url_for("project_detail", pid=pid))


# --------------------------------------------------------------------------- mentorat, objectifs, jalons
@app.route("/projets/<int:pid>/mentor", methods=["POST"])
@roles_required("coordonnateur")
def assign_mentor(pid):
    p = get_project(pid)
    if p["status"] not in ("incube", "post_incubation"):
        flash("Un mentor se désigne une fois le projet accepté.", "warn")
        return redirect(url_for("project_detail", pid=pid))
    mid = request.form.get("mentor_id", type=int)
    if not q("SELECT 1 FROM users WHERE id=? AND role='mentor'", (mid,), one=True):
        abort(400)
    ex("UPDATE projects SET mentor_id=? WHERE id=?", (mid, pid))
    flash("Mentor affecté.", "ok")
    return redirect(url_for("project_detail", pid=pid))


@app.route("/projets/<int:pid>/objectifs", methods=["POST"])
@login_required
def objective_add(pid):
    p = get_project(pid)
    if not can_manage(p):
        abort(403)
    label = request.form.get("label", "").strip()
    if len(label) < 5:
        flash("Décrivez l'objectif (5 caractères minimum).", "error")
    else:
        ex("INSERT INTO objectives(project_id,label,indicator,due_date,created_by) VALUES (?,?,?,?,?)",
           (pid, label, request.form.get("indicator", "").strip(), request.form.get("due_date") or None, g.user["id"]))
        flash("Objectif ajouté.", "ok")
    return redirect(url_for("project_detail", pid=pid))


def _valid_date(s):
    try:
        dt.date.fromisoformat(s)
        return True
    except (TypeError, ValueError):
        return False


@app.route("/projets/<int:pid>/jalons", methods=["POST"])
@login_required
def milestone_add(pid):
    p = get_project(pid)
    if not can_manage(p):
        abort(403)
    title, due = request.form.get("title", "").strip(), request.form.get("due_date", "")
    if len(title) < 3 or not _valid_date(due):
        flash("Un jalon nécessite un titre et une date valide.", "error")
        return redirect(url_for("project_detail", pid=pid))
    oid = request.form.get("objective_id", type=int)
    if oid and not q("SELECT 1 FROM objectives WHERE id=? AND project_id=?", (oid, pid), one=True):
        oid = None
    ex("INSERT INTO milestones(project_id,objective_id,title,description,due_date,created_by) VALUES (?,?,?,?,?,?)",
       (pid, oid, title, request.form.get("description", "").strip(), due, g.user["id"]))
    flash("Jalon ajouté.", "ok")
    return redirect(url_for("project_detail", pid=pid))


@app.route("/jalons/<int:mid>/statut", methods=["POST"])
@login_required
def milestone_update(mid):
    m = q("SELECT * FROM milestones WHERE id=?", (mid,), one=True)
    if m is None:
        abort(404)
    p = get_project(m["project_id"])
    allowed = can_manage(p) or (g.user["role"] == "porteur" and p["owner_id"] == g.user["id"])
    if not allowed or p["status"] not in ("incube", "post_incubation"):
        abort(403)
    status = request.form.get("status")
    if status not in MILESTONE_STATUS:
        abort(400)
    proof = save_upload(request.files.get("proof"))
    if status == "fait" and not (proof or m["proof_stored"]):
        flash("Joignez une preuve (document, capture, rapport) pour valider un jalon.", "error")
        return redirect(url_for("project_detail", pid=p["id"]))
    if proof:
        ex("UPDATE milestones SET proof_name=?, proof_stored=? WHERE id=?", (proof[0], proof[1], mid))
    ex("UPDATE milestones SET status=?, completed_at=? WHERE id=?",
       (status, now() if status == "fait" else None, mid))
    flash("Jalon mis à jour.", "ok")
    return redirect(url_for("project_detail", pid=p["id"]))


@app.route("/jalons/<int:mid>/preuve")
@login_required
def milestone_proof(mid):
    m = q("SELECT * FROM milestones WHERE id=?", (mid,), one=True)
    if m is None or not m["proof_stored"]:
        abort(404)
    get_project(m["project_id"])
    return send_from_directory(app.config["UPLOAD_DIR"], m["proof_stored"], as_attachment=True,
                               download_name=m["proof_name"])


@app.route("/projets/<int:pid>/commentaires", methods=["POST"])
@login_required
def comment_add(pid):
    get_project(pid)
    body = request.form.get("body", "").strip()
    if len(body) < 2:
        flash("Le commentaire est vide.", "error")
    else:
        ex("INSERT INTO comments(project_id,author_id,body,created_at) VALUES (?,?,?,?)",
           (pid, g.user["id"], body[:2000], now()))
    return redirect(url_for("project_detail", pid=pid) + "#commentaires")


@app.route("/suivis/<int:fid>", methods=["POST"])
@login_required
def followup_save(fid):
    f = q("SELECT * FROM followups WHERE id=?", (fid,), one=True)
    if f is None:
        abort(404)
    p = get_project(f["project_id"])
    if not can_manage(p):
        abort(403)

    def num(key):
        v = request.form.get(key, "").strip()
        return int(v) if v.isdigit() else None
    ex("UPDATE followups SET status='fait', done_date=?, notes=?, jobs=?, revenue=?, funding=? WHERE id=?",
       (today(), request.form.get("notes", "").strip(), num("jobs"), num("revenue"), num("funding"), fid))
    flash("Suivi enregistré.", "ok")
    return redirect(url_for("project_detail", pid=p["id"]))


# --------------------------------------------------------------------------- alertes et tableau de bord
@app.route("/alertes")
@login_required
def alerts():
    u = g.user
    sql = f"""SELECT m.*, p.title AS project, p.id AS pid, o.name AS owner,
              CAST(julianday('now') - julianday(m.due_date) AS INTEGER) AS days_late
              FROM milestones m JOIN projects p ON p.id=m.project_id JOIN users o ON o.id=p.owner_id
              WHERE {late_milestones_sql()}"""
    args = []
    if u["role"] == "mentor":
        sql += " AND p.mentor_id=?"; args.append(u["id"])
    elif u["role"] == "porteur":
        sql += " AND p.owner_id=?"; args.append(u["id"])
    elif u["role"] != "coordonnateur":
        abort(403)
    late = q(sql + " ORDER BY m.due_date", args)
    fsql = """SELECT f.*, p.title AS project, p.id AS pid FROM followups f JOIN projects p ON p.id=f.project_id
              WHERE f.status='a_faire' AND f.due_date <= date('now', '+14 day')"""
    if u["role"] == "mentor":
        fsql += " AND p.mentor_id=?"
    followups = q(fsql + " ORDER BY f.due_date", [u["id"]] if u["role"] == "mentor" else []) \
        if u["role"] in ("coordonnateur", "mentor") else []
    return render_template("alerts.html", late=late, followups=followups)


def dashboard_data(cohort="", domain=""):
    where, args = [], []
    if cohort:
        where.append("cohort=?"); args.append(cohort)
    if domain:
        where.append("domain=?"); args.append(domain)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    wa = (" AND " + " AND ".join(where)) if where else ""
    total = q(f"SELECT COUNT(*) c FROM projects {w}", args, one=True)["c"]
    by_status = {r["status"]: r["c"] for r in q(f"SELECT status, COUNT(*) c FROM projects {w} GROUP BY status", args)}
    by_domain = q(f"SELECT COALESCE(domain,'Non renseigné') d, COUNT(*) c FROM projects {w} GROUP BY d ORDER BY c DESC", args)
    by_cohort = q("""SELECT COALESCE(cohort,'Sans cohorte') k, COUNT(*) total,
                     SUM(status IN ('incube','post_incubation')) accepted FROM projects GROUP BY k ORDER BY k""")
    submitted = sum(by_status.get(s, 0) for s in ("soumis", "en_evaluation", "liste_attente", "refuse", "incube", "post_incubation"))
    decided = sum(by_status.get(s, 0) for s in ("refuse", "incube", "post_incubation", "liste_attente"))
    accepted = by_status.get("incube", 0) + by_status.get("post_incubation", 0)
    ms = q(f"""SELECT COUNT(*) total, SUM(m.status='fait') done,
               SUM(m.status!='fait' AND m.due_date < date('now')) late
               FROM milestones m JOIN projects p ON p.id=m.project_id WHERE 1=1 {wa.replace('cohort', 'p.cohort').replace('domain', 'p.domain')}""",
           args, one=True)
    avg = q(f"""SELECT ROUND(AVG((e.innovation*25.0+e.faisabilite*20+e.impact*25+e.equipe*15+e.marche*15)/5),1) a
                FROM evaluations e JOIN projects p ON p.id=e.project_id WHERE 1=1 {wa.replace('cohort', 'p.cohort').replace('domain', 'p.domain')}""",
            args, one=True)["a"]
    fu = q("""SELECT kind, SUM(status='fait') done, COUNT(*) total, COALESCE(SUM(jobs),0) jobs,
              COALESCE(SUM(revenue),0) revenue, COALESCE(SUM(funding),0) funding FROM followups GROUP BY kind""")
    return dict(total=total, by_status=by_status, by_domain=by_domain, by_cohort=by_cohort,
                submitted=submitted, decided=decided, accepted=accepted,
                acceptance_rate=round(accepted / decided * 100) if decided else None,
                ms=ms, ms_rate=round(ms["done"] / ms["total"] * 100) if ms["total"] else None,
                avg=avg, followups=fu)


@app.route("/tableau-de-bord")
@roles_required("coordonnateur")
def dashboard():
    cohort, domain = request.args.get("cohort", ""), request.args.get("domain", "")
    data = dashboard_data(cohort, domain)
    cohorts = [r["cohort"] for r in q("SELECT DISTINCT cohort FROM projects WHERE cohort IS NOT NULL ORDER BY cohort")]
    pending = q("""SELECT p.id, p.title, p.status, p.submitted_at, o.name owner,
                   (SELECT COUNT(*) FROM evaluations e WHERE e.project_id=p.id) n_eval
                   FROM projects p JOIN users o ON o.id=p.owner_id
                   WHERE p.status IN ('soumis','en_evaluation') ORDER BY p.submitted_at""")
    late = q(f"""SELECT m.title, m.due_date, p.id pid, p.title project FROM milestones m JOIN projects p ON p.id=m.project_id
                 WHERE {late_milestones_sql()} ORDER BY m.due_date LIMIT 8""")
    return render_template("dashboard.html", d=data, cohorts=cohorts, cohort=cohort, domain=domain,
                           pending=pending, late=late, min_evals=MIN_EVALUATIONS)


# --------------------------------------------------------------------------- gestion des utilisateurs
@app.route("/utilisateurs", methods=["GET", "POST"])
@roles_required("coordonnateur")
def users_admin():
    if request.method == "POST":
        f = request.form
        name, email, role = f.get("name", "").strip(), f.get("email", "").strip().lower(), f.get("role")
        pwd = f.get("password", "")
        if role not in ROLES or len(name) < 3 or "@" not in email or len(pwd) < 8:
            flash("Informations invalides (mot de passe : 8 caractères minimum).", "error")
        elif q("SELECT 1 FROM users WHERE email=?", (email,), one=True):
            flash("Cet e-mail existe déjà.", "error")
        else:
            ex("INSERT INTO users(email,name,role,password_hash,created_at) VALUES (?,?,?,?,?)",
               (email, name, role, generate_password_hash(pwd), now()))
            flash("Compte créé.", "ok")
        return redirect(url_for("users_admin"))
    return render_template("users.html", users=q("SELECT * FROM users ORDER BY role, name"))


@app.route("/utilisateurs/<int:uid>/role", methods=["POST"])
@roles_required("coordonnateur")
def user_role(uid):
    role = request.form.get("role")
    if role not in ROLES or uid == g.user["id"]:
        flash("Modification impossible (vous ne pouvez pas changer votre propre rôle).", "error")
    else:
        ex("UPDATE users SET role=? WHERE id=?", (role, uid))
        flash("Rôle mis à jour.", "ok")
    return redirect(url_for("users_admin"))


# --------------------------------------------------------------------------- exports
@app.route("/export/projets.xlsx")
@roles_required("coordonnateur")
def export_xlsx():
    from exports import build_xlsx
    data = build_xlsx(get_db())
    return send_file(io.BytesIO(data), as_attachment=True, download_name=f"incubateur_ciat_{today()}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/export/projets.pdf")
@roles_required("coordonnateur")
def export_list_pdf():
    from exports import build_list_pdf
    return send_file(io.BytesIO(build_list_pdf(get_db(), dashboard_data())), as_attachment=True,
                     download_name=f"synthese_incubateur_{today()}.pdf", mimetype="application/pdf")


@app.route("/projets/<int:pid>/compte-rendu.pdf")
@login_required
def export_report(pid):
    p = get_project(pid)
    if g.user["role"] == "evaluateur" or (g.user["role"] == "porteur" and p["status"] in ("brouillon", "a_completer")):
        abort(403)
    from exports import build_project_pdf
    evs, scores, avg = project_scores(pid)
    pdf = build_project_pdf(get_db(), p, evs, scores, avg, completeness(p), g.user["name"], show_evals=g.user["role"] != "porteur")
    return send_file(io.BytesIO(pdf), as_attachment=True, download_name=f"compte_rendu_projet_{pid}.pdf",
                     mimetype="application/pdf")


# --------------------------------------------------------------------------- IA générative
@app.route("/projets/<int:pid>/ia", methods=["POST"])
@login_required
def ai_assist(pid):
    from ai import KINDS, generate
    p = get_project(pid)
    if g.user["role"] not in ("porteur", "mentor", "coordonnateur"):
        abort(403)
    kind = request.form.get("kind")
    if kind not in KINDS:
        abort(400)
    if kind == "compte_rendu" and g.user["role"] == "porteur":
        abort(403)
    context = dict(
        project=dict(p),
        milestones=[dict(m) for m in q("SELECT * FROM milestones WHERE project_id=? ORDER BY due_date", (pid,))],
        objectives=[dict(o) for o in q("SELECT * FROM objectives WHERE project_id=?", (pid,))],
        scores=project_scores(pid)[2])
    output, mode = generate(kind, context)
    ex("INSERT INTO ai_logs(user_id,project_id,purpose,mode,output,created_at) VALUES (?,?,?,?,?,?)",
       (g.user["id"], pid, kind, mode, output, now()))
    return project_detail(pid, ai_output=(output, mode), ai_kind=KINDS[kind])


# --------------------------------------------------------------------------- erreurs
@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(413)
def http_error(e):
    msgs = {400: "Requête invalide ou session expirée. Rechargez la page.", 403: "Accès refusé.",
            404: "Page introuvable.", 413: "Fichier trop volumineux (5 Mo maximum)."}
    return render_template("error.html", code=e.code, msg=msgs.get(e.code, "Erreur")), e.code


@app.errorhandler(500)
def server_error(_e):
    return render_template("error.html", code=500, msg="Une erreur interne est survenue. Elle a été consignée."), 500


@app.route("/sante")
def health():
    return {"status": "ok"}


if not os.path.exists(app.config["DATABASE"]):
    init_db()
