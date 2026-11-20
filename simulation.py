"""
simulation.py — Simulation Monte Carlo et comparaison 60/40 (Haochen)

Contrat (section 4.3) :
    simuler(portefeuille, montant, versement_mensuel, horizon_ans, cible)
      -> {"p10": [...], "p50": [...], "p90": [...], "proba_cible": 0.72, "ref_6040": [...]}
Les listes donnent la valeur du capital en fin d'année : indice 0 = aujourd'hui, indice n = année n.
Clés supplémentaires : "p10_6040", "p90_6040", "capital_verse", "hypotheses".

Hypothèses de marché (section 5.4 : source publiée, pas seulement le passé récent) :
Amundi Investment Institute, « Capital Market Assumptions — H2 update », août 2026
(point de départ des simulations : 30 juin 2026), horizon 10 ans, rendements nominaux
en devise locale, bruts de frais.
https://research-center.amundi.com/files/nuxeo/dl/6df1bf9d-44de-412e-aa5c-4578e393e8b0
Les chiffres ont été lus dans l'extraction texte du PDF : Haochen doit les recontrôler
dans le tableau original (la ligne immobilier coté était ambiguë).

Méthode :
1. Chaque ligne reçoit le rendement attendu et la volatilité de sa classe d'actifs
   (tableau HYPOTHESES), moins ses frais (TER).
2. Les corrélations entre lignes cotées sont estimées sur 3 ans de cours (analytics).
   Sans cours, on suppose une corrélation de 1 entre toutes les lignes : c'est une
   borne prudente (le risque est surestimé, jamais sous-estimé).
3. Le portefeuille est simulé chaque mois avec un rendement log-normal :
   la médiane croît au rendement attendu, la dispersion suit la volatilité.
4. Les versements mensuels sont ajoutés en fin de mois.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import regles

SOURCE_HYPOTHESES = ("Amundi Investment Institute, Capital Market Assumptions H2 update, "
                     "août 2026, horizon 10 ans")

# (rendement annuel attendu, volatilité annuelle) — bruts de frais
HYPOTHESES = {
    "euro_cash": (0.019, 0.010),
    "euro_gov": (0.037, 0.051),
    "euro_ig": (0.035, 0.050),
    "euro_hy": (0.046, 0.125),
    "actions_monde": (0.079, 0.154),
    "actions_usa": (0.080, 0.158),
    "actions_europe": (0.079, 0.162),
    "actions_emergents": (0.077, 0.162),
    "or": (0.064, 0.145),
    "immobilier_cote": (0.059, 0.121),   # TODO Haochen : ligne ambiguë dans l'extraction, vérifier dans le PDF
}

# Correspondance sous-classe de l'univers -> mélange de classes d'hypothèses.
# Les lignes marquées « approximation » n'ont pas d'équivalent exact dans la source.
CORRESPONDANCE = {
    "monde": {"actions_monde": 1.0},
    "thematique": {"actions_monde": 1.0},                     # approximation : sous-estime le risque d'une thématique
    "usa": {"actions_usa": 1.0},
    "europe": {"actions_europe": 1.0},
    "emergents": {"actions_emergents": 1.0},
    "etat": {"euro_gov": 1.0},
    "etat_court": {"euro_gov": 0.5, "euro_cash": 0.5},        # approximation : pas de ligne 1-3 ans dans la source
    "ig": {"euro_ig": 1.0},
    "haut_rendement": {"euro_hy": 1.0},
    "monetaire": {"euro_cash": 1.0},
    "or": {"or": 1.0},
    "immobilier": {"immobilier_cote": 1.0},
    "scpi": {"immobilier_cote": 1.0},                         # approximation : immobilier coté pour une SCPI
    "patrimonial": {"actions_monde": 0.5, "euro_gov": 0.5},   # approximation : fonds flexible
    "actions_actif": {"actions_monde": 1.0},
}

PORTEFEUILLE_6040 = {"IE00B4L5Y983": 0.60, "IE00B4WXJJ64": 0.40}   # MSCI World + emprunts d'État euro


def hypotheses_ligne(isin: str) -> tuple[float, float]:
    """Rendement attendu net de frais et volatilité d'une ligne."""
    u = regles.charger_univers()
    ligne = u.loc[isin]
    if ligne["sous_classe"] == "fonds_euros":
        # Fonds en euros : taux servi (déjà net de frais de gestion), capital garanti -> volatilité nulle
        return float(ligne["taux_annuel_num"]), 0.0
    melange = CORRESPONDANCE[ligne["sous_classe"]]
    mu = sum(p * HYPOTHESES[c][0] for c, p in melange.items())
    sigma = sum(p * HYPOTHESES[c][1] for c, p in melange.items())   # corrélation 1 à l'intérieur du mélange
    ter = ligne["ter_num"]
    return mu - (0.0 if pd.isna(ter) else float(ter)), sigma


