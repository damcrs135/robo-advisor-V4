"""
analytics.py — Indicateurs de risque et rééquilibrage (Aly)

Contrat (section 4.3) :
    analyser(portefeuille) -> {"perf_1a", "perf_3a", "volatilite", "drawdown_max", "sharpe", "ter_moyen", ...}
    alerte_reequilibrage(cible, actuel) -> liste des classes qui dérivent de plus de 5 points

Source des cours, dans l'ordre :
1. yfinance (Yahoo Finance) ;
2. data/prix_snapshot.csv (copie de secours créée par telecharger_prix.py) ;
3. sinon, indicateurs à None et un avertissement — on n'invente aucun chiffre.

Mettre la variable d'environnement ROBO_HORS_LIGNE=1 pour ne jamais appeler Yahoo
(tests, démo sans réseau).

Conventions :
- 252 jours de bourse par an ;
- performances 1/3/5 ans = performance cumulée sur la période (clés *_annualisee en plus) ;
- portefeuille rééquilibré chaque jour à ses poids cibles (simplification d'école) ;
- fonds en euros et SCPI : rendement constant égal au taux saisi dans univers.csv,
  sans volatilité (la valeur d'une part de SCPI n'est pas cotée chaque jour) ;
- une ligne sans historique à une date donnée est retirée et les poids des autres
  lignes sont remis à l'échelle ; la date du premier historique complet est renvoyée.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

import regles

DOSSIER = Path(__file__).resolve().parent
CHEMIN_SNAPSHOT = DOSSIER / "data" / "prix_snapshot.csv"
JOURS = 252
TICKER_SANS_RISQUE = "XEON.DE"     # ETF €STR, sert de taux sans risque (section 5.4)
SEUIL_DERIVE = 0.05

_prix_imposes: pd.DataFrame | None = None   # utilisé par les tests
_cache: dict = {}


# ---------------------------------------------------------------------------
# 1. Chargement des cours
# ---------------------------------------------------------------------------
def definir_prix(prix: pd.DataFrame | None) -> None:
    """Impose une table de prix (tests) ; None pour revenir au fonctionnement normal."""
    global _prix_imposes
    _prix_imposes = prix
    _cache.clear()


def _hors_ligne() -> bool:
    return os.environ.get("ROBO_HORS_LIGNE", "0") == "1"


def _telecharger_yahoo(tickers: list[str], debut: str = "2005-01-01") -> pd.DataFrame:
    """Télécharge les cours de clôture ajustés depuis Yahoo. Lève une exception en cas d'échec."""
    import yfinance as yf

    data = yf.download(tickers, start=debut, auto_adjust=True, progress=False,
                       group_by="column", threads=True, timeout=15)
    if data is None or data.empty:
        raise RuntimeError("Yahoo n'a renvoyé aucune donnée")
    close = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]]
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    if list(close.columns) == ["Close"]:
        close.columns = tickers[:1]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close.dropna(how="all")


def lire_snapshot() -> pd.DataFrame | None:
    """Lit data/prix_snapshot.csv s'il existe."""
    if not CHEMIN_SNAPSHOT.exists():
        return None
    df = pd.read_csv(CHEMIN_SNAPSHOT, index_col=0, parse_dates=True)
    return df.sort_index()


def charger_prix(tickers: list[str]) -> tuple[pd.DataFrame, str]:
    """
    Renvoie (prix, source) avec source = "imposés", "yahoo", "snapshot" ou "aucune".
    Les colonnes sont les tickers demandés ; une colonne absente reste vide.
    """
    tickers = sorted({t for t in tickers if t and t != "TODO"})
    if _prix_imposes is not None:
        return _prix_imposes.reindex(columns=tickers), "imposés"
    cle = tuple(tickers)
    if cle in _cache:
        return _cache[cle]
    prix, source = None, "aucune"
    if not _hors_ligne() and tickers:
        try:
            prix, source = _telecharger_yahoo(tickers), "yahoo"
        except Exception:
            prix = None
    if prix is None or prix.dropna(how="all").empty:
        snap = lire_snapshot()
        if snap is not None:
            prix, source = snap, "snapshot"
    if prix is None:
        prix = pd.DataFrame(columns=tickers, dtype=float)
    res = (prix.reindex(columns=tickers).sort_index(), source)
    _cache[cle] = res
    return res


