"""Page Profil : notes, limites, alertes, choix du niveau de risque."""

from __future__ import annotations

import streamlit as st

import etat
import regles
from etat import tr
from textes import t


def _barres(v: int) -> str:
    return "".join(f"<span style='display:inline-block;width:26px;height:8px;border-radius:4px;margin-right:4px;"
                   f"background:{'#1F3A5F' if i < v else '#D6E4F2'}'></span>" for i in range(5))


def _choisir():
    s = st.session_state
    if s.profil_radio is None:            # un second clic désélectionne : on revient au profil recommandé
        s.profil_radio = s.profil_calcule["profil"]
    s.profil_choisi = s.profil_radio
    s.enveloppe = regles.choisir_enveloppe(s.reponses, s.profil_choisi)
    s.delta_actions = s.delta_oblig = 0
    s.explication = None


def afficher():
    if not etat.exiger_profil():
        return
    s = st.session_state
    L = etat.L()
    p = s.profil_calcule
    num = p["profil"]
    etat.entete(tr("Mon profil d'investisseur", "My investor profile"), t("profil_regle", L))

    gauche, droite = st.columns([1.1, 1], gap="large")
    with gauche:
        st.markdown(
            f"<div class='ra-carte' style='background:#EAF2FB;border:none'><div class='ra-note'>{tr('Profil recommandé', 'Recommended profile')}</div>"
            f"<div style='font-size:30px;font-weight:700;color:#1F3A5F'>{etat.nom_profil(num)} <span style='font-size:18px'>· {num}/5</span></div>"
            f"<div style='margin-top:8px'>{_barres(num)}</div></div>", unsafe_allow_html=True)
        noms = t("notes", L)
        lignes = "".join(f"<tr><td style='padding:7px 0;color:#4A5560'>{noms[k]}</td><td>{_barres(v)}</td>"
                         f"<td style='text-align:right;font-weight:650'>{v}/5</td></tr>" for k, v in p["notes"].items())
        st.markdown(f"<div class='ra-carte'><table style='width:100%;font-size:14px'>{lignes}</table></div>",
                    unsafe_allow_html=True)
    with droite:
        alloc = regles.PROFILS[num]["allocation"]
        cls = t("classes", L)
        st.markdown(f"**{tr('Allocation type de ce profil', 'Typical allocation for this profile')}**")
        st.markdown("".join(
            f"<div style='display:flex;align-items:center;gap:10px;font-size:13.5px;margin:5px 0'>"
            f"<span style='width:170px'>{cls[c]}</span><div style='flex:1;background:#EEF1F5;border-radius:4px;height:9px'>"
            f"<div style='width:{w * 100:.0f}%;background:#1F3A5F;height:9px;border-radius:4px'></div></div>"
            f"<span style='width:42px;text-align:right'>{w * 100:.0f} %</span></div>" for c, w in alloc.items() if w > 0),
            unsafe_allow_html=True)
        st.caption(tr(f"Volatilité visée : {regles.PROFILS[num]['vol_min']:.0%} à {regles.PROFILS[num]['vol_max']:.0%} par an.",
                      f"Target volatility: {regles.PROFILS[num]['vol_min']:.0%} to {regles.PROFILS[num]['vol_max']:.0%} a year."))

    if p["plafonds"]:
        elems = p["plafonds"] if L == "fr" else [f"{noms[k]}: {v}/5" for k, v in p["notes"].items() if v < 5]
        st.markdown(f"**{t('plafonds', L)}**")
        st.markdown("<ul style='margin:2px 0 10px;padding-left:20px;line-height:1.55'>"
                    + "".join(f"<li>{x}</li>" for x in elems) + "</ul>", unsafe_allow_html=True)
    for a in p.get("alertes", []):
        st.warning(a)

    with st.container(border=True):
        st.markdown("**" + tr("Choisissez votre niveau de risque", "Choose your risk level") + "**")
        if "profil_radio" not in s:
            s.profil_radio = etat.profil_num()
        st.segmented_control("niveau", [1, 2, 3, 4, 5], key="profil_radio", on_change=_choisir,
                             label_visibility="collapsed", format_func=lambda n: f"{n} · {etat.nom_profil(n)}")
        if etat.profil_num() > num:
            st.warning(tr(f"Vous choisissez un profil plus risqué que celui recommandé ({num}). Vous pouvez perdre plus "
                          "en cas de baisse des marchés ; ce choix sera tracé dans votre dossier.",
                          f"You chose a riskier profile than recommended ({num}). You may lose more if markets fall; "
                          "this choice will be recorded in your file."))
        st.caption(tr("Enveloppe proposée : ", "Proposed wrapper: ") + etat.nom_enveloppe())
    st.button(tr("Voir mon portefeuille", "See my portfolio") + " →", type="primary", on_click=etat.aller,
              args=("portefeuille",), key="btn_profil_suite")
