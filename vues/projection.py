"""Page Projection : simulation Monte Carlo, scénarios « et si », impact des frais, probabilité d'atteindre l'objectif."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import etat
import simulation
from etat import eur, pct, tr
from textes import t


def afficher():
    if not etat.exiger_profil():
        return
    s = st.session_state
    r = s.reponses
    L = etat.L()
    etat.entete(tr("Projection de votre capital", "Projection of your capital"),
                tr("10 000 trajectoires simulées à partir d'hypothèses de marché publiées. Modifiez les curseurs pour tester vos scénarios.",
                   "10,000 simulated paths based on published market assumptions. Move the sliders to test scenarios."))
    mini, maxi, _ = etat.HORIZONS.get(r.get("horizon"), (1, 30, 10))
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        s.horizon_ans = c1.slider(t("horizon_sim", L), mini, maxi, int(min(max(s.horizon_ans or maxi, mini), maxi)), key="sl_horizon")
        versement = c2.slider(tr("Versement mensuel (€)", "Monthly contribution (€)"), 0, 5_000,
                              int(min(r.get("versement_mensuel", 0) or 0, 5_000)), 50, key="sl_versement")
        cible = c3.number_input(tr("Objectif (€)", "Target (€)"), 0, 100_000_000, int(r.get("cible", 0) or 0), 10_000, key="ni_cible")
        s.ter_trad = c4.slider(tr("Frais gestion traditionnelle (%/an)", "Traditional fees (% p.a.)"), 0.5, 3.0,
                               float(s.ter_trad), 0.1, key="sl_trad")
    items = etat.items_pf()
    mt = r["montant"]
    with st.spinner("Monte Carlo…"):
        sim = etat.simuler(items, mt, versement, s.horizon_ans, cible)
    ind = etat.analyser(items)
    h = sim["hypotheses"]
    brut = h["rendement_portefeuille"] + ind["ter_moyen"]
    trad = [mt] + [simulation.impact_frais(mt, versement, an, brut, ind["ter_moyen"], s.ter_trad / 100)["capital_traditionnel"]
                   for an in range(1, s.horizon_ans + 1)]
    imp = simulation.impact_frais(mt, versement, s.horizon_ans, brut, ind["ter_moyen"], s.ter_trad / 100)

    etat.rangee_kpi([
        etat.kpi(t("defavorable", L), eur(sim["p10"][-1]), tr("1 chance sur 10 de faire moins", "1 in 10 chance of less")),
        etat.kpi(t("central", L), eur(sim["p50"][-1]), tr("scénario médian", "median scenario"), couleur=etat.BLEU),
        etat.kpi(t("favorable", L), eur(sim["p90"][-1]), tr("1 chance sur 10 de faire plus", "1 in 10 chance of more")),
        etat.kpi(tr("Capital versé", "Capital contributed"), eur(sim["capital_verse"][-1])),
        etat.kpi(tr("Probabilité d'atteindre l'objectif", "Probability of reaching target"),
                 "—" if sim["proba_cible"] is None else pct(sim["proba_cible"], 0),
                 eur(cible) if cible else tr("aucun objectif saisi", "no target set")),
    ])
    debut = pd.Timestamp.today().normalize()
    dates = [debut + pd.DateOffset(years=an) for an in range(s.horizon_ans + 1)]
    fe = "%{y:,.0f} €"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=sim["p90"], name=t("favorable", L), line=dict(width=1, color="#2E7D32"), hovertemplate=fe))
    fig.add_trace(go.Scatter(x=dates, y=sim["p10"], name=t("defavorable", L), fill="tonexty", fillcolor="rgba(46,125,50,0.10)",
                             line=dict(width=1, color="#C62828"), hovertemplate=fe))
    fig.add_trace(go.Scatter(x=dates, y=sim["p50"], name=t("central", L), line=dict(width=3, color="#1F3A5F"), hovertemplate=fe))
    fig.add_trace(go.Scatter(x=dates, y=sim["ref_6040"], name=t("ref_6040", L), line=dict(width=1.5, color="#9AA5B1", dash="dash"),
                             hovertemplate=fe))
    fig.add_trace(go.Scatter(x=dates, y=trad, name=tr("Gestion traditionnelle", "Traditional management") + f" ({s.ter_trad:.1f} %)",
                             line=dict(width=2, color="#D85A30"), hovertemplate=fe))
    fig.add_trace(go.Scatter(x=dates, y=sim["capital_verse"], name=t("verse", L), line=dict(dash="dot", color="#BBBBBB"), hovertemplate=fe))
    if cible:
        fig.add_hline(y=cible, line_dash="dot", line_color="#E65100", annotation_text=tr("Objectif", "Target"),
                      annotation_position="top left")
    fig.update_layout(height=480, margin=dict(t=10, b=10, l=0, r=0), hovermode="x unified",
                      xaxis=dict(tickformat="%Y", dtick="M12" if s.horizon_ans <= 15 else "M24", showgrid=False),
                      yaxis=dict(tickformat=",.0f", ticksuffix=" €", gridcolor="#EEF1F5"), legend=dict(orientation="h", y=-0.12))
    st.plotly_chart(fig, width="stretch", key="fig_projection")

    g, d = st.columns(2, gap="large")
    with g:
        st.markdown("**" + tr("Impact des frais", "Impact of fees") + "**")
        st.write(tr(f"Avec nos frais ({pct(ind['ter_moyen'], 2)} par an), le capital médian atteint {eur(imp['capital_portefeuille'])}. "
                    f"Avec une gestion traditionnelle à {s.ter_trad:.1f} %, il serait de {eur(imp['capital_traditionnel'])}, "
                    f"soit {eur(imp['ecart'])} de moins.",
                    f"With our fees ({pct(ind['ter_moyen'], 2)} a year) the median capital reaches {eur(imp['capital_portefeuille'])}; "
                    f"with traditional management at {s.ter_trad:.1f}% it would be {eur(imp['capital_traditionnel'])}."))
    with d:
        st.markdown("**" + tr("Lecture", "How to read it") + "**")
        st.write(tr("La zone verte contient 8 trajectoires sur 10. Le portefeuille 60/40 (60 % actions monde, 40 % obligations d'État) "
                    "sert de référence de marché.",
                    "The green band holds 8 paths out of 10. The 60/40 portfolio is the market benchmark."))
    with st.expander(t("hypotheses", L)):
        st.write(t("hyp_texte", L, mu=pct(h["rendement_portefeuille"]), vol=pct(h["volatilite_portefeuille"]),
                   n=f"{h['trajectoires']:,}".replace(",", " "), src=h["source"], corr=h["methode_correlation"]))
        st.caption(tr("Les frais de la gestion traditionnelle sont une valeur de démonstration.", "Traditional fees are a demo value."))
