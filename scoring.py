"""
scoring.py — Calcul du profil de risque

Règle : profil = la plus petite des 4 notes (tolérance, horizon, capacité, connaissances).
C'est la règle prudente des banques.

    calculer_profil(reponses) -> {"profil": 3, "notes": {...}, "plafonds": [...], "alertes": [...],
                                  "nom": "Équilibré", "quiz_score": 4}

Toutes les lectures de réponses sont protégées : une réponse manquante ou inconnue ne fait
jamais planter le calcul (elle est ignorée, ou on prend l'hypothèse la plus prudente).
"""

from __future__ import annotations

import math

import questionnaire as qn

MONTANT_MIN = 100_000
MONTANT_MAX = 1_000_000

NOTE_HORIZON = {"<2": 1, "2-5": 3, "5-8": 4, ">8": 5}
NOMS = {1: "Prudent", 2: "Modéré", 3: "Équilibré", 4: "Dynamique", 5: "Offensif"}


def verifier_montant(montant: float) -> str:
    """Renvoie "trop_bas" (< 100 k€), "trop_haut" (> 1 M€) ou "ok"."""
    if montant < MONTANT_MIN:
        return "trop_bas"
    if montant > MONTANT_MAX:
        return "trop_haut"
    return "ok"


def _moyenne_basse(valeurs: list[int], defaut: int) -> int:
    """Moyenne arrondie à l'entier inférieur (choix prudent), bornée à 1-5."""
    if not valeurs:
        return defaut
    return max(1, min(5, math.floor(sum(valeurs) / len(valeurs))))


def note_tolerance(reponses: dict) -> int:
    """Moyenne des points des questions du bloc D (et des priorités) ; 1 si rien n'est renseigné."""
    if "tolerance" in reponses:
        return max(1, min(5, int(reponses["tolerance"])))
    pts = [p for p in (qn.points_ou_none(q, reponses.get(q)) for q in qn.TOLERANCE) if p is not None]
    return _moyenne_basse(pts, defaut=1)


def note_connaissances(quiz: int, reponses: dict | None = None) -> int:
    """
    Quiz < 3/5 -> 3 ; 3 ou 4/5 -> 4 ; 5/5 -> 5, puis plafonné par l'expérience déclarée
    (ancienneté, fréquence des ordres, niveau estimé).
    """
    note = 3 if quiz < 3 else 4 if quiz < 5 else 5
    pts = [p for p in (qn.points_ou_none(q, (reponses or {}).get(q)) for q in qn.EXPERIENCE) if p is not None]
    if pts:
        note = min(note, _moyenne_basse(pts, 5))
    return note


def part_investie(reponses: dict) -> float | None:
    """Part du patrimoine total placée ici (montant / patrimoine)."""
    patrimoine = reponses.get("patrimoine") or 0
    montant = reponses.get("montant") or 0
    if patrimoine <= 0:
        return None
    return montant / patrimoine


def note_capacite(reponses: dict) -> tuple[int, list[str]]:
    """Capacité à subir des pertes : 5 par défaut, abaissée par chaque fragilité. Renvoie (note, raisons)."""
    note, raisons = 5, []

    def plafond(valeur: int, raison: str):
        nonlocal note
        note = min(note, valeur)
        raisons.append(raison)

    part = part_investie(reponses)
    if reponses.get("epargne_precaution") is False:
        plafond(3, "pas d'épargne de précaution")
    if part is not None and part > 0.5:
        plafond(3, f"{part:.0%} du patrimoine investi ici")
    pts = qn.points_ou_none("taux_effort", reponses.get("taux_effort"))
    if pts is not None and pts < 5:
        plafond(pts, "crédits qui pèsent sur vos revenus")
    for qid, texte in (("statut_pro", "situation professionnelle"), ("stabilite_revenus", "revenus peu stables")):
        pts = qn.points_ou_none(qid, reponses.get(qid))
        if pts is not None and pts < 4:
            plafond(pts, texte)
    age = reponses.get("age")
    if isinstance(age, (int, float)):
        if age >= 75:
            plafond(3, f"âge ({int(age)} ans)")
        elif age >= 65:
            plafond(4, f"âge ({int(age)} ans)")
    if reponses.get("besoin_liquidite"):
        plafond(4, "besoin éventuel de retrait")
    return note, raisons


def calculer_profil(reponses: dict) -> dict:
    """Calcule le profil (1 à 5) à partir du dictionnaire de réponses."""
    quiz = reponses["quiz_score"] if "quiz_score" in reponses else qn.score_quiz(reponses)
    tolerance = note_tolerance(reponses)
    horizon = NOTE_HORIZON.get(reponses.get("horizon"), 1)      # horizon inconnu = le plus court (prudent)
    capacite, raisons_cap = note_capacite(reponses)
    connaissances = note_connaissances(quiz, reponses)

    notes = {"tolerance": tolerance, "horizon": horizon, "capacite": capacite, "connaissances": connaissances}
    profil = min(notes.values())

    plafonds, alertes = [], []
    if horizon < 5:
        plafonds.append(f"Horizon {reponses.get('horizon', '?')} ans : profil limité à {horizon}.")
    if capacite < 5:
        plafonds.append(f"Capacité à subir des pertes ({', '.join(raisons_cap)}) : profil limité à {capacite}.")
    if connaissances < 5:
        plafonds.append(f"Connaissances (quiz {quiz}/5 et expérience) : profil limité à {connaissances}.")
    if tolerance < 5:
        plafonds.append(f"Tolérance au risque déclarée : {tolerance}/5.")

    part = part_investie(reponses)
    if reponses.get("epargne_precaution") is False:
        alertes.append("Constituez d'abord une épargne de précaution disponible à tout moment.")
    if part is not None and part > 1:
        alertes.append("Le montant investi dépasse votre patrimoine déclaré : vérifiez vos réponses.")
    elif part is not None and part > 0.5:
        alertes.append("Plus de la moitié de votre patrimoine serait investie ici : risque de concentration.")
    if reponses.get("credits") and reponses.get("besoin_liquidite"):
        alertes.append("Crédits en cours et besoin de liquidité : gardez une réserve disponible.")
    # Cohérence : on espère beaucoup mais on n'accepte aucune perte
    if reponses.get("rendement_attendu") in ("6-8", ">8") and reponses.get("perte_max") in ("0", "5"):
        alertes.append("Vous espérez un rendement élevé tout en acceptant très peu de pertes : "
                       "ces deux souhaits sont difficiles à concilier.")
    if reponses.get("cible") and reponses.get("montant") and reponses["cible"] < reponses["montant"]:
        alertes.append("Votre objectif chiffré est inférieur au montant investi.")

    return {"profil": profil, "notes": notes, "plafonds": plafonds,
            "alertes": alertes, "nom": NOMS[profil], "quiz_score": quiz}
