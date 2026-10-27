-- Schéma de la base de données - Plateforme de gestion de l'incubateur du CIAT
-- SQLite 3. Les clés étrangères sont activées à chaque connexion (PRAGMA foreign_keys=ON).

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('porteur','evaluateur','mentor','coordonnateur')),
    password_hash TEXT NOT NULL,
    phone         TEXT,
    organisation  TEXT,
    bio           TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    domain       TEXT,
    stage        TEXT,
    team_size    INTEGER,
    summary      TEXT,
    problem      TEXT,
    solution     TEXT,
    target       TEXT,
    cohort       TEXT,
    status       TEXT NOT NULL DEFAULT 'brouillon'
                 CHECK (status IN ('brouillon','a_completer','soumis','en_evaluation',
                                   'liste_attente','refuse','incube','post_incubation')),
    mentor_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at   TEXT NOT NULL,
    submitted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_projects_owner  ON projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    doc_type    TEXT NOT NULL,
    filename    TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    uploaded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evaluations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    evaluator_id INTEGER NOT NULL REFERENCES users(id),
    innovation   INTEGER NOT NULL CHECK (innovation   BETWEEN 0 AND 5),
    faisabilite  INTEGER NOT NULL CHECK (faisabilite  BETWEEN 0 AND 5),
    impact       INTEGER NOT NULL CHECK (impact       BETWEEN 0 AND 5),
    equipe       INTEGER NOT NULL CHECK (equipe       BETWEEN 0 AND 5),
    marche       INTEGER NOT NULL CHECK (marche       BETWEEN 0 AND 5),
    comment      TEXT,
    created_at   TEXT NOT NULL,
    UNIQUE (project_id, evaluator_id)
);

CREATE TABLE IF NOT EXISTS decisions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    decision    TEXT NOT NULL CHECK (decision IN ('accepte','refuse','liste_attente')),
    motivation  TEXT NOT NULL,
    decided_by  INTEGER NOT NULL REFERENCES users(id),
    decided_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS objectives (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    label      TEXT NOT NULL,
    indicator  TEXT,
    due_date   TEXT,
    created_by INTEGER NOT NULL REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS milestones (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    objective_id INTEGER REFERENCES objectives(id) ON DELETE SET NULL,
    title        TEXT NOT NULL,
    description  TEXT,
    due_date     TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'a_faire' CHECK (status IN ('a_faire','en_cours','fait')),
    proof_name   TEXT,
    proof_stored TEXT,
    completed_at TEXT,
    created_by   INTEGER NOT NULL REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_milestones_project ON milestones(project_id);

CREATE TABLE IF NOT EXISTS comments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    milestone_id INTEGER REFERENCES milestones(id) ON DELETE SET NULL,
    author_id    INTEGER NOT NULL REFERENCES users(id),
    body         TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS followups (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL CHECK (kind IN ('3_mois','6_mois')),
    due_date   TEXT NOT NULL,
    done_date  TEXT,
    status     TEXT NOT NULL DEFAULT 'a_faire' CHECK (status IN ('a_faire','fait')),
    notes      TEXT,
    jobs       INTEGER,
    revenue    INTEGER,
    funding    INTEGER,
    UNIQUE (project_id, kind)
);

CREATE TABLE IF NOT EXISTS ai_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    purpose    TEXT NOT NULL,
    mode       TEXT NOT NULL,
    output     TEXT NOT NULL,
    created_at TEXT NOT NULL
);
