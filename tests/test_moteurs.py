"""Tests des moteurs de la V4 : frontière efficiente, stress tests, fiscalité, ESG, conformité, dossiers."""
import os
import random
import sys
from pathlib import Path

os.environ["ROBO_HORS_LIGNE"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import conformite, dossiers, esg, fiscalite, optimisation, regles, scoring, stress
from test_parcours import reponses_aleatoires


def _pf(p=3, env="assurance-vie", **kw):
    return regles.construire_portefeuille(p, "aucune", env, horizon=">8", graine=1, **kw)


# ------------------------------------------------------------------ Markowitz
def test_frontiere_croissante_et_au_dessus_des_portefeuilles():
    for avec_fe in (False, True):
        pts = optimisation.frontiere(avec_fe)
        assert len(pts) > 20
        vols = [p["vol"] for p in pts]
        mus = [p["mu"] for p in pts]
        assert all(b >= a - 1e-6 for a, b in zip(mus, mus[1:]))
        assert all(b >= a - 1e-4 for a, b in zip(vols, vols[1:]))
        assert all(abs(sum(p["poids"].values()) - 1) < 1e-3 for p in pts)
    for p in range(1, 6):
        a = optimisation.analyse(_pf(p))
        assert a["mu"] <= a["mu_frontiere"] + 1e-3, "un portefeuille ne peut pas battre la frontière"


def test_profils_ordonnes_par_risque():
    pts = optimisation.points_profils("assurance-vie")
    vols = [pts[p][0] for p in range(1, 6)]
    assert vols == sorted(vols)


# ------------------------------------------------------------------ Stress tests
@pytest.mark.parametrize("p", range(1, 6))
def test_stress_bornes_et_ordre(p):
    pf = _pf(p)
    res = {r["cle"]: r for r in stress.tous(pf, 300_000)}
    for r in res.values():
        assert -1 < r["variation"] < 0.5
        assert abs(r["variation_eur"] - r["variation"] * 300_000) < 1e-6
        assert abs(sum(r["par_classe"].values()) - r["variation"]) < 1e-9
    assert res["crise_2008"]["variation"] < 0


def test_stress_plus_fort_pour_profil_offensif():
    v1 = stress.appliquer(_pf(1), 1, "crise_2008")["variation"]
    v5 = stress.appliquer(_pf(5), 1, "crise_2008")["variation"]
    assert v5 < v1


# ------------------------------------------------------------------ Fiscalité
def test_fiscalite_regles():
    r = {x["enveloppe"]: x for x in fiscalite.comparer(100_000, 0, 3, 0.06)}
    assert r["PEA"]["capital_net"] == pytest.approx(r["CTO"]["capital_net"])      # PEA avant 5 ans = PFU
    assert r["CTO"]["taux_effectif"] == pytest.approx(0.314)
    r10 = {x["enveloppe"]: x for x in fiscalite.comparer(100_000, 0, 10, 0.06)}
    assert r10["PEA"]["taux_effectif"] == pytest.approx(0.186)
    assert r10["assurance-vie"]["taux_effectif"] < 0.30
    assert sum(x["meilleur"] for x in r10.values()) == 1


def test_fiscalite_pea_plafond():
    r = {x["enveloppe"]: x for x in fiscalite.comparer(500_000, 0, 10, 0.06)}
    assert 0.186 < r["PEA"]["taux_effectif"] < 0.314
    assert all(x["capital_net"] > x["verse"] for x in r.values())


def test_fiscalite_rendement_negatif():
    r = fiscalite.comparer(200_000, 0, 5, -0.03)
    assert all(x["impots"] == 0 for x in r)


# ------------------------------------------------------------------ ESG
def test_esg_exclusions_visibles():
    a = esg.analyser(_pf(4, "CTO"))
    assert 0 <= a["part_esg"] <= 1 and 0 < a["couverture_carbone"] <= 1
    b = esg.analyser(_pf(4, "CTO", exclusions=["fossiles", "armement", "aerien", "tabac", "alcool", "nucleaire"]))
    assert not b["exposition_tags"]


# ------------------------------------------------------------------ Conformité
@pytest.mark.parametrize("graine", range(40))
def test_conformite_sur_reponses_aleatoires(graine):
    rng = random.Random(graine)
    r = reponses_aleatoires(rng)
    p = scoring.calculer_profil(r)
    num = rng.randint(1, 5)
    env = regles.choisir_enveloppe(r, num)
    excl, e = regles.preferences_durables(r)
    pf = regles.construire_portefeuille(num, r["durabilite"], env, horizon=r["horizon"], exclusions=excl, esg=e, graine=graine)
    c = conformite.controler(r, dict(p, profil_calcule=p["profil"], profil=num), pf, env)
    assert c and all(x["statut"] in ("ok", "attention", "bloquant") for x in c)
    if num > p["profil"]:
        assert any(x["code"] == "RISQUE" and x["statut"] == "attention" for x in c)
    if r["patrimoine"] and r["montant"] > r["patrimoine"]:
        assert conformite.synthese(c) == "bloquant"


# ------------------------------------------------------------------ Dossiers
def test_dossiers_cycle(tmp_path, monkeypatch):
    monkeypatch.setattr(dossiers, "DOSSIER", tmp_path)
    i = dossiers.enregistrer({"profil": 3})
    assert dossiers.charger(i)["statut"] == "à valider"
    dossiers.evenement(i, "Appel client", statut="validé")
    d = dossiers.charger(i)
    assert d["statut"] == "validé" and len(d["journal"]) == 2
    assert [x["id"] for x in dossiers.lister()] == [i]
    with pytest.raises(ValueError):
        dossiers.charger("../../etc/passwd")