# ---------------------------------------------------------------------------
# 2. Série de rendements du portefeuille
# ---------------------------------------------------------------------------
def _rendements_lignes(portefeuille: dict, prix: pd.DataFrame) -> pd.DataFrame:
    """Rendements quotidiens de chaque ligne (colonnes = identifiants de l'univers)."""
    u = regles.charger_univers()
    index = prix.dropna(how="all").index
    rend = pd.DataFrame(index=index, dtype=float)
    for isin in portefeuille:
        ligne = u.loc[isin]
        taux = ligne["taux_annuel_num"]
        ticker = ligne["ticker_yahoo"]
        if not pd.isna(taux):                                   # fonds euros, SCPI
            rend[isin] = (1 + taux) ** (1 / JOURS) - 1
        elif ticker in prix.columns and prix[ticker].notna().sum() > 1:
            rend[isin] = prix[ticker].ffill(limit=5).pct_change(fill_method=None)
        else:
            rend[isin] = np.nan
    return rend.iloc[1:] if len(rend) > 1 else rend


def serie_portefeuille(portefeuille: dict, prix: pd.DataFrame | None = None) -> tuple[pd.Series, list[str]]:
    """Rendements quotidiens du portefeuille + avertissements."""
    u = regles.charger_univers()
    if prix is None:
        prix, _ = charger_prix([u.loc[i, "ticker_yahoo"] for i in portefeuille])
    avert = []
    rend = _rendements_lignes(portefeuille, prix)
    if rend.empty:
        return pd.Series(dtype=float), ["Aucun cours disponible."]
    poids = pd.Series(portefeuille)
    sans = [i for i in portefeuille if rend[i].isna().all()]
    if sans:
        noms = ", ".join(u.loc[i, "nom"] for i in sans)
        avert.append(f"Pas d'historique pour : {noms} (exclu des calculs, poids redistribué).")
    dispo = rend.notna()
    # On ne garde que les dates où au moins 90 % du poids des lignes ayant un historique
    # est disponible : sinon les premières années ne refléteraient que quelques lignes.
    avec_histo = [i for i in portefeuille if i not in sans]
    cotees = [i for i in portefeuille if pd.isna(u.loc[i, "taux_annuel_num"])]
    if not avec_histo or (cotees and all(i in sans for i in cotees)):
        return pd.Series(dtype=float), avert
    couverture = dispo[avec_histo].mul(poids[avec_histo], axis=1).sum(axis=1) / poids[avec_histo].sum()
    dispo = dispo[couverture >= 0.9]
    rend = rend.loc[dispo.index]
    if rend.empty:
        return pd.Series(dtype=float), avert + ["Historique commun insuffisant."]
    w = dispo.mul(poids, axis=1)
    w = w.div(w.sum(axis=1), axis=0)
    serie = (rend.fillna(0) * w).sum(axis=1)
    if (couverture < 0.999).any() and (couverture >= 0.9).any():
        avert.append("Sur une partie de l'historique, des lignes récentes manquent : poids remis à l'échelle.")
    return serie, avert


# ---------------------------------------------------------------------------
# 3. Indicateurs
# ---------------------------------------------------------------------------
def _perf(serie: pd.Series, annees: int) -> float | None:
    n = annees * JOURS
    if len(serie) < n * 0.95:
        return None
    return float((1 + serie.iloc[-n:]).prod() - 1)


def _annualiser(perf: float | None, annees: int) -> float | None:
    return None if perf is None else (1 + perf) ** (1 / annees) - 1


def drawdown_max(serie: pd.Series) -> float | None:
    if serie.empty:
        return None
    valeur = (1 + serie).cumprod()
    return float((valeur / valeur.cummax() - 1).min())


def taux_sans_risque(prix: pd.DataFrame | None = None, annees: int = 3) -> float | None:
    """Rendement annualisé de l'ETF €STR sur la période (taux sans risque du Sharpe)."""
    if prix is None or TICKER_SANS_RISQUE not in prix.columns:
        prix, _ = charger_prix([TICKER_SANS_RISQUE])
    s = prix[TICKER_SANS_RISQUE].dropna() if TICKER_SANS_RISQUE in prix.columns else pd.Series(dtype=float)
    n = annees * JOURS
    if len(s) < n * 0.95:
        return None
    return float((s.iloc[-1] / s.iloc[-n]) ** (1 / annees) - 1)


def ter_moyen(portefeuille: dict) -> tuple[float, list[str]]:
    """Frais moyens pondérés. Les lignes sans frais connus (TODO) sont signalées."""
    u = regles.charger_univers()
    total, inconnus = 0.0, []
    for isin, w in portefeuille.items():
        ter = u.loc[isin, "ter_num"]
        if pd.isna(ter):
            if u.loc[isin, "sous_classe"] != "fonds_euros" and u.loc[isin, "type"] != "obligation":
                # (fonds euros : taux déjà net ; obligations en direct : pas de frais de gestion)
                inconnus.append(u.loc[isin, "nom"])
        else:
            total += w * ter
    avert = [f"Frais non renseignés pour : {', '.join(inconnus)}."] if inconnus else []
    return total, avert


