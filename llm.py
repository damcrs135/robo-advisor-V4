"""
llm.py — Explication en langage naturel par IA (Amina)

Contrat (section 4.3) :
    expliquer(dossier) -> texte de 150 mots maximum

Principe (section 5.6) :
- on envoie à l'IA uniquement des chiffres déjà calculés ; l'IA ne choisit rien, elle reformule ;
- service : API Gemini (offre gratuite via Google AI Studio) ;
- clé dans les secrets Streamlit (GEMINI_API_KEY), jamais dans le code ;
- garde-fou : si le texte contient un nombre absent des chiffres fournis, il est rejeté ;
- plan B : en cas d'échec (pas de clé, quota, réseau, nombre inventé), on renvoie
  les phrases de justification de regles.py. La démo ne peut pas planter à cause de l'IA.

Modèle : lu dans les secrets (GEMINI_MODEL) ; sinon on essaie la liste MODELES_PAR_DEFAUT.
Les noms de modèles changent souvent : vérifier dans Google AI Studio ceux de l'offre gratuite.
"""

from __future__ import annotations

import os
import re

import regles

MOTS_MAX = 150
MODELES_PAR_DEFAUT = ["gemini-3-flash-preview", "gemini-3.1-flash-lite", "gemini-2.5-flash"]
derniere_source = "aucune"     # "gemini:<modèle>" ou "plan B : <raison>" (affiché sur le site)


def _secret(nom: str) -> str | None:
    """Lit un secret Streamlit, puis une variable d'environnement."""
    try:
        import streamlit as st
        if nom in st.secrets:
            return str(st.secrets[nom])
    except Exception:
        pass
    return os.environ.get(nom)


AVERTISSEMENT = {
    "fr": "Les performances passées ne préjugent pas des performances futures ; les simulations ne sont pas une garantie.",
    "en": "Past performance is no guide to future performance; simulations are not a guarantee.",
}


def _pct(x, langue: str = "fr") -> str:
    """Pourcentage arrondi à l'entier (12 %), avec virgule décimale en français si besoin."""
    if x is None:
        return "n.d." if langue == "fr" else "n/a"
    v = x * 100
    txt = f"{v:.0f} %" if abs(v) >= 9.5 or abs(v - round(v)) < 0.05 else f"{v:.1f} %"
    return txt.replace(".", ",") if langue == "fr" else txt.replace(" %", "%")


def _euros(x, langue: str = "fr") -> str:
    if x is None:
        return "n.d." if langue == "fr" else "n/a"
    return f"{x:,.0f} €".replace(",", " ") if langue == "fr" else f"€{x:,.0f}"


def chiffres_autorises(dossier: dict) -> dict[str, str]:
    """
    Les chiffres, déjà formatés, que l'IA a le droit de citer.
    Les libellés séparent clairement le PASSÉ (historique) et l'AVENIR (simulation),
    pour que l'IA ne présente jamais une performance passée comme un résultat simulé.
    """
    lg = dossier.get("langue", "fr")
    profil = dossier["profil"]
    ind = dossier.get("indicateurs", {}) or {}
    sim = dossier.get("simulation", {}) or {}
    classes = regles.poids_par_classe(dossier["portefeuille"])
    r = dossier.get("reponses", {})
    n = dossier.get("horizon_ans")
    c = {
        "profil (sur 5)": str(profil["profil"]),
        "nom du profil": regles.PROFILS[profil["profil"]]["nom_en" if lg == "en" else "nom"],
        "enveloppe": dossier.get("enveloppe", ""),
        "montant investi": _euros(r.get("montant"), lg),
        "versement mensuel": _euros(r.get("versement_mensuel"), lg),
    }
    noms = {"actions": "part actions", "obligations": "part obligations",
            "monetaire": "part monétaire et fonds en euros", "diversifiants": "part or et immobilier coté",
            "scpi": "part SCPI", "actif": "part fonds gérés activement"}
    for cle, nom in noms.items():
        if classes[cle] > 0:                      # les classes absentes ne sont pas citées
            c[nom] = _pct(classes[cle], lg)
    c["frais moyens annuels"] = _pct(ind.get("ter_moyen"), lg)
    if ind.get("volatilite") is not None:
        c["PASSÉ - volatilité historique"] = _pct(ind["volatilite"], lg)
        c["PASSÉ - pire baisse historique"] = _pct(ind.get("drawdown_max"), lg)
    if sim and n:
        duree = f"{n} an" if n == 1 else f"{n} ans"
        if lg == "en":
            duree = f"{n} year" if n == 1 else f"{n} years"
        c["AVENIR - durée de la simulation"] = duree
        c["AVENIR - capital final scénario défavorable"] = _euros(sim["p10"][-1], lg)
        c["AVENIR - capital final scénario central"] = _euros(sim["p50"][-1], lg)
        c["AVENIR - capital final scénario favorable"] = _euros(sim["p90"][-1], lg)
        c["AVENIR - capital final central d'un portefeuille 60/40 de référence"] = _euros(sim["ref_6040"][-1], lg)
        if sim.get("proba_cible") is not None:
            c["AVENIR - probabilité d'atteindre l'objectif"] = _pct(sim["proba_cible"], lg)
            c["objectif du client"] = _euros(r.get("cible"), lg)
    return c


