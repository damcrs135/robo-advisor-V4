"""Page Profil : tout l'essentiel visible sans défiler, bouton vers le portefeuille en haut."""

from __future__ import annotations

import streamlit as st

import etat
import regles
from etat import tr
from textes import t

COULEURS = {"actions": "#1F3A5F", "obligations": "#12873F", "monetaire": "#3E7CB1", "diversifiants": "#D85A30",
            "scpi": "#9AA5B1", "actif": "#9CC3E6"}


def _choisir():
    s = st.session_state
    if s.profil_radio is None:            # un second clic désélectionne : on revient au profil recommandé
        s.profil_radio = s.profil_calcule["profil"]
    s.profil_choisi = s.profil_radio
    s.enveloppe = regles.choisir_enveloppe(s.reponses, s.profil_choisi)
    s.delta_actions = s.delta_oblig = 0
    s.explication = None


def _jauge(v: int) -> str:
    return "".join(f"<span style='display:inline-block;width:18px;height:6px;border-radius:3px;margin-right:3px;"
                   f"background:{'#1F3A5F' if i < v else '#D6E4F2'}'></span>" for i in range(5))


def afficher():
    if not etat.exiger_profil():
        return
    s = st.session_state
    L = etat.L()
    p = s.profil_calcule
    num = p["profil"]
    choisi = etat.profil_num()

    # --- En-tête : profil + bouton principal visible tout de suite
    g, d = st.columns([3, 1], vertical_alignment="center")
    with g:
        st.markdown(f"<div class='ra-note'>{tr('Profil recommandé', 'Recommended profile')}</div>"
                    f"<div style='font-size:30px;font-weight:700;color:#1F3A5F;line-height:1.2'>{etat.nom_profil(num)} "
                    f"<span style='font-size:18px'>· {num}/5</span></div>"
                    f"<div class='ra-note'>{t('profil_regle', L)}</div>", unsafe_allow_html=True)
    d.button(tr("Voir mon portefeuille", "See my portfolio") + " →", type="primary", on_click=etat.aller,
             args=("portefeuille",), key="btn_profil_suite", width="stretch")

    # --- Les 4 notes sur une ligne
    noms = t("notes", L)
    etat.rangee_kpi([etat.kpi(noms[k], f"{v}/5", _jauge(v)) for k, v in p["notes"].items()])

    # --- Choix du niveau de risque | allocation type
    g, d = st.columns([1.2, 1], gap="large")
    with g:
        st.markdown(f"**{tr('Choisir mon niveau de risque', 'Choose my risk level')}**")
        if "profil_radio" not in s:
            s.profil_radio = choisi
        st.segmented_control("niveau", [1, 2, 3, 4, 5], key="profil_radio", on_change=_choisir,
                             label_visibility="collapsed", format_func=lambda n: f"{n} · {etat.nom_profil(n)}")
        st.caption(tr("Enveloppe proposée : ", "Proposed wrapper: ") + etat.nom_enveloppe())
        if choisi > num:
            st.warning(tr(f"Profil plus risqué que celui recommandé ({num}) : pertes possibles plus fortes. Ce choix sera tracé dans votre dossier.",
                          f"Riskier than recommended ({num}): larger losses possible. This choice will be recorded."))
    with d:
        prof = regles.PROFILS[choisi]
        alloc = {c: w for c, w in prof["allocation"].items() if w > 0}
        cls = t("classes", L)
        st.markdown(f"**{tr('Allocation type', 'Typical allocation')}** <span class='ra-note'>· {etat.nom_profil(choisi)}</span>",
                    unsafe_allow_html=True)
        st.markdown(
            "<div style='display:flex;height:12px;border-radius:6px;overflow:hidden;margin:6px 0'>"
            + "".join(f"<div style='width:{w * 100:.0f}%;background:{COULEURS[c]}'></div>" for c, w in alloc.items()) + "</div>"
            + "<div class='ra-note'>" + " · ".join(f"<span style='color:{COULEURS[c]}'>●</span> {cls[c]} {w * 100:.0f} %"
                                                    for c, w in alloc.items()) + "</div>"
            + f"<div class='ra-note' style='margin-top:4px'>{tr('Volatilité visée', 'Target volatility')} : "
              f"{prof['vol_min']:.0%} – {prof['vol_max']:.0%} {tr('par an', 'a year')}</div>", unsafe_allow_html=True)

    # --- Limites et alertes en étiquettes, détail repliable
    puces = "".join(f"<span class='ra-badge' style='background:#FFF4DB;color:#8A5A00;font-weight:500'>⚠ {a}</span>"
                    for a in p.get("alertes", []))
    puces += "".join(f"<span class='ra-badge' style='background:#F1F3F6;color:#4A5560;font-weight:500'>{noms[k]} {v}/5</span>"
                     for k, v in p["notes"].items() if v < 5)
    if puces:
        st.markdown(f"<div style='display:flex;gap:6px;flex-wrap:wrap;margin:6px 0'>{puces}</div>", unsafe_allow_html=True)
    if p["plafonds"]:
        with st.expander(tr("Pourquoi ce profil ?", "Why this profile?")):
            elems = p["plafonds"] if L == "fr" else [f"{noms[k]}: {v}/5" for k, v in p["notes"].items() if v < 5]
            for x in elems:
                st.write("• " + x)