def _correlations(isins: list[str], prix: pd.DataFrame | None) -> tuple[np.ndarray, str]:
    """Matrice de corrélation des lignes. 1 par défaut (prudent) quand l'historique manque."""
    n = len(isins)
    c = np.ones((n, n))
    methode = "corrélation 1 entre toutes les lignes (pas de cours disponibles, hypothèse prudente)"
    try:
        import analytics
        u = regles.charger_univers()
        if prix is None:
            prix, source = analytics.charger_prix([u.loc[i, "ticker_yahoo"] for i in isins])
        rend = analytics._rendements_lignes({i: 1 for i in isins}, prix).iloc[-3 * analytics.JOURS:]
        hist = rend.corr(min_periods=120)
        trouve = False
        for a, ia in enumerate(isins):
            for b, ib in enumerate(isins):
                v = hist.loc[ia, ib] if ia in hist.index and ib in hist.columns else np.nan
                if a != b and not np.isnan(v):
                    c[a, b] = v
                    trouve = True
        if trouve:
            methode = "corrélations historiques sur 3 ans (1 par défaut pour les lignes sans cours)"
    except Exception:
        pass
    # Rendre la matrice semi-définie positive (on coupe les valeurs propres négatives)
    vals, vecs = np.linalg.eigh((c + c.T) / 2)
    c = vecs @ np.diag(np.clip(vals, 0, None)) @ vecs.T
    d = np.sqrt(np.clip(np.diag(c), 1e-12, None))
    c = c / np.outer(d, d)
    return c, methode


def parametres_portefeuille(portefeuille: dict, prix: pd.DataFrame | None = None) -> dict:
    """Rendement attendu (net de frais) et volatilité du portefeuille."""
    isins = list(portefeuille)
    w = np.array([portefeuille[i] for i in isins])
    mus, sigmas = zip(*(hypotheses_ligne(i) for i in isins))
    mus, sigmas = np.array(mus), np.array(sigmas)
    corr, methode = _correlations(isins, prix)
    cov = np.outer(sigmas, sigmas) * corr
    return {"rendement": float(w @ mus), "volatilite": float(np.sqrt(max(w @ cov @ w, 0.0))),
            "methode_correlation": methode, "source": SOURCE_HYPOTHESES}


def _trajectoires(mu: float, sigma: float, montant: float, versement: float, horizon_ans: int,
                  n: int, rng: np.random.Generator) -> np.ndarray:
    """Matrice (n, horizon_ans + 1) des valeurs en fin d'année."""
    mois = horizon_ans * 12
    derive = np.log1p(mu) / 12                      # la médiane du rendement composé vaut mu
    vol = sigma / np.sqrt(12)
    chocs = rng.standard_normal((n, mois)) * vol + derive
    croissance = np.exp(chocs)
    valeurs = np.empty((n, horizon_ans + 1))
    valeurs[:, 0] = montant
    v = np.full(n, float(montant))
    for m in range(mois):
        v = v * croissance[:, m] + versement
        if (m + 1) % 12 == 0:
            valeurs[:, (m + 1) // 12] = v
    return valeurs


def simuler(portefeuille: dict, montant: float, versement_mensuel: float, horizon_ans: int, cible: float,
            n: int = 10_000, graine: int = 42, prix: pd.DataFrame | None = None) -> dict:
    """Simulation Monte Carlo (10 000 trajectoires par défaut). Voir le contrat en tête de fichier."""
    horizon_ans = max(1, int(horizon_ans))
    rng = np.random.default_rng(graine)
    p = parametres_portefeuille(portefeuille, prix)
    traj = _trajectoires(p["rendement"], p["volatilite"], montant, versement_mensuel, horizon_ans, n, rng)
    ref = parametres_portefeuille(PORTEFEUILLE_6040, prix)
    traj_ref = _trajectoires(ref["rendement"], ref["volatilite"], montant, versement_mensuel, horizon_ans,
                             n, np.random.default_rng(graine + 1))
    q = np.percentile(traj, [10, 50, 90], axis=0)
    q_ref = np.percentile(traj_ref, [10, 50, 90], axis=0)
    return {
        "p10": q[0].round(2).tolist(),
        "p50": q[1].round(2).tolist(),
        "p90": q[2].round(2).tolist(),
        "proba_cible": float((traj[:, -1] >= cible).mean()) if cible and cible > 0 else None,
        "ref_6040": q_ref[1].round(2).tolist(),
        "p10_6040": q_ref[0].round(2).tolist(),
        "p90_6040": q_ref[2].round(2).tolist(),
        "capital_verse": [montant + versement_mensuel * 12 * a for a in range(horizon_ans + 1)],
        "hypotheses": {"rendement_portefeuille": p["rendement"], "volatilite_portefeuille": p["volatilite"],
                       "rendement_6040": ref["rendement"], "volatilite_6040": ref["volatilite"],
                       "methode_correlation": p["methode_correlation"], "source": p["source"],
                       "trajectoires": n},
    }


def impact_frais(montant: float, versement_mensuel: float, horizon_ans: int, rendement_brut: float,
                 ter_portefeuille: float, ter_traditionnel: float) -> dict:
    """
    Capital final (scénario médian, sans aléa) avec les frais du portefeuille
    et avec ceux d'une gestion traditionnelle (taux paramétrable, section 5.4).
    """
    def capital(ter):
        r = (1 + rendement_brut - ter) ** (1 / 12) - 1
        v = montant
        for _ in range(int(horizon_ans) * 12):
            v = v * (1 + r) + versement_mensuel
        return v
    a, b = capital(ter_portefeuille), capital(ter_traditionnel)
    return {"capital_portefeuille": a, "capital_traditionnel": b, "ecart": a - b}
