"""
optimisation.py — Frontière efficiente de Markowitz

Le portefeuille du client est placé sur un graphique risque / rendement, à côté de :
- la frontière efficiente (meilleur rendement attendu pour chaque niveau de volatilité) ;
- les portefeuilles de référence des 5 profils ;
- le portefeuille 60/40.

Méthode (moyenne-variance, sans vente à découvert) :
1. univers = les 10 grandes classes d'actifs des hypothèses de simulation.py (source Amundi, rendements bruts) ;
2. corrélations entre classes = matrice CORRELATIONS ci-dessous (ordres de grandeur de long terme, hypothèse
   pédagogique à affiner avec les cours réels) ;
3. chaque ligne du portefeuille est décomposée sur ces classes (simulation.CORRESPONDANCE) ;
4. la frontière est obtenue en minimisant la variance pour une série de rendements cibles (scipy, SLSQP).
Le fonds en euros (capital garanti, volatilité nulle) peut être ajouté comme actif sans risque de l'assurance-vie.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy.optimize import minimize

import regles
import simulation

CLASSES = ["euro_cash", "euro_gov", "euro_ig", "euro_hy", "actions_monde", "actions_usa",
           "actions_europe", "actions_emergents", "or", "immobilier_cote"]
NOMS = {"euro_cash": ("Monétaire", "Money market"), "euro_gov": ("Obligations d'État", "Government bonds"),
        "euro_ig": ("Obligations d'entreprises", "Corporate bonds"), "euro_hy": ("Haut rendement", "High yield"),
        "actions_monde": ("Actions monde", "World equities"), "actions_usa": ("Actions États-Unis", "US equities"),
        "actions_europe": ("Actions Europe", "European equities"), "actions_emergents": ("Actions émergentes", "EM equities"),
        "or": ("Or", "Gold"), "immobilier_cote": ("Immobilier coté", "Listed real estate"),
        "fonds_euros": ("Fonds en euros", "Euro fund")}

# Corrélations de long terme (ordres de grandeur, hypothèse pédagogique), dans l'ordre de CLASSES.
_C = {
    ("euro_gov", "euro_ig"): 0.80, ("euro_gov", "euro_hy"): 0.20, ("euro_ig", "euro_hy"): 0.60,
    ("actions_monde", "actions_usa"): 0.97, ("actions_monde", "actions_europe"): 0.88,
    ("actions_monde", "actions_emergents"): 0.75, ("actions_usa", "actions_europe"): 0.80,
    ("actions_usa", "actions_emergents"): 0.65, ("actions_europe", "actions_emergents"): 0.70,
    ("immobilier_cote", "actions_monde"): 0.75, ("immobilier_cote", "actions_usa"): 0.70,
    ("immobilier_cote", "actions_europe"): 0.72, ("immobilier_cote", "actions_emergents"): 0.60,
    ("immobilier_cote", "euro_gov"): 0.20, ("immobilier_cote", "euro_ig"): 0.40, ("immobilier_cote", "euro_hy"): 0.60,
    ("or", "euro_gov"): 0.20, ("or", "euro_ig"): 0.20, ("or", "euro_hy"): 0.10, ("or", "immobilier_cote"): 0.15,
}
for _a in ("actions_monde", "actions_usa", "actions_europe", "actions_emergents"):
    _C[("euro_gov", _a)] = 0.0
    _C[("euro_ig", _a)] = 0.30
    _C[("euro_hy", _a)] = 0.70
    _C[("or", _a)] = 0.10
for _a in CLASSES[1:]:
    _C.setdefault(("euro_cash", _a), 0.05)


def _matrice_correlation() -> np.ndarray:
    n = len(CLASSES)
    c = np.eye(n)
    for (a, b), v in _C.items():
        i, j = CLASSES.index(a), CLASSES.index(b)
        c[i, j] = c[j, i] = v
    vals, vecs = np.linalg.eigh(c)                       # matrice semi-définie positive garantie
    c = vecs @ np.diag(np.clip(vals, 1e-6, None)) @ vecs.T
    d = np.sqrt(np.diag(c))
    return c / np.outer(d, d)


CORRELATIONS = _matrice_correlation()
MU = np.array([simulation.HYPOTHESES[c][0] for c in CLASSES])
SIGMA = np.array([simulation.HYPOTHESES[c][1] for c in CLASSES])
COV = np.outer(SIGMA, SIGMA) * CORRELATIONS


def taux_fonds_euros() -> float:
    u = regles.charger_univers()
    return float(u.loc["FONDS-EUROS", "taux_annuel_num"]) if "FONDS-EUROS" in u.index else 0.0265


def exposition(portefeuille: dict) -> dict[str, float]:
    """Décompose un portefeuille {ligne: poids} sur les grandes classes (+ « fonds_euros »)."""
    u = regles.charger_univers()
    expo: dict[str, float] = {}
    for isin, w in portefeuille.items():
        sc = u.loc[isin, "sous_classe"]
        melange = {"fonds_euros": 1.0} if sc == "fonds_euros" else simulation.CORRESPONDANCE.get(sc, {"actions_monde": 1.0})
        for c, p in melange.items():
            expo[c] = expo.get(c, 0.0) + w * p
    return expo


def point(expo: dict[str, float]) -> tuple[float, float]:
    """(volatilité, rendement attendu) d'une exposition par classe."""
    w = np.array([expo.get(c, 0.0) for c in CLASSES])
    mu = float(w @ MU) + expo.get("fonds_euros", 0.0) * taux_fonds_euros()
    vol = float(np.sqrt(max(w @ COV @ w, 0.0)))
    return vol, mu


