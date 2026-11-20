"""Page Explication : texte de l'IA (Gemini) relu par un garde-fou, et justification ligne par ligne."""

from __future__ import annotations

import re

import streamlit as st

import etat
import llm
from etat import tr
from textes import t


def _regenerer():
    st.session_state.explication = None


def afficher():
    if not etat.exiger_profil():
        return
    s = st.session_state
    d = etat.dossier_complet()
    etat.entete(t("explication_titre", etat.L()),
                tr("Un texte rédigé pour vous, puis la raison d'être de chaque ligne.", "A text written for you, then the reason for each holding."))
    if s.explication is None:
        with st.spinner("…"):
            s.explication = llm.expliquer(d)
            s.source_explication = llm.derniere_source
    plan_b = str(s.source_explication or "").lower().startswith("plan b")
    if not plan_b and s.explication:
        with st.container(border=True):
            st.markdown(s.explication)
            st.caption(tr("Texte rédigé par IA à partir des seuls chiffres calculés par le robo-advisor ; tout nombre inventé est rejeté.",
                          "AI-written from the robo-advisor's own figures only; any invented number is rejected."))
            st.button(tr("Régénérer", "Regenerate"), on_click=_regenerer, key="btn_regen")
    phrases = d["justifications"]
    if phrases:
        st.info(phrases[0])
    cartes, autres = "", []
    for ph in phrases[1:]:
        m = re.match(r"^(.*?) \(([\d.,]+\s?%)\)\s?:\s?(.*)$", ph, re.S)
        if not m:
            autres.append(ph)
            continue
        nom, poids, txt = m.groups()
        cartes += ("<div class='ra-carte' style='margin:0'><div style='display:flex;justify-content:space-between;gap:8px'>"
                   f"<b style='color:#1B2A41'>{nom}</b><span class='ra-badge' style='background:#EAF2FB;color:#1F3A5F'>{poids}</span></div>"
                   f"<div style='font-size:13px;color:#4A5560;margin-top:4px'>{txt}</div></div>")
    if cartes:
        st.markdown("**" + tr("Pourquoi ces lignes ?", "Why these holdings?") + "**")
        st.markdown(f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:10px'>{cartes}</div>",
                    unsafe_allow_html=True)
    for ph in autres:
        st.write("• " + ph)
    st.caption(tr("Les performances passées ne préjugent pas des performances futures ; les simulations ne sont pas une garantie.",
                  "Past performance does not predict future results; simulations are not a guarantee."))
