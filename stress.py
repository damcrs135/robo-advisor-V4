"""
stress.py — Scénarios de crise appliqués au portefeuille du client

Chaque scénario donne un choc (variation totale, en euros) par grande classe d'actifs.
- Scénarios historiques : ordres de grandeur des baisses de 2007-2009, 2020 et 2022 (indices larges en euros,
  du plus haut au plus bas), arrondis et à recouper avec les données de marché ; ils servent à illustrer, pas à prévoir.
- Scénarios hypothétiques : chocs instantanés construits (hausse de taux de 2 points, krach actions de 30 %).
  Pour la hausse de taux, chaque obligation détenue en direct perd environ sa duration × 2 points.

Pour chaque scénario : perte en % et en euros, contribution de chaque classe, et durée estimée pour revenir
au capital de départ au rendement attendu du portefeuille (hypothèses de simulation.py).
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd

import optimisation
import regles

# Chocs par classe (en décimal). fonds_euros et scpi sont traités à part (pas de cotation quotidienne).
SCENARIOS = {
    "crise_2008": {
        "nom": ("Crise financière 2007-2009", "Global financial crisis 2007-2009"),
        "periode": ("oct. 2007 – mars 2009 (17 mois)", "Oct 2007 – Mar 2009 (17 months)"),
        "type": "historique",
        "recit": ("Faillite de Lehman Brothers, gel du crédit, récession mondiale.",
                  "Lehman Brothers collapse, credit freeze, global recession."),
        "chocs": {"euro_cash": 0.05, "euro_gov": 0.12, "euro_ig": 0.03, "euro_hy": -0.30, "actions_monde": -0.52,
                  "actions_usa": -0.50, "actions_europe": -0.58, "actions_emergents": -0.60, "or": 0.25,
                  "immobilier_cote": -0.65, "fonds_euros": 0.06, "scpi": -0.10},
    },
    "covid_2020": {
        "nom": ("Krach du Covid-19", "Covid-19 crash"),
        "periode": ("19 fév. – 23 mars 2020 (1 mois)", "19 Feb – 23 Mar 2020 (1 month)"),
        "type": "historique",
        "recit": ("Confinements mondiaux, arrêt brutal de l'économie, puis rebond rapide grâce aux banques centrales.",
                  "Global lockdowns, sudden economic stop, then a fast rebound driven by central banks."),
        "chocs": {"euro_cash": 0.0, "euro_gov": -0.01, "euro_ig": -0.07, "euro_hy": -0.18, "actions_monde": -0.33,
                  "actions_usa": -0.33, "actions_europe": -0.37, "actions_emergents": -0.32, "or": -0.03,
                  "immobilier_cote": -0.40, "fonds_euros": 0.0, "scpi": 0.0},
    },
    "taux_2022": {
        "nom": ("Remontée des taux 2022", "2022 rate hikes"),
        "periode": ("janv. – déc. 2022 (12 mois)", "Jan – Dec 2022 (12 months)"),
        "type": "historique",
        "recit": ("Inflation au plus haut depuis 40 ans : les banques centrales relèvent fortement leurs taux, "
                  "actions et obligations baissent ensemble.",
                  "Inflation at a 40-year high: central banks hike sharply, stocks and bonds fall together."),
        "chocs": {"euro_cash": 0.0, "euro_gov": -0.18, "euro_ig": -0.14, "euro_hy": -0.11, "actions_monde": -0.13,
                  "actions_usa": -0.14, "actions_europe": -0.10, "actions_emergents": -0.15, "or": 0.06,
                  "immobilier_cote": -0.35, "fonds_euros": 0.02, "scpi": -0.05},
    },
    "choc_taux": {
        "nom": ("Hausse des taux de 2 points", "Rates up 2 points"),
        "periode": ("choc instantané (hypothèse)", "instant shock (hypothetical)"),
        "type": "hypothetique",
        "recit": ("Les taux d'intérêt montent brutalement de 2 points : le prix des obligations baisse d'autant plus "
                  "que leur échéance est lointaine.",
                  "Interest rates jump by 2 points: bond prices fall, more so for longer maturities."),
        "chocs": {"euro_cash": 0.0, "euro_gov": -0.14, "euro_ig": -0.09, "euro_hy": -0.08, "actions_monde": -0.10,
                  "actions_usa": -0.10, "actions_europe": -0.10, "actions_emergents": -0.12, "or": -0.05,
                  "immobilier_cote": -0.15, "fonds_euros": 0.0, "scpi": -0.10},
        "taux": 0.02,
    },
    "krach_actions": {
        "nom": ("Krach actions de 30 %", "30% equity crash"),
        "periode": ("choc instantané (hypothèse)", "instant shock (hypothetical)"),
        "type": "hypothetique",
        "recit": ("Les marchés actions mondiaux perdent 30 % ; les obligations d'État jouent leur rôle d'amortisseur.",
                  "World equity markets lose 30%; government bonds act as a cushion."),
        "chocs": {"euro_cash": 0.0, "euro_gov": 0.03, "euro_ig": -0.02, "euro_hy": -0.10, "actions_monde": -0.30,
                  "actions_usa": -0.30, "actions_europe": -0.30, "actions_emergents": -0.33, "or": 0.05,
                  "immobilier_cote": -0.20, "fonds_euros": 0.0, "scpi": -0.05},
    },
}


def duration(isin: str) -> float | None:
    """Duration modifiée approchée d'une obligation détenue en direct (échéance résiduelle actualisée)."""
    u = regles.charger_univers()
    l = u.loc[isin]
    if l["type"] != "obligation" or not l["maturite"]:
        return None
    try:
        annees = max((pd.Timestamp(l["maturite"]) - pd.Timestamp(date.today())).days / 365.25, 0.0)
    except (ValueError, TypeError):
        return None
    taux = float(l["taux_annuel_num"]) if l["taux_annuel_num"] == l["taux_annuel_num"] else 0.03
    cp = float(l["coupon"] or 0)
    # Duration de Macaulay approchée (coupon faible -> proche de l'échéance), puis modifiée
    mac = annees if cp <= 0 else (1 + taux) / taux - (1 + taux + annees * (cp - taux)) / (cp * ((1 + taux) ** annees - 1) + taux)
    return max(0.0, min(mac, annees)) / (1 + taux)


