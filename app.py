"""
app.py — Point d'entrée du robo-advisor (V4)

Lancer en local :  py -m streamlit run app.py

Organisation :
- etat.py           : session, calculs partagés, petits composants visuels ;
- vues/*.py         : une page par fichier (accueil, parcours, profil, portefeuille, risques, projection,
                      fiscalité, durabilité, explication, documents, conseiller, méthodologie) ;
- moteurs métier    : scoring, regles, analytics, simulation, optimisation, stress, fiscalite, esg, conformite,
                      dossiers, livrable_pdf, livrable_excel, llm (sans aucune dépendance à Streamlit).
"""

from __future__ import annotations

import streamlit as st

import etat
from etat import tr
from vues import (accueil, conseiller, documents, durabilite, explication, fiscal, methodologie, parcours,
                  portefeuille, profil, projection, risques)

st.set_page_config(page_title="Robo-advisor patrimonial", page_icon="📈", layout="wide")
etat.initialiser()

# ---------------------------------------------------------------------------
# Style commun
# ---------------------------------------------------------------------------
_FR = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 3 2'><rect width='1' height='2' fill='%23002395'/>"
       "<rect x='1' width='1' height='2' fill='%23fff'/><rect x='2' width='1' height='2' fill='%23ed2939'/></svg>")
_GB = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 60 30'><clipPath id='t'><path d='M30,15 h30 v15 z v15 h-30 z h-30 v-15 z v-15 h30 z'/></clipPath>"
       "<path d='M0,0 v30 h60 v-30 z' fill='%23012169'/><path d='M0,0 L60,30 M60,0 L0,30' stroke='%23fff' stroke-width='6'/>"
       "<path d='M0,0 L60,30 M60,0 L0,30' clip-path='url(%23t)' stroke='%23C8102E' stroke-width='4'/>"
       "<path d='M30,0 v30 M0,15 h60' stroke='%23fff' stroke-width='10'/><path d='M30,0 v30 M0,15 h60' stroke='%23C8102E' stroke-width='6'/></svg>")
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, label {{font-family:'Inter', sans-serif;}}
.block-container {{padding-top:2.2rem; max-width:1280px;}}
.ra-titre {{font-size:28px; font-weight:700; color:#1B2A41; letter-spacing:-.4px; margin:0 0 2px;}}
.ra-sous-titre {{font-size:14px; color:#6B7785; margin:0 0 18px;}}
.ra-kpis {{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin:4px 0 14px;}}
.ra-kpi {{background:#F7F9FB; border:1px solid #E3E8EE; border-radius:12px; padding:12px 14px;}}
.ra-kpi-l {{font-size:12px; color:#6B7785;}}
.ra-kpi-v {{font-size:21px; font-weight:650; line-height:1.25; margin-top:2px;}}
.ra-kpi-a {{font-size:11.5px; color:#6B7785; margin-top:2px;}}
.ra-carte {{border:1px solid #E3E8EE; border-radius:12px; padding:14px 16px; background:#fff; margin-bottom:10px;}}
.ra-badge {{font-size:11.5px; font-weight:600; padding:3px 9px; border-radius:20px; white-space:nowrap;}}
.ra-etapes {{display:flex; gap:6px; margin:0 0 18px; flex-wrap:wrap;}}
.ra-etape {{flex:1; min-width:90px; font-size:12px; color:#6B7785; border-top:4px solid #E3E8EE; padding-top:6px;}}
.ra-etape.fait {{border-color:#9CC3E6; color:#1F3A5F;}}
.ra-etape.actif {{border-color:#1F3A5F; color:#1B2A41; font-weight:650;}}
.ra-note {{font-size:12px; color:#6B7785;}}
.st-key-lang_fr button, .st-key-lang_en button {{width:40px; min-height:28px; padding:0; background-size:cover;
  background-position:center; border:2px solid transparent; border-radius:6px; opacity:.45;}}
.st-key-lang_fr button p, .st-key-lang_en button p {{display:none;}}
.st-key-lang_fr button {{background-image:url("{_FR}");}}
.st-key-lang_en button {{background-image:url("{_GB}");}}
.st-key-lang_{etat.L()} button {{opacity:1; border-color:#1F3A5F;}}
</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
P = {
    "accueil": st.Page(accueil.afficher, title=tr("Accueil", "Home"), icon=":material/home:", url_path="accueil", default=True),
    "parcours": st.Page(parcours.afficher, title=tr("Mon questionnaire", "My questionnaire"), icon=":material/edit_note:", url_path="questionnaire"),
    "profil": st.Page(profil.afficher, title=tr("Mon profil", "My profile"), icon=":material/person:", url_path="profil"),
    "portefeuille": st.Page(portefeuille.afficher, title=tr("Mon portefeuille", "My portfolio"), icon=":material/pie_chart:", url_path="portefeuille"),
    "risques": st.Page(risques.afficher, title=tr("Risques et optimisation", "Risk & optimisation"), icon=":material/monitoring:", url_path="risques"),
    "projection": st.Page(projection.afficher, title=tr("Projection", "Projection"), icon=":material/trending_up:", url_path="projection"),
    "fiscal": st.Page(fiscal.afficher, title=tr("Fiscalité", "Tax"), icon=":material/account_balance:", url_path="fiscalite"),
    "durabilite": st.Page(durabilite.afficher, title=tr("Durabilité", "Sustainability"), icon=":material/eco:", url_path="durabilite"),
    "explication": st.Page(explication.afficher, title=tr("Explication", "Explanation"), icon=":material/forum:", url_path="explication"),
    "documents": st.Page(documents.afficher, title=tr("Mes documents", "My documents"), icon=":material/description:", url_path="documents"),
    "conseiller": st.Page(conseiller.afficher, title=tr("Espace conseiller", "Advisor area"), icon=":material/badge:", url_path="conseiller"),
    "methodologie": st.Page(methodologie.afficher, title=tr("Méthodologie et données", "Methodology & data"), icon=":material/science:", url_path="methodologie"),
}
etat.PAGES.update(P)

navigation = st.navigation({
    "": [P["accueil"]],
    tr("Mon projet", "My plan"): [P["parcours"], P["profil"], P["portefeuille"], P["risques"], P["projection"],
                                  P["fiscal"], P["durabilite"], P["explication"], P["documents"]],
    tr("Espace professionnel", "Professional area"): [P["conseiller"], P["methodologie"]],
})

# Changement de page demandé par un bouton (callback) lors de l'exécution précédente
cible = st.session_state.pop("_cible", None)
if cible in P:
    st.switch_page(P[cible])

# ---------------------------------------------------------------------------
# Barre latérale : langue, état du dossier, avertissement
# ---------------------------------------------------------------------------
with st.sidebar:
    c1, c2, _ = st.columns([1, 1, 3])
    c1.button("FR", key="lang_fr", on_click=lambda: st.session_state.update(langue="fr"))
    c2.button("EN", key="lang_en", on_click=lambda: st.session_state.update(langue="en"))
    if etat.a_un_profil():
        st.markdown(f"<div class='ra-carte' style='padding:10px 12px'><div class='ra-note'>{tr('Votre dossier', 'Your file')}</div>"
                    f"<b>{etat.nom_profil()} · {etat.profil_num()}/5</b><br><span class='ra-note'>{etat.eur(etat.montant())} · "
                    f"{etat.nom_enveloppe()}</span></div>", unsafe_allow_html=True)
    st.caption("⚠️ " + tr("Projet pédagogique de M2 Banque-Finance : ceci n'est pas un conseil en investissement réel.",
                          "Master's student project: this is not real investment advice."))

navigation.run()
