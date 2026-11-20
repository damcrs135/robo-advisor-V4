"""Page Durabilité : préférences du client, part ESG, secteurs sensibles, intensité carbone estimée."""

from __future__ import annotations

import streamlit as st

import esg
import etat
import questionnaire as qn
import regles
from etat import pct, tr


def afficher():
    if not etat.exiger_profil():
        return
    s = st.session_state
    r = s.reponses
    L = etat.L()
    i = 1 if L == "en" else 0
    pf = etat.portefeuille_courant()
    a = esg.analyser(pf)
    excl, filtre = regles.preferences_durables(r)
    etat.entete(tr("Durabilité de votre portefeuille", "Sustainability of your portfolio"),
                tr("Vos préférences de durabilité (exigées par MiFID II depuis 2022) et ce qu'elles changent concrètement.",
                   "Your sustainability preferences (required by MiFID II since 2022) and what they change."))
    pref = qn.libelle("durabilite", r.get("durabilite", "aucune"), L)
    ex_txt = ", ".join(esg.TAGS[e][i] for e in excl) or tr("aucune", "none")
    st.markdown(f"<div class='ra-carte' style='background:#EAF2FB;border:none'><b>{tr('Vos préférences', 'Your preferences')}</b> · "
                f"{pref} · {tr('Exclusions', 'Exclusions')} : {ex_txt} · {tr('Filtre ESG', 'ESG filter')} : "
                f"{tr('oui', 'yes') if filtre else tr('non', 'no')}</div>", unsafe_allow_html=True)
    if s.note_construction in ("exclusions", "esg"):
        st.warning(tr("Vos préférences n'ont pas pu être appliquées entièrement (univers trop restreint) : voir le contrôle "
                      "d'adéquation sur la page Portefeuille.", "Your preferences could not be fully applied."))
    ic = a["intensite_carbone"]
    ref = a["reference_monde"]
    etat.rangee_kpi([
        etat.kpi(tr("Part ESG", "ESG share"), pct(a["part_esg"], 0), tr("lignes retenues par le filtre ESG", "holdings passing the ESG screen")),
        etat.kpi(tr("Intensité carbone", "Carbon intensity"), "n.d." if ic is None else f"{ic:.0f}",
                 tr("t CO2e / M€ de chiffre d'affaires", "t CO2e / €m revenue"),
                 couleur=etat.VERT if ic is not None and ic <= ref else "#8A5A00"),
        etat.kpi(tr("Indice actions monde", "World equity index"), f"{ref}", tr("référence indicative", "indicative benchmark")),
        etat.kpi(tr("Couverture des données", "Data coverage"), pct(a["couverture_carbone"], 0),
                 tr("hors États et or", "excl. sovereigns and gold")),
    ])
    g, d = st.columns(2, gap="large")
    with g:
        st.markdown("**" + tr("Exposition aux secteurs sensibles", "Exposure to sensitive sectors") + "**")
        if a["exposition_tags"]:
            st.markdown("".join(
                f"<div style='display:flex;justify-content:space-between;font-size:13.5px;padding:5px 0;border-bottom:1px solid #EEF1F5'>"
                f"<span>{esg.TAGS.get(k, (k, k))[i]}</span><b>{pct(v)}</b></div>" for k, v in a["exposition_tags"].items()),
                unsafe_allow_html=True)
        else:
            st.success(tr("Aucune ligne dans les secteurs sensibles suivis (fossiles, armement, tabac, alcool, aérien, nucléaire).",
                          "No holding in the tracked sensitive sectors."))
    with d:
        st.markdown("**" + tr("Principales sources d'émissions", "Main emission sources") + "**")
        st.markdown("".join(
            f"<div style='display:flex;justify-content:space-between;font-size:13.5px;padding:5px 0;border-bottom:1px solid #EEF1F5'>"
            f"<span>{n}</span><span>{v:.0f}</span></div>" for n, v in a["principales_sources"]), unsafe_allow_html=True)
        st.caption(tr("Contribution à l'intensité carbone du portefeuille.", "Contribution to portfolio carbon intensity."))
    st.caption(tr("Intensité carbone : estimation par moyenne sectorielle (scopes 1 et 2), ordre de grandeur indicatif. En production, "
                  "elle viendrait d'un fournisseur de données (MSCI, Sustainalytics, CDP). Classification SFDR des fonds : à compléter "
                  "depuis les DIC.", "Carbon intensity: sector-average estimate (scopes 1 and 2). SFDR classification to be completed from KIDs."))