def point_portefeuille(portefeuille: dict) -> tuple[float, float]:
    return point(exposition(portefeuille))


def _actifs(avec_fonds_euros: bool):
    mu, cov, noms = MU.copy(), COV.copy(), list(CLASSES)
    if avec_fonds_euros:
        mu = np.append(mu, taux_fonds_euros())
        cov = np.pad(cov, ((0, 1), (0, 1)))
        noms.append("fonds_euros")
    return mu, cov, noms


def _min_variance(mu, cov, cible=None, plafond=None):
    n = len(mu)
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    if cible is not None:
        cons.append({"type": "eq", "fun": lambda w: w @ mu - cible})
    bornes = [(0.0, plafond or 1.0)] * n
    res = minimize(lambda w: w @ cov @ w, np.full(n, 1 / n), method="SLSQP", bounds=bornes, constraints=cons,
                   options={"maxiter": 300, "ftol": 1e-12})
    return res.x if res.success else None


@lru_cache(maxsize=4)
def frontiere(avec_fonds_euros: bool = False, n_points: int = 40) -> list[dict]:
    """Points de la frontière efficiente : [{"vol", "mu", "poids": {classe: w}}], du moins au plus risqué."""
    mu, cov, noms = _actifs(avec_fonds_euros)
    w0 = _min_variance(mu, cov)
    mu_min = float(w0 @ mu) if w0 is not None else float(mu.min())
    pts = []
    for cible in np.linspace(mu_min, float(mu.max()), n_points):
        w = _min_variance(mu, cov, float(cible))
        if w is None:
            continue
        w = np.clip(w, 0, None)
        w /= w.sum()
        pts.append({"vol": float(np.sqrt(w @ cov @ w)), "mu": float(w @ mu),
                    "poids": {nom: float(x) for nom, x in zip(noms, w) if x > 1e-4}})
    return pts


def rendement_sur_frontiere(vol: float, avec_fonds_euros: bool = False) -> float | None:
    """Meilleur rendement attendu atteignable sur la frontière pour une volatilité donnée (interpolation)."""
    pts = frontiere(avec_fonds_euros)
    if not pts:
        return None
    vols = np.array([p["vol"] for p in pts])
    mus = np.array([p["mu"] for p in pts])
    if vol <= vols[0]:
        return float(mus[0])
    return float(np.interp(vol, vols, mus))


def portefeuille_max_sharpe() -> dict:
    """Portefeuille tangent : point de la frontière des marchés au meilleur ratio de Sharpe (sans risque = monétaire)."""
    rf = simulation.HYPOTHESES["euro_cash"][0]
    pts = [p for p in frontiere(False) if p["vol"] > 1e-6]
    return max(pts, key=lambda p: (p["mu"] - rf) / p["vol"])


@lru_cache(maxsize=8)
def points_profils(enveloppe: str = "assurance-vie") -> dict[int, tuple[float, float]]:
    """(volatilité, rendement) du portefeuille de référence de chaque profil."""
    res = {}
    for p in regles.PROFILS:
        pf = regles.construire_portefeuille(p, "aucune", enveloppe, horizon=">8", graine=0)
        res[p] = point_portefeuille(pf)
    return res


def point_6040() -> tuple[float, float]:
    return point_portefeuille(simulation.PORTEFEUILLE_6040)


def analyse(portefeuille: dict, enveloppe: str = "assurance-vie") -> dict:
    """Tout ce qu'affiche la page Analyse : position du client, écart à la frontière, références."""
    avec_fe = "FONDS-EUROS" in portefeuille
    vol, mu = point_portefeuille(portefeuille)
    mu_front = rendement_sur_frontiere(vol, avec_fe)
    rf = simulation.HYPOTHESES["euro_cash"][0]
    tangent = portefeuille_max_sharpe()
    return {
        "vol": vol, "mu": mu, "sharpe": (mu - rf) / vol if vol > 0 else None,
        "mu_frontiere": mu_front, "ecart_frontiere": None if mu_front is None else mu - mu_front,
        "frontiere": frontiere(avec_fe), "avec_fonds_euros": avec_fe, "max_sharpe": tangent,
        "profils": points_profils(enveloppe if enveloppe in ("assurance-vie", "PEA", "CTO") else "assurance-vie"),
        "ref_6040": point_6040(), "exposition": exposition(portefeuille), "taux_sans_risque": rf,
    }
