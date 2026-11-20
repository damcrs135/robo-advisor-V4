"""Page Risques : frontière efficiente de Markowitz et stress tests."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import etat
import optimisation
import regles
import stress
from etat import eur, pct, tr
from textes import t


def _frontiere(a: dict):
    L = etat.L()
    i = 1 if L == "en" else 0
    fig = go.Figure()
    marches = optimisation.frontiere(False)
    fig.add_trace(go.Scatter(x=[p["vol"] * 100 for p in marches], y=[p["mu"] * 100 for p in marches], mode="lines",
                             name=tr("Frontière efficiente (marchés)", "Efficient frontier (markets)"),
                             line=dict(color="#1F3A5F", width=3), hovertemplate="σ %{x:.1f} % · μ %{y:.2f} %<extra></extra>"))
    if a["avec_fonds_euros"]:
        fe = optimisation.frontiere(True)
        fig.add_trace(go.Scatter(x=[p["vol"] * 100 for p in fe], y=[p["mu"] * 100 for p in fe], mode="lines",
                                 name=tr("Frontière avec fonds en euros", "Frontier with euro fund"),
                                 line=dict(color="#3E7CB1", width=2, dash="dash"), hoverinfo="skip"))
    for p, (v, m) in a["profils"].items():
        fig.add_trace(go.Scatter(x=[v * 100], y=[m * 100], mode="markers+text", text=[f"{p}"], textposition="top center",
                                 marker=dict(size=11, color="#9CC3E6", line=dict(color="#1F3A5F", width=1)),
                                 name=tr("Profils de référence", "Reference profiles"), showlegend=p == 1,
                                 hovertemplate=f"{etat.nom_profil(p)}<br>σ %{{x:.1f}} % · μ %{{y:.2f}} %<extra></extra>"))
    v, m = a["ref_6040"]
    fig.add_trace(go.Scatter(x=[v * 100], y=[m * 100], mode="markers", name="60/40",
                             marker=dict(size=11, symbol="diamond", color="#9AA5B1")))
    ms = a["max_sharpe"]
    fig.add_trace(go.Scatter(x=[ms["vol"] * 100], y=[ms["mu"] * 100], mode="markers",
                             name=tr("Meilleur ratio de Sharpe", "Max Sharpe"), marker=dict(size=11, symbol="square", color="#12873F")))
    fig.add_trace(go.Scatter(x=[a["vol"] * 100], y=[a["mu"] * 100], mode="markers", name=tr("Votre portefeuille", "Your portfolio"),
                             marker=dict(size=20, symbol="star", color="#D85A30", line=dict(color="white", width=1))))
    fig.update_layout(height=470, margin=dict(l=0, r=0, t=10, b=0), hovermode="closest",
                      xaxis=dict(title=tr("Volatilité attendue (% par an)", "Expected volatility (% p.a.)"), gridcolor="#EEF1F5", rangemode="tozero"),
                      yaxis=dict(title=tr("Rendement attendu (% par an)", "Expected return (% p.a.)"), gridcolor="#EEF1F5"),
                      legend=dict(orientation="h", y=-0.18))
    st.plotly_chart(fig, width="stretch", key="fig_frontiere")
    noms = optimisation.NOMS
    with st.expander(tr("Composition du portefeuille au meilleur ratio de Sharpe", "Max Sharpe portfolio composition")):
        st.markdown("".join(
            f"<div style='display:flex;gap:10px;align-items:center;font-size:13px;margin:4px 0'><span style='width:190px'>{noms[c][i]}</span>"
            f"<div style='flex:1;background:#EEF1F5;height:8px;border-radius:4px'><div style='width:{w * 100:.0f}%;background:#12873F;height:8px;border-radius:4px'></div></div>"
            f"<span style='width:44px;text-align:right'>{w * 100:.0f} %</span></div>"
            for c, w in sorted(ms["poids"].items(), key=lambda x: -x[1]) if w > 0.005), unsafe_allow_html=True)
        st.caption(tr("Portefeuille théorique sans contrainte de profil ni d'enveloppe : il sert de point de repère, pas de recommandation.",
                      "Unconstrained theoretical portfolio: a benchmark, not a recommendation."))


def _onglet_markowitz():
    a = etat.markowitz(etat.items_pf(), etat.enveloppe())
    ecart = a["ecart_frontiere"]
    etat.rangee_kpi([
        etat.kpi(tr("Rendement attendu", "Expected return"), pct(a["mu"], 2), tr("par an, brut de frais", "p.a., gross of fees")),
        etat.kpi(tr("Volatilité attendue", "Expected volatility"), pct(a["vol"]), tr("écart-type annuel", "annual std. dev.")),
        etat.kpi(tr("Ratio de Sharpe", "Sharpe ratio"), "n.d." if a["sharpe"] is None else f"{a['sharpe']:.2f}",
                 tr(f"sans risque {pct(a['taux_sans_risque'])}", f"risk-free {pct(a['taux_sans_risque'])}")),
        etat.kpi(tr("Écart à la frontière", "Gap to frontier"), "n.d." if ecart is None else f"{ecart * 100:+.2f} pt",
                 tr("rendement perdu à risque égal", "return given up at equal risk"),
                 couleur=etat.VERT if ecart is not None and ecart > -0.003 else "#8A5A00"),
    ])
    _frontiere(a)
    if ecart is not None:
        if ecart > -0.003:
            msg = tr("Votre portefeuille est pratiquement sur la frontière : pour son niveau de risque, il est proche du meilleur rendement attendu possible.",
                     "Your portfolio sits almost on the frontier: close to the best expected return for its risk.")
        else:
            msg = tr(f"À volatilité égale, la frontière offre {abs(ecart) * 100:.2f} point de rendement attendu en plus. Cet écart est le prix des "
                     "contraintes de conseil : plafond de 30 % par ligne, titres vifs à poids égal, SCPI, fonds actifs, préférences du client. "
                     "Un gérant l'accepte en échange d'une meilleure diversification et d'un portefeuille compréhensible.",
                     f"At equal volatility, the frontier offers {abs(ecart) * 100:.2f} more points of expected return: the cost of advisory "
                     "constraints (30% line cap, equal-weighted stocks, SCPI, active funds, client preferences).")
        st.info(msg)
    st.caption(tr("Méthode : moyenne-variance de Markowitz sur 10 classes d'actifs, sans vente à découvert. Rendements et volatilités : "
                  "Amundi, Capital Market Assumptions 2026 (10 ans). Corrélations : ordres de grandeur de long terme (voir Méthodologie).",
                  "Method: Markowitz mean-variance on 10 asset classes, long only. Assumptions: Amundi CMA 2026; long-run correlations."))


def _recup(ans) -> str:
    if ans is None:
        return "—"
    return tr(f"{ans:.1f} ans", f"{ans:.1f} years")


def _onglet_stress():
    mt = etat.montant()
    pf = etat.portefeuille_courant()
    res = stress.tous(pf, mt, etat.L())
    ind = etat.analyser(etat.items_pf())
    lignes = "".join(
        f"<tr><td style='padding:9px 8px'><b>{r['nom']}</b><div class='ra-note'>{r['periode']}</div></td>"
        f"<td style='text-align:right;color:{etat.couleur_signe(r['variation'])};font-weight:650'>{pct(r['variation'], signe=True)}</td>"
        f"<td style='text-align:right'>{eur(r['variation_eur'], signe=True)}</td>"
        f"<td style='text-align:right'>{eur(r['valeur_apres'])}</td>"
        f"<td style='text-align:right'>{_recup(r['recuperation_ans'])}</td></tr>"
        for r in res)
    st.markdown(
        "<div class='ra-carte'><table style='width:100%;font-size:13.5px;border-collapse:collapse'>"
        f"<tr style='color:#6B7785;font-size:12px;border-bottom:1px solid #E3E8EE'><th style='text-align:left;padding:6px 8px'>{tr('Scénario', 'Scenario')}</th>"
        f"<th style='text-align:right'>{tr('Impact', 'Impact')}</th><th style='text-align:right'>{tr('En euros', 'In euros')}</th>"
        f"<th style='text-align:right'>{tr('Valeur après', 'Value after')}</th><th style='text-align:right'>{tr('Temps de récupération', 'Recovery time')}</th></tr>"
        f"{lignes}</table></div>", unsafe_allow_html=True)
    noms = {r["cle"]: r["nom"] for r in res}
    choix = st.segmented_control("scenario", list(noms), format_func=noms.get, default="crise_2008", key="sc_stress",
                                 label_visibility="collapsed") or "crise_2008"
    r = next(x for x in res if x["cle"] == choix)
    g, d = st.columns([1.2, 1], gap="large")
    with g:
        cls = t("classes", etat.L())
        cl = sorted(r["par_classe"].items(), key=lambda x: x[1])
        fig = go.Figure(go.Bar(x=[v * mt for _, v in cl], y=[cls[c] for c, _ in cl], orientation="h",
                               marker_color=["#C0392B" if v < 0 else "#12873F" for _, v in cl],
                               hovertemplate="%{y} : %{x:,.0f} €<extra></extra>"))
        fig.update_layout(height=260, margin=dict(l=0, r=0, t=26, b=0), title=dict(text=tr("Contribution par classe (€)", "Contribution by class (€)"),
                          font=dict(size=13)), xaxis=dict(gridcolor="#EEF1F5", tickformat=",.0f"))
        st.plotly_chart(fig, width="stretch", key="fig_stress")
    with d:
        st.markdown(f"**{r['nom']}** · <span class='ra-note'>{r['periode']}</span>", unsafe_allow_html=True)
        st.write(r["recit"])
        if r["pires_lignes"]:
            st.markdown(f"<div class='ra-note' style='margin-top:6px'>{tr('Lignes les plus touchées', 'Most affected holdings')}</div>"
                        + "".join(f"<div style='display:flex;justify-content:space-between;font-size:13px;padding:3px 0;border-bottom:1px solid #EEF1F5'>"
                                  f"<span>{n}</span><span style='color:#C0392B'>{pct(v, 0, signe=True)} · {eur(e)}</span></div>"
                                  for n, v, e in r["pires_lignes"]), unsafe_allow_html=True)
    reels = {k: v for k, v in (ind.get("stress") or {}).items() if v is not None}
    if reels:
        st.markdown("**" + tr("Contrôle sur les cours réels du portefeuille", "Check against actual prices") + "**")
        st.write(" · ".join(f"{k} : {pct(v, signe=True)}" for k, v in reels.items()))
    vmax = regles.PROFILS[etat.profil_num()]["vol_max"]
    st.caption(tr("Chocs par classe d'actifs : ordres de grandeur des baisses historiques (indices larges, en euros) ou chocs hypothétiques. "
                  f"Le temps de récupération suppose le rendement attendu du portefeuille. Volatilité maximale de votre profil : {vmax:.0%}.",
                  "Class shocks: orders of magnitude of past drawdowns or hypothetical shocks. Recovery time assumes the expected return."))


def afficher():
    if not etat.exiger_profil():
        return
    etat.entete(tr("Risques et optimisation", "Risk & optimisation"),
                tr("Où se situe votre portefeuille face à la théorie, et comment il réagirait aux grandes crises.",
                   "Where your portfolio stands against theory, and how it would react to major crises."))
    o1, o2 = st.tabs([tr("Frontière efficiente", "Efficient frontier"), tr("Stress tests", "Stress tests")])
    with o1:
        _onglet_markowitz()
    with o2:
        _onglet_stress()
