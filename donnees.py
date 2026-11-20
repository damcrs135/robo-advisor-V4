"""
donnees.py — Interrupteur unique de la source des données de marché

Trois positions, choisies avec le réglage ROBO_DONNEES (secrets Streamlit ou variable d'environnement) :

- "demo"   : cours FICTIFS générés ici (2005 à aujourd'hui), réalistes et reproductibles, AUCUN appel internet.
             Actualités et marchés de l'accueil fictifs aussi. Pour les tests et les démonstrations.
- "local"  : vrais cours lus dans data/prix_snapshot.csv (créé par telecharger_prix.py), aucun appel internet.
             Plan B si Yahoo bloque le jour de la présentation.
- "direct" : Yahoo Finance et Google Actualités en temps réel, repli automatique sur la copie locale.

Par défaut : "demo". L'ancien réglage ROBO_HORS_LIGNE=1 équivaut à "local".

Les cours fictifs suivent, pour chaque ligne, le rendement et la volatilité de sa classe d'actifs (hypothèses de
simulation.py), avec un facteur de marché commun, et reproduisent les grandes crises (2008, Covid, 2022) à partir
des chocs de stress.py : les indicateurs, corrélations et stress tests restent cohérents.
"""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache

import numpy as np
import pandas as pd

MODES = ("demo", "local", "direct")
DEBUT = "2005-01-03"
NOMS = {"demo": ("Démo : cours fictifs", "Demo: simulated prices"),
        "local": ("Copie locale des vrais cours", "Local copy of real prices"),
        "direct": ("Temps réel (Yahoo Finance)", "Live (Yahoo Finance)")}


def _reglage(nom: str) -> str | None:
    try:
        import streamlit as st
        if nom in st.secrets:
            return str(st.secrets[nom])
    except Exception:
        pass
    return os.environ.get(nom)


def mode() -> str:
    m = (_reglage("ROBO_DONNEES") or "").strip().lower()
    if m in MODES:
        return m
    if _reglage("ROBO_HORS_LIGNE") == "1":
        return "local"
    return "demo"


def nom_mode(langue: str = "fr") -> str:
    return NOMS[mode()][1 if langue == "en" else 0]


def _graine(texte: str) -> int:
    return int(hashlib.md5(texte.encode()).hexdigest()[:8], 16)


def _classe_ticker(ticker: str) -> str:
    """Classe d'hypothèses (simulation.HYPOTHESES) dominante de la ligne qui porte ce ticker."""
    import optimisation
    import regles
    if ticker == "XEON.DE":
        return "euro_cash"
    u = regles.charger_univers()
    lignes = u.index[u["ticker_yahoo"] == ticker]
    if len(lignes) == 0:
        return "actions_monde"
    expo = optimisation.exposition({lignes[0]: 1.0})
    return max(expo, key=expo.get) if expo else "actions_monde"


@lru_cache(maxsize=1)
def _facteur_marche(n: int) -> np.ndarray:
    return np.random.default_rng(20050103).standard_normal(n)


@lru_cache(maxsize=512)
def _serie(ticker: str, fin: str) -> pd.Series:
    import simulation
    import stress
    jours = pd.bdate_range(DEBUT, fin)
    n = len(jours)
    classe = _classe_ticker(ticker)
    mu, sigma = simulation.HYPOTHESES.get(classe, (0.06, 0.15))
    est_action = classe.startswith("actions")
    import regles
    u = regles.charger_univers()
    titre_vif = bool(((u["ticker_yahoo"] == ticker) & (u["type"] == "action")).any())
    if titre_vif:
        sigma *= 1.6                                  # une action seule est plus volatile que l'indice
    rho = 0.75 if est_action else 0.35 if classe in ("euro_hy", "immobilier_cote") else 0.1
    z = rho * _facteur_marche(n) + np.sqrt(1 - rho ** 2) * np.random.default_rng(_graine(ticker)).standard_normal(n)
    vol_j = sigma / np.sqrt(252)
    r = np.log1p(mu) / 252 - vol_j ** 2 / 2 + vol_j * z
    # Crises historiques : on ajoute une dérive pour retrouver l'ordre de grandeur du choc de stress.py
    for cle, (d0, d1) in {"crise_2008": ("2007-10-09", "2009-03-09"), "covid_2020": ("2020-02-19", "2020-03-23"),
                          "taux_2022": ("2021-12-31", "2022-12-30")}.items():
        masque = (jours >= d0) & (jours <= d1)
        k = int(masque.sum())
        if k:
            choc = stress.SCENARIOS[cle]["chocs"].get(classe, 0.0)
            r[masque] += (np.log1p(choc) - r[masque].sum()) / k
    return pd.Series(100 * np.exp(np.cumsum(r)), index=jours, name=ticker)


def prix_fictifs(tickers: list[str]) -> pd.DataFrame:
    """Table de cours fictifs (une colonne par ticker), du 3 janvier 2005 au dernier jour ouvré."""
    fin = (pd.Timestamp.today().normalize() - pd.offsets.BDay(1)).strftime("%Y-%m-%d")
    tickers = [t for t in tickers if t and t != "TODO"]
    if not tickers:
        return pd.DataFrame()
    return pd.concat([_serie(t, fin) for t in tickers], axis=1)
