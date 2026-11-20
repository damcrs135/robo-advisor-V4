"""Page Composition et durabilité : secteurs, pays, concentration, et ce que les préférences du client ont changé."""

from __future__ import annotations

import streamlit as st

import esg
import etat
import optimisation
import questionnaire as qn
import regles
from etat import pct, tr


def _barres(valeurs: dict, couleur: str, n: int = 7) -> str:
    items = list(valeurs.items())[:n]
    maxi = max((v for _, v in items), default=1) or 1
    reste = sum(v for _, v in list(valeurs.items())[n:])
    if reste > 0.0005:
        items.append((tr("Autres", "Others"), reste))
    return "".join(
        f"<div style='display:grid;grid-template-columns:150px 1fr 48px;gap:8px;align-items:center;font-size:13px;margin:5px 0'>"
        f"<span style='white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{k}</span>"
        f"<div style='background:#EEF1F5;border-radius:4px;height:8px'><div style='width:{v / maxi * 100:.0f}%;height:8px;"
        f"background:{couleur};border-radius:4px'></div></div><span style='text-align:right'>{v * 100:.0f} %</span></div>"
        for k, v in items)


def _preferences(pf: dict):
    s = st.session_state
    r = s.reponses
    L = etat.L()
    i = 1 if L == "en" else 0
    u = regles.charger_univers()
    excl, filtre = regles.preferences_durables(r)
    pref = qn.libelle("durabilite", r.get("durabilite", "aucune"), L)
    ex_txt = ", ".join(esg.TAGS[e][i] for e in excl) or tr("aucune", "none")
    st.markdown(f"#### {tr('Ce que vos préférences ont changé', 'What your preferences changed')}")
    st.markdown(f"<div class='ra-note' style='margin:-4px 0 8px'>{pref} · {tr('Exclusions', 'Exclusions')} : {ex_txt} · "
                f"{tr('Filtre ESG', 'ESG filter')} : {tr('oui', 'yes') if filtre else tr('non', 'no')}</div>", unsafe_allow_html=True)
    if not excl and not filtre:
        st.info(tr("Vous n'avez exprimé aucune préférence de durabilité : le portefeuille est construit sans filtre. "
                   "Vous pouvez en ajouter en refaisant le questionnaire (bloc E).",
                   "You expressed no sustainability preference: the portfolio is built without screens."))
        return
    base = etat.portefeuille_sans_preferences()
    if not base:
        return
    ecartes = [u.loc[x, "nom"] for x in sorted(base, key=lambda x: -base[x]) if x not in pf]
    _, mu_b = optimisation.point_portefeuille(base)
    _, mu_p = optimisation.point_portefeuille(pf)
    c_b = esg.analyser(base)["intensite_carbone"]
    c_p = esg.analyser(pf)["intensite_carbone"]
    cartes = [
        (tr("Titres écartés", "Holdings removed"),
         (", ".join(ecartes[:4]) + (f" +{len(ecartes) - 4}" if len(ecartes) > 4 else "")) if ecartes else tr("aucun", "none")),
        (tr("Rendement attendu", "Expected return"), f"{pct(mu_b, 2)} → {pct(mu_p, 2)}"),
        (tr("Intensité carbone", "Carbon intensity"), "n.d." if c_b is None or c_p is None else f"{c_b:.0f} → {c_p:.0f}"),
    ]
    st.markdown("<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px'>" + "".join(
        f"<div class='ra-kpi'><div class='ra-kpi-l'>{a}</div><div style='font-size:15px;font-weight:600;margin-top:3px'>{b}</div></div>"
        for a, b in cartes) + "</div>", unsafe_allow_html=True)
    st.caption(tr("Comparaison avec le même portefeuille construit sans aucune préférence (même profil, même enveloppe).",
                  "Compared with the same portfolio built without any preference."))
    if s.note_construction in ("exclusions", "esg"):
        st.warning(tr("Vos préférences n'ont pas pu être appliquées entièrement (univers trop restreint).",
                      "Your preferences could not be fully applied."))


def afficher():
    if not etat.exiger_profil():
        return
    pf = etat.portefeuille_courant()
    L = etat.L()
    c = esg.composition(pf, L)
    a = esg.analyser(pf)
    etat.entete(tr("Composition et durabilité", "Composition & sustainability"),
                tr("Où est investi votre argent, et ce que vos préférences de durabilité y ont changé.",
                   "Where your money is invested, and what your sustainability preferences changed."))
    ic, ref = a["intensite_carbone"], a["reference_monde"]
    ecart_c = None if ic is None else ic / ref - 1
    etat.rangee_kpi([
        etat.kpi(tr("Lignes", "Holdings"), str(c["n_lignes"])),
        etat.kpi(tr("10 premières lignes", "Top 10 holdings"), pct(c["top10"], 0), tr("du portefeuille", "of the portfolio")),
        etat.kpi(tr("Pays", "Countries"), str(c["n_pays"]), tr("hors fonds", "excluding funds")),
        etat.kpi(tr("Carbone vs indice monde", "Carbon vs world index"), "n.d." if ecart_c is None else pct(ecart_c, 0, signe=True),
                 tr(f"{ic:.0f} t CO2e / M€ de CA (estimation)", f"{ic:.0f} t CO2e / €m revenue (estimate)") if ic is not None else "",
                 couleur=etat.VERT if ecart_c is not None and ecart_c <= 0 else "#8A5A00"),
    ])
    g, d = st.columns(2, gap="large")
    with g:
        st.markdown(f"**{tr('Par secteur', 'By sector')}**")
        st.markdown(_barres(c["secteurs"], "#1F3A5F"), unsafe_allow_html=True)
    with d:
        st.markdown(f"**{tr('Par pays', 'By country')}**")
        st.markdown(_barres(c["pays"], "#12873F"), unsafe_allow_html=True)
    st.divider()
    _preferences(pf)
    with st.expander(tr("Détail extra-financier", "Non-financial details")):
        i = 1 if L == "en" else 0
        tags = a["exposition_tags"]
        st.write(tr("Exposition aux secteurs sensibles : ", "Sensitive sectors exposure: ")
                 + (", ".join(f"{esg.TAGS.get(k, (k, k))[i]} {pct(v)}" for k, v in tags.items()) or tr("aucune", "none")))
        st.write(tr("Principales sources d'émissions : ", "Main emission sources: ")
                 + ", ".join(f"{n} ({v:.0f})" for n, v in a["principales_sources"]))
        st.caption(tr("Intensité carbone : estimation par moyenne sectorielle (scopes 1 et 2). En production, elle viendrait d'un "
                      "fournisseur de données (MSCI, Sustainalytics, CDP).", "Carbon intensity: sector-average estimate."))
