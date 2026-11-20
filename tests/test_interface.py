"""
Parcours complets dans l'interface, avec le faux Streamlit (tests/banc_streamlit.py).
Vérifie qu'aucune page ne plante, du questionnaire jusqu'à l'espace conseiller, en français et en anglais.
"""
import os
import random
import sys
from pathlib import Path

os.environ["ROBO_HORS_LIGNE"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from banc_streamlit import Banc
from test_parcours import reponses_aleatoires

PAGES = ["accueil", "questionnaire", "profil", "portefeuille", "risques", "projection", "fiscalite", "durabilite",
         "explication", "documents", "conseiller", "methodologie"]


@pytest.fixture
def banc(tmp_path, monkeypatch):
    b = Banc()
    import dossiers
    monkeypatch.setattr(dossiers, "DOSSIER", tmp_path / "dossiers")
    return b


def _remplir(b: Banc, r: dict, par_widgets: bool = False):
    """Remplit le questionnaire étape par étape et valide."""
    import questionnaire as qn
    b.aller("questionnaire")
    L = b.etat["langue"]
    if par_widgets:
        b.choisir(f"montant_{L}", r["montant"])
    else:
        b.etat["brouillon"]["montant"] = r["montant"]
    b.cliquer("btn_suiv")
    for bloc in qn.BLOCS:
        assert b.etat["etape_parcours"] == list(qn.BLOCS).index(bloc) + 1, b.etat.get("_erreur_parcours")
        for q in qn.QUESTIONS:
            if q["bloc"] != bloc:
                continue
            if par_widgets and f"q_{q['id']}_{L}" in b.etat:
                b.choisir(f"q_{q['id']}_{L}", r[q["id"]])
            else:
                b.etat["brouillon"][q["id"]] = r[q["id"]]
        b.cliquer("btn_suiv")
    assert b.etat["etape_parcours"] == len(qn.BLOCS) + 1
    b.cliquer("btn_valider")


def _reponses(graine: int) -> dict:
    r = reponses_aleatoires(random.Random(graine))
    r["patrimoine"] = max(r["patrimoine"], r["montant"])          # sinon le parcours bloque (voulu)
    r["credits"] = r["credits"] if r["credits"] is not None else False
    for q in ("epargne_precaution", "besoin_liquidite"):
        r[q] = bool(r[q])
    return r


@pytest.mark.parametrize("graine", range(6))
def test_parcours_complet(banc, graine):
    b = banc
    b.etat["langue"] = "en" if graine % 2 else "fr"
    b.lancer()
    _remplir(b, _reponses(graine), par_widgets=graine == 0)
    assert b.etat["profil_calcule"], "profil non calculé"
    assert b.page == "profil" or b.etat.get("_cible") is None
    b.aller("profil")
    b.choisir("profil_radio", random.Random(graine).randint(1, 5))     # choix libre du niveau de risque
    for p in PAGES:
        b.aller(p)
    # validation de la recommandation, si aucun contrôle bloquant
    b.aller("portefeuille")
    b.choisir("chk_risques", True)
    if "btn_valider_reco" in b.boutons:
        b.cliquer("btn_valider_reco")
    # espace conseiller
    b.aller("conseiller")
    b.etat["code_conseiller"] = "conseiller"
    b.cliquer("btn_conseiller")
    assert b.etat["conseiller_ok"]
    if b.etat.get("dossier_id"):
        i = b.etat["dossier_id"]
        b.etat[f"statut_{i}"] = "validé"
        b.etat[f"note_{i}"] = "Appel client"
        b.cliquer(f"btn_statut_{i}")
        import dossiers
        assert dossiers.charger(i)["statut"] == "validé"


def test_changer_de_langue_garde_les_reponses(banc):
    b = banc
    b.lancer()
    b.aller("questionnaire")
    b.choisir("montant_fr", 300_000)
    b.cliquer("btn_suiv")
    b.choisir("q_situation_familiale_fr", "couple")
    b.etat["langue"] = "en"
    b.lancer()
    assert b.etat["q_situation_familiale_en"] == "couple"
    assert b.etat["brouillon"]["montant"] == 300_000


def test_montant_superieur_au_patrimoine_bloque(banc):
    b = banc
    b.lancer()
    r = _reponses(1)
    r["montant"], r["patrimoine"] = 500_000, 100_000
    with pytest.raises(AssertionError):
        _remplir(b, r)
    assert "patrimoine" in (b.etat.get("_erreur_parcours") or "") or "wealth" in (b.etat.get("_erreur_parcours") or "")


def test_questions_adaptatives(banc):
    import questionnaire as qn
    from vues import parcours
    b = banc
    b.lancer()
    b.etat["brouillon"].update(credits=False, durabilite="aucune")
    assert not parcours.visible(qn.question("taux_effort")) and not parcours.visible(qn.question("exclusions"))
    b.etat["brouillon"].update(credits=True, durabilite="article 9")
    assert parcours.visible(qn.question("taux_effort")) and parcours.visible(qn.question("exclusions"))


def test_refaire_le_questionnaire(banc):
    b = banc
    b.lancer()
    _remplir(b, _reponses(3))
    b.aller("accueil")
    b.cliquer("btn_res_refaire")
    assert not b.etat["profil_calcule"] and b.etat["brouillon"].get("montant")