def repartition(portefeuille: dict, colonne: str) -> dict:
    u = regles.charger_univers()
    res: dict[str, float] = {}
    for isin, w in portefeuille.items():
        cle = u.loc[isin, colonne]
        res[cle] = res.get(cle, 0.0) + w
    return dict(sorted(res.items(), key=lambda x: -x[1]))


STRESS = {
    "Crise financière 2008": ("2007-10-09", "2009-03-09"),
    "Covid 2020": ("2020-02-19", "2020-03-23"),
    "Hausse des taux 2022": ("2021-12-31", "2022-12-30"),
}


def stress_tests(serie: pd.Series) -> dict:
    """Performance du portefeuille pendant 3 crises (None si l'historique ne couvre pas la période)."""
    res = {}
    for nom, (debut, fin) in STRESS.items():
        s = serie.loc[debut:fin]
        couvre = not s.empty and s.index[0] <= pd.Timestamp(debut) + pd.Timedelta(days=7)
        res[nom] = float((1 + s).prod() - 1) if couvre else None
    return res


def analyser(portefeuille: dict, prix: pd.DataFrame | None = None) -> dict:
    """Calcule les indicateurs du portefeuille (voir le contrat en tête de fichier)."""
    u = regles.charger_univers()
    tickers = [u.loc[i, "ticker_yahoo"] for i in portefeuille] + [TICKER_SANS_RISQUE]
    source = "imposés"
    if prix is None:
        prix, source = charger_prix(tickers)
    serie, avert = serie_portefeuille(portefeuille, prix)
    ter, avert_ter = ter_moyen(portefeuille)
    avert += avert_ter

    res = {"perf_1a": None, "perf_3a": None, "perf_5a": None, "volatilite": None,
           "drawdown_max": None, "sharpe": None, "ter_moyen": ter,
           "repartition_classes": repartition(portefeuille, "classe"),
           "repartition_zones": repartition(portefeuille, "zone"),
           "var_95": None, "stress": {}, "source_prix": source,
           "historique_depuis": None, "avertissements": avert}
    if serie.empty or len(serie) < 60:
        res["avertissements"].append(
            "Cours indisponibles : lancez telecharger_prix.py puis rechargez la page.")
        return res

    res["historique_depuis"] = str(serie.index[0].date())
    res["perf_1a"] = _perf(serie, 1)
    res["perf_3a"] = _perf(serie, 3)
    res["perf_5a"] = _perf(serie, 5)
    res["perf_3a_annualisee"] = _annualiser(res["perf_3a"], 3)
    res["perf_5a_annualisee"] = _annualiser(res["perf_5a"], 5)
    fenetre = serie.iloc[-3 * JOURS:]
    res["volatilite"] = float(fenetre.std() * np.sqrt(JOURS))
    res["drawdown_max"] = drawdown_max(serie.iloc[-5 * JOURS:])
    rf = taux_sans_risque(prix)
    rend_ann = float((1 + fenetre).prod() ** (JOURS / len(fenetre)) - 1)
    if rf is not None and res["volatilite"] > 0:
        res["sharpe"] = (rend_ann - rf) / res["volatilite"]
    else:
        res["avertissements"].append("Sharpe non calculé : historique de l'ETF €STR insuffisant.")
    res["taux_sans_risque"] = rf
    res["var_95"] = float(-np.percentile(fenetre, 5))          # perte journalière dépassée 1 jour sur 20
    res["stress"] = stress_tests(serie)
    res["sri_estime"] = regles.estimer_sri(res["volatilite"])
    return res


def perf_lignes(portefeuille: dict, prix: pd.DataFrame | None = None) -> pd.DataFrame:
    """Performance 1 an et 3 ans de chaque ligne (tableau du portefeuille, étape 6)."""
    u = regles.charger_univers()
    if prix is None:
        prix, _ = charger_prix([u.loc[i, "ticker_yahoo"] for i in portefeuille])
    rend = _rendements_lignes(portefeuille, prix)
    lignes = []
    for isin in portefeuille:
        s = rend[isin].dropna() if isin in rend else pd.Series(dtype=float)
        lignes.append({"isin": isin, "perf_1a": _perf(s, 1), "perf_3a": _perf(s, 3)})
    return pd.DataFrame(lignes).set_index("isin")


def matrice_correlation(portefeuille: dict, prix: pd.DataFrame | None = None) -> pd.DataFrame:
    """Corrélations des rendements quotidiens des lignes cotées (3 dernières années)."""
    u = regles.charger_univers()
    if prix is None:
        prix, _ = charger_prix([u.loc[i, "ticker_yahoo"] for i in portefeuille])
    rend = _rendements_lignes(portefeuille, prix).iloc[-3 * JOURS:]
    cotees = [i for i in portefeuille if pd.isna(u.loc[i, "taux_annuel_num"]) and rend[i].notna().sum() > 60]
    return rend[cotees].corr()
