"""
Fonctionnalité d'IA générative : aide à la rédaction (pitch, SWOT, modèle économique,
brouillon de compte rendu).

- Si la variable ANTHROPIC_API_KEY est définie et le paquet `anthropic` installé, la génération
  passe par l'API Claude (mode "claude").
- Sinon, un gabarit local déterministe produit un squelette à partir des données du dossier
  (mode "gabarit"). Cela garantit que la démonstration fonctionne sans clé ni réseau.

Principes de conception (exigence « vérification humaine ») :
  * le texte généré est affiché comme BROUILLON, jamais enregistré automatiquement dans le dossier ;
  * le modèle reçoit l'instruction de ne pas inventer de chiffres absents du dossier ;
  * chaque génération est journalisée (table ai_logs) pour traçabilité.
"""
import os

KINDS = {
    "pitch": "Pitch de 60 secondes",
    "swot": "Analyse SWOT",
    "modele_eco": "Première proposition de modèle économique",
    "plan_action": "Plan d'action à 90 jours",
    "compte_rendu": "Brouillon de compte rendu de suivi",
}

SYSTEM = (
    "Tu es un assistant de l'incubateur du CIAT (ISEP Amadou Trawaré de Diamniadio, Sénégal). "
    "Tu aides à rédiger des documents en français clair et professionnel. "
    "Règles strictes : base-toi UNIQUEMENT sur les informations du dossier fournies ; n'invente aucun chiffre, "
    "nom, partenaire ou fait absent du dossier ; quand une information manque, écris « [à compléter] ». "
    "Reste concis (300 mots maximum). Ton texte est un brouillon qui sera relu et corrigé par un humain."
)

INSTRUCTIONS = {
    "pitch": "Rédige un pitch oral de 60 secondes (problème, solution, cible, ambition, demande).",
    "swot": "Produis une analyse SWOT en quatre rubriques (Forces, Faiblesses, Opportunités, Menaces) avec 3 points maximum chacune.",
    "modele_eco": "Propose un premier modèle économique : segments, proposition de valeur, sources de revenus, canaux, coûts principaux. Signale les hypothèses à valider.",
    "plan_action": "Propose un plan d'action à 90 jours en trois étapes de 30 jours, avec des actions vérifiables.",
    "compte_rendu": "Rédige un brouillon de compte rendu de suivi : avancement, jalons réalisés, retards, points d'attention, prochaines étapes.",
}


def _fact(v):
    return str(v).strip() if v and str(v).strip() else "[à compléter]"


def _dossier_text(ctx):
    p = ctx["project"]
    lines = [
        f"Titre : {_fact(p.get('title'))}", f"Domaine : {_fact(p.get('domain'))}",
        f"Stade : {_fact(p.get('stage'))}", f"Taille de l'équipe : {_fact(p.get('team_size'))}",
        f"Résumé : {_fact(p.get('summary'))}", f"Problème : {_fact(p.get('problem'))}",
        f"Solution : {_fact(p.get('solution'))}", f"Public cible : {_fact(p.get('target'))}",
    ]
    if ctx.get("objectives"):
        lines.append("Objectifs : " + " ; ".join(o["label"] for o in ctx["objectives"]))
    if ctx.get("milestones"):
        lines.append("Jalons : " + " ; ".join(f"{m['title']} ({m['status']}, échéance {m['due_date']})" for m in ctx["milestones"]))
    return "\n".join(lines)


def _template(kind, ctx):
    p = ctx["project"]
    t, prob, sol, tgt = (_fact(p.get(k)) for k in ("title", "problem", "solution", "target"))
    if kind == "pitch":
        return (f"Bonjour, je présente {t}.\n\nLe problème : {prob}\n\nNotre solution : {sol}\n\n"
                f"Nous nous adressons à : {tgt}\n\nÀ ce stade ({_fact(p.get('stage'))}), nous sollicitons l'appui du CIAT "
                "pour [à compléter : besoin précis — mentorat, prototype, financement, premiers clients].")
    if kind == "swot":
        return ("FORCES\n- [à compléter : atout de l'équipe ou de la solution]\n\nFAIBLESSES\n- [à compléter]\n\n"
                "OPPORTUNITÉS\n- Accès à l'accompagnement du CIAT et au réseau de l'ISEP\n- [à compléter : tendance du marché]\n\n"
                "MENACES\n- [à compléter : concurrents, réglementation, financement]")
    if kind == "modele_eco":
        return (f"Segments clients : {tgt}\nProposition de valeur : {sol}\nSources de revenus : [à compléter : abonnement, vente, "
                "commission, prestation]\nCanaux : [à compléter]\nCoûts principaux : [à compléter]\n\n"
                "Hypothèses à valider : consentement à payer, taille réelle du segment, coût d'acquisition.")
    if kind == "plan_action":
        return ("JOURS 1 à 30 : valider le besoin auprès de 5 utilisateurs réels ; formaliser le périmètre minimal.\n"
                "JOURS 31 à 60 : construire et tester un prototype ; consigner les retours.\n"
                "JOURS 61 à 90 : mesurer les résultats, ajuster, préparer la présentation devant le comité.\n"
                "(Squelette générique : à adapter avec le mentor.)")
    ms = ctx.get("milestones", [])
    done = [m["title"] for m in ms if m["status"] == "fait"]
    late = [m["title"] for m in ms if m["status"] != "fait" and m["due_date"] < __import__("datetime").date.today().isoformat()]
    nxt = [m["title"] for m in ms if m["status"] != "fait" and m["title"] not in late]
    return (f"COMPTE RENDU DE SUIVI : {t}\n\nJalons réalisés : {', '.join(done) or 'aucun'}\n"
            f"Jalons en retard : {', '.join(late) or 'aucun'}\nProchaines étapes : {', '.join(nxt) or '[à compléter]'}\n\n"
            "Points d'attention : [à compléter par le mentor]")


def generate(kind, ctx):
    """Retourne (texte, mode)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key, timeout=30)
            msg = client.messages.create(
                model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
                max_tokens=900, system=SYSTEM,
                messages=[{"role": "user", "content": f"{INSTRUCTIONS[kind]}\n\nDOSSIER :\n{_dossier_text(ctx)}"}])
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
            if text:
                return text, "claude"
        except Exception:  # réseau, clé invalide, quota... -> repli sur le gabarit
            pass
    return _template(kind, ctx), "gabarit"