def construire_prompt(dossier: dict) -> str:
    langue = "anglais" if dossier.get("langue") == "en" else "français"
    lignes = "\n".join(f"- {k} : {v}" for k, v in chiffres_autorises(dossier).items())
    return (
        f"Tu es conseiller en gestion de patrimoine. Écris en {langue}, en {MOTS_MAX - 40} mots au plus, "
        "deux courts paragraphes adressés au client (vouvoiement) :\n"
        "- le premier explique POURQUOI ce portefeuille lui convient : lien entre son profil, son enveloppe "
        "et la répartition (actions pour la croissance, obligations et fonds en euros pour la stabilité…) ;\n"
        "- le second dit ce que montre la simulation : la fourchette de capital final et, s'il y en a une, "
        "la probabilité d'atteindre l'objectif.\n"
        "Règles strictes :\n"
        "1. Cite au plus 6 chiffres, choisis parmi ceux ci-dessous et recopiés tels quels. N'en calcule aucun "
        "autre, n'ajoute aucune date, aucun pourcentage ni montant.\n"
        "2. Les chiffres marqués PASSÉ décrivent l'historique : ne les présente jamais comme un résultat "
        "de la simulation. Les chiffres marqués AVENIR viennent de la simulation.\n"
        "3. Ne recommande aucun produit supplémentaire et ne promets aucun rendement.\n"
        "4. N'ajoute pas d'avertissement final : le site l'ajoute lui-même.\n"
        "5. Pas de titre, pas de liste, pas de markdown.\n\n"
        f"Chiffres calculés par le robo-advisor :\n{lignes}"
    )


def _nombres(texte: str) -> list[float]:
    """Extrait les nombres d'un texte (1 234,5 / 1,234.5 / 12 % …)."""
    t = texte.replace(" ", " ").replace(" ", " ")
    res = []
    # 1re forme : milliers séparés par espace ou virgule (300 000 / 1,234.5) ; 2e forme : 12,7 / 85.0 / 5
    for brut in re.findall(r"\d{1,3}(?:[ ,]\d{3})+(?:[.,]\d+)?(?!\d)|\d+(?:[.,]\d+)?", t):
        s = re.sub(r"[ ,](?=\d{3}(?:\D|$))", "", brut).replace(",", ".")
        try:
            res.append(float(s))
        except ValueError:
            pass
    return res


def verifier_chiffres(texte: str, dossier: dict) -> list[float]:
    """Renvoie les nombres du texte qui ne figurent pas parmi les chiffres autorisés."""
    autorises = set()
    for v in chiffres_autorises(dossier).values():
        for x in _nombres(v):
            autorises.add(round(x, 1))
            autorises.add(round(x))
    autorises.update({1, 2, 3, 4, 5, 10, 50, 90, 60, 40})   # profils, percentiles, 60/40
    return [x for x in _nombres(texte) if round(x, 1) not in autorises and round(x) not in autorises]


def plan_b(dossier: dict) -> str:
    """Phrases fixes de regles.justifier, coupées à 150 mots."""
    reponses = dict(dossier.get("reponses", {}))
    reponses["_profil"] = dossier["profil"]["profil"]
    reponses["_enveloppe"] = dossier.get("enveloppe")
    phrases = dossier.get("justifications") or regles.justifier(dossier["portefeuille"], reponses,
                                                                dossier.get("langue", "fr"))
    return avec_avertissement(" ".join(phrases), dossier.get("langue", "fr"))


def avec_avertissement(texte: str, langue: str = "fr") -> str:
    """Coupe le texte pour que, avertissement compris, il tienne en 150 mots ; l'avertissement n'est jamais coupé."""
    avert = AVERTISSEMENT.get(langue, AVERTISSEMENT["fr"])
    return couper(texte.strip(), MOTS_MAX - len(avert.split())) + "\n\n" + avert


def couper(texte: str, mots: int = MOTS_MAX) -> str:
    m = texte.split()
    return texte if len(m) <= mots else " ".join(m[:mots]).rstrip(",;:") + "…"


def appeler_gemini(prompt: str, cle: str, modeles: list[str]) -> tuple[str, str]:
    """Appelle Gemini en essayant chaque modèle. Renvoie (texte, modèle). Lève une exception si tout échoue."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=cle, http_options=types.HttpOptions(timeout=20_000))
    derniere_erreur = None
    for modele in modeles:
        try:
            rep = client.models.generate_content(
                model=modele, contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=400))
            if rep.text and rep.text.strip():
                return rep.text.strip(), modele
        except Exception as e:      # modèle inconnu, quota, réseau…
            derniere_erreur = e
    raise RuntimeError(f"Aucun modèle Gemini n'a répondu ({derniere_erreur})")


def expliquer(dossier: dict) -> str:
    """Explication de 150 mots maximum ; plan B automatique en cas de problème."""
    global derniere_source
    cle = _secret("GEMINI_API_KEY")
    if not cle:
        derniere_source = "plan B : pas de clé GEMINI_API_KEY"
        return plan_b(dossier)
    modele = _secret("GEMINI_MODEL")
    modeles = [modele] if modele else MODELES_PAR_DEFAUT
    try:
        texte, utilise = appeler_gemini(construire_prompt(dossier), cle, modeles)
    except Exception as e:
        derniere_source = f"plan B : {type(e).__name__}"
        return plan_b(dossier)
    inconnus = verifier_chiffres(texte, dossier)
    if inconnus:
        derniere_source = f"plan B : l'IA a cité des chiffres non fournis ({inconnus[:3]})"
        return plan_b(dossier)
    derniere_source = f"gemini:{utilise}"
    return avec_avertissement(texte, dossier.get("langue", "fr"))