def choc_ligne(isin: str, scenario: dict) -> float:
    """Variation de valeur d'une ligne dans un scénario."""
    u = regles.charger_univers()
    sc = u.loc[isin, "sous_classe"]
    chocs = scenario["chocs"]
    if sc in ("fonds_euros", "scpi"):
        return chocs[sc]
    if "taux" in scenario:
        d = duration(isin)
        if d is not None:
            return -d * scenario["taux"]
    melange = optimisation.exposition({isin: 1.0})
    return sum(p * chocs.get(c, 0.0) for c, p in melange.items())


def appliquer(portefeuille: dict, montant: float, cle: str, langue: str = "fr") -> dict:
    """Résultat d'un scénario : perte, contribution par classe, lignes les plus touchées, durée de récupération."""
    s = SCENARIOS[cle]
    i = 1 if langue == "en" else 0
    u = regles.charger_univers()
    lignes = {isin: choc_ligne(isin, s) for isin in portefeuille}
    variation = sum(w * lignes[i_] for i_, w in portefeuille.items())
    par_classe: dict[str, float] = {}
    for isin, w in portefeuille.items():
        c = u.loc[isin, "classe"]
        par_classe[c] = par_classe.get(c, 0.0) + w * lignes[isin]
    _, mu = optimisation.point_portefeuille(portefeuille)
    recup = None
    if variation < 0 and mu > 0:
        recup = math.log(1 / (1 + variation)) / math.log(1 + mu)
    pires = sorted(lignes.items(), key=lambda x: portefeuille[x[0]] * x[1])[:5]
    return {"cle": cle, "nom": s["nom"][i], "periode": s["periode"][i], "recit": s["recit"][i], "type": s["type"],
            "variation": variation, "variation_eur": variation * montant, "valeur_apres": montant * (1 + variation),
            "par_classe": par_classe, "recuperation_ans": recup,
            "pires_lignes": [(u.loc[k, "nom"], v, portefeuille[k] * v * montant) for k, v in pires if v < 0]}


def tous(portefeuille: dict, montant: float, langue: str = "fr") -> list[dict]:
    return [appliquer(portefeuille, montant, cle, langue) for cle in SCENARIOS]
