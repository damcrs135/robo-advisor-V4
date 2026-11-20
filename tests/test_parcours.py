"""Parcours complets avec des réponses tirées au hasard : rien ne doit planter, les contraintes doivent tenir."""
import os, random, sys
from pathlib import Path

os.environ["ROBO_HORS_LIGNE"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import livrable_excel, livrable_pdf, questionnaire as qn, regles, scoring, simulation, analytics


def reponses_aleatoires(rng):
    r = {}
    for q in qn.QUESTIONS:
        t = q["type"]
        if t == "nombre":
            r[q["id"]] = rng.choice([q["min"], q["defaut"], q["max"], rng.randint(q["min"], min(q["max"], 10 * q["defaut"] + 100))])
        elif t == "choix":
            r[q["id"]] = rng.choice([o[0] for o in q["options"]])
        elif t == "multi":
            r[q["id"]] = rng.sample([o[0] for o in q["options"]], rng.randint(0, len(q["options"])))
        else:
            r[q["id"]] = rng.choice([True, False, None]) if t == "vrai_faux" else rng.choice([True, False])
    r["montant"] = rng.choice([100_000, 250_000, 500_000, 1_000_000])
    return r


@pytest.mark.parametrize("graine", range(120))
def test_parcours_aleatoire(graine, tmp_path):
    rng = random.Random(graine)
    r = reponses_aleatoires(rng)
    p = scoring.calculer_profil(r)
    assert 1 <= p["profil"] <= 5
    num = rng.choice([p["profil"], rng.randint(1, 5)])          # le client peut choisir un profil plus risqué
    env = regles.choisir_enveloppe(r, num)
    excl, esg = regles.preferences_durables(r)
    pf = regles.construire_portefeuille(num, r.get("durabilite", "aucune"), env, horizon=r["horizon"],
                                        zone=r["zone"], exclusions=excl, esg=esg, graine=graine)
    assert abs(sum(pf.values()) - 1) < 1e-6
    assert max(pf.values()) <= regles.MAX_PAR_LIGNE + 1e-9
    u = regles.charger_univers()
    for i in pf:
        for tag in excl:
            assert tag not in str(u.loc[i, "tags"]).split(";")
    horizon = {"<2": 2, "2-5": 5, "5-8": 8, ">8": 15}[r["horizon"]]
    sim = simulation.simuler(pf, r["montant"], r["versement_mensuel"], horizon, r["cible"], n=500)
    assert len(sim["p50"]) == horizon + 1 and sim["p10"][-1] <= sim["p90"][-1]
    ind = analytics.analyser(pf)
    dossier = {"date": "2026-11-09", "langue": rng.choice(["fr", "en"]), "reponses": r, "profil": dict(p, profil_calcule=p["profil"], profil=num),
               "enveloppe": env, "portefeuille": pf, "indicateurs": ind, "simulation": sim, "horizon_ans": horizon,
               "justifications": regles.justifier(pf, dict(r, _profil=num, _enveloppe=env), "fr"), "explication": "Texte."}
    assert os.path.getsize(livrable_excel.generer_excel(dossier, str(tmp_path))) > 5000
    assert os.path.getsize(livrable_pdf.generer_pdf(dossier, str(tmp_path))) > 5000


def test_reponses_vides_ne_plantent_pas():
    p = scoring.calculer_profil({})
    assert p["profil"] == 1


def _prix_synthetiques():
    import numpy as np, pandas as pd
    u = regles.charger_univers()
    idx = pd.bdate_range("2012-01-02", "2026-11-06")
    rng = np.random.default_rng(1)
    tick = sorted({t for t in u["ticker_yahoo"] if t and t != "TODO"} | {analytics.TICKER_SANS_RISQUE})
    return pd.DataFrame({t: 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, len(idx))) for t in tick}, index=idx)


@pytest.mark.parametrize("graine", range(15))
def test_avec_cours(graine):
    """Même parcours mais avec des cours synthétiques : indicateurs, perf par ligne, simulation avec corrélations."""
    rng = random.Random(1000 + graine)
    r = reponses_aleatoires(rng)
    num = rng.randint(1, 5)
    env = regles.choisir_enveloppe(r, num)
    pf = regles.construire_portefeuille(num, "aucune", env, horizon=r["horizon"], zone=r["zone"], graine=graine)
    analytics.definir_prix(_prix_synthetiques())
    try:
        ind = analytics.analyser(pf)
        assert ind["volatilite"] is not None and not any("Frais non renseignés" in a and "Obl" in a for a in ind["avertissements"])
        perf = analytics.perf_lignes(pf)
        assert set(perf.index) == set(pf)
        sim = simulation.simuler(pf, 300_000, 500, 10, 400_000, n=300)
        assert sim["proba_cible"] is not None
    finally:
        analytics.definir_prix(None)
