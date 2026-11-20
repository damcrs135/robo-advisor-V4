"""Page d'accueil : actualités, résumé du portefeuille, marchés, pédagogie."""

from __future__ import annotations

import hashlib
from datetime import date

import accueil_marche
import etat
import regles
from textes import t


def perf_jour_fictive(isin: str, classe: str) -> float:
    """Performance du jour FICTIVE (démonstration) : stable pour une journée donnée."""
    h = int(hashlib.md5(f"{isin}{date.today().isoformat()}".encode()).hexdigest()[:8], 16)
    x = (h % 2001 - 1000) / 1000
    c = str(classe).lower()
    vol = 0.0005 if c.startswith("mon") else 0.0015 if c.startswith("obl") else 0.009 if c.startswith("act") else 0.007
    return x * vol


def resume():
    if not etat.a_un_profil():
        return None
    try:
        pf = etat.portefeuille_courant()
        u = regles.charger_univers()
        cls = t("classes", etat.L())
        mt = etat.montant()
        pj = sum(w * perf_jour_fictive(i, u.loc[i, "classe"]) for i, w in pf.items())
        return {"perf_jour": (pj * 100, pj * mt), "montant": mt, "profil_num": etat.profil_num(),
                "profil_nom": etat.nom_profil(), "enveloppe": etat.nom_enveloppe(),
                "allocation": {cls[k]: v * 100 for k, v in regles.poids_par_classe(pf).items() if v > 0}}
    except Exception:
        return None


def afficher():
    accueil_marche.afficher_accueil(etat.L(), etat.aller, resume())
