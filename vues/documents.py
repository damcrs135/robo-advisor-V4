"""Page Documents : déclaration d'adéquation (PDF) et fichier Excel complet."""

from __future__ import annotations

import os

import streamlit as st

import esg
import etat
import fiscalite
import livrable_excel
import livrable_pdf
import llm
import optimisation
import stress
from etat import tr
from textes import t


def dossier_enrichi() -> dict:
    """Dossier de base + analyses de la V4 (stress tests, fiscalité, ESG, conformité, Markowitz)."""
    d = etat.dossier_complet()
    r = d["reponses"]
    if not d["explication"]:
        d["explication"] = llm.plan_b(d)
    rendement = d["simulation"]["hypotheses"]["rendement_portefeuille"]
    d["stress"] = stress.tous(d["portefeuille"], r["montant"], d["langue"])
    d["fiscalite"] = fiscalite.comparer(r["montant"], r.get("versement_mensuel", 0), d["horizon_ans"], rendement,
                                        fiscalite.foyer_depuis_reponses(r), d["langue"])
    d["esg"] = esg.analyser(d["portefeuille"])
    d["controles"] = etat.controles()
    vol, mu = optimisation.point_portefeuille(d["portefeuille"])
    d["markowitz"] = {"vol": vol, "mu": mu}
    d["dossier_id"] = st.session_state.get("dossier_id")
    return d


@st.cache_data(show_spinner=False)
def _fichiers(cle: str, _d: dict):
    return livrable_pdf.generer_pdf(_d), livrable_excel.generer_excel(_d)


def afficher():
    if not etat.exiger_profil():
        return
    etat.entete(tr("Mes documents", "My documents"),
                tr("À conserver : ils reprennent votre profil, votre portefeuille et toutes les analyses.",
                   "To keep: your profile, portfolio and all analyses."))
    d = dossier_enrichi()
    cle = f"{etat.items_pf()}-{d['langue']}-{d['horizon_ans']}-{d['profil']['profil']}-{d.get('dossier_id')}-{len(d['explication'])}"
    with st.spinner(tr("Préparation des documents…", "Preparing documents…")):
        chemin_pdf, chemin_xl = _fichiers(cle, d)
    c1, c2 = st.columns(2)
    with c1.container(border=True):
        st.markdown("#### 📄 " + tr("Déclaration d'adéquation (PDF)", "Suitability statement (PDF)"))
        st.caption(tr("Profil, portefeuille, projection, stress tests, fiscalité, durabilité, contrôles et signature.",
                      "Profile, portfolio, projection, stress tests, tax, sustainability, checks and signature."))
        with open(chemin_pdf, "rb") as f:
            st.download_button(t("telech_pdf", etat.L()), f.read(), file_name=os.path.basename(chemin_pdf),
                               mime="application/pdf", width="stretch", key="dl_pdf", type="primary")
    with c2.container(border=True):
        st.markdown("#### 📊 " + tr("Fichier Excel", "Excel file"))
        st.caption(tr("Toutes les données, ligne par ligne, avec graphiques natifs et filtres.",
                      "All data, line by line, with native charts and filters."))
        with open(chemin_xl, "rb") as f:
            st.download_button(t("telech_excel", etat.L()), f.read(), file_name=os.path.basename(chemin_xl),
                               width="stretch", key="dl_excel")
    if not st.session_state.get("dossier_id"):
        st.caption(tr("Astuce : validez votre recommandation sur la page Portefeuille pour obtenir une référence de dossier.",
                      "Tip: validate your recommendation on the Portfolio page to get a file reference."))
