"""Page Fiscalité : comparaison assurance-vie / PEA / compte-titres après impôts."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import etat
import fiscalite
from etat import eur, pct, tr


def afficher():
    if not etat.exiger_profil():
        return
    s = st.session_state
    r = s.reponses
    etat.entete(tr("Fiscalité : quelle enveloppe vous rapporte le plus ?", "Tax: which wrapper leaves you the most?"),
                tr("Même portefeuille, trois enveloppes : capital net de frais et d'impôts au moment du retrait (règles 2026).",
                   "Same portfolio, three wrappers: capital net of fees and taxes at withdrawal (2026 rules)."))
    sim = etat.simuler(etat.items_pf(), r["montant"], r.get("versement_mensuel", 0), s.horizon_ans, r.get("cible", 0))
    rendement = sim["hypotheses"]["rendement_portefeuille"]
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        ans = c1.slider(tr("Durée de détention (années)", "Holding period (years)"), 1, 30, int(s.horizon_ans or 10), key="sl_fisc_ans")
        foyers = ["seul", "couple"]
        foyer = c2.segmented_control(tr("Foyer fiscal", "Tax household"), foyers,
                                     default=fiscalite.foyer_depuis_reponses(r), key="sc_foyer",
                                     format_func=lambda f: tr("Personne seule", "Single") if f == "seul" else tr("Couple", "Couple")) or "seul"
        c3.markdown(f"<div class='ra-note'>{tr('Rendement attendu du portefeuille', 'Expected portfolio return')}</div>"
                    f"<div style='font-size:20px;font-weight:650'>{pct(rendement, 2)}</div>"
                    f"<div class='ra-note'>{tr('net des frais des fonds, hypothèse de simulation', 'net of fund fees')}</div>",
                    unsafe_allow_html=True)
    res = fiscalite.comparer(r["montant"], r.get("versement_mensuel", 0), ans, rendement, foyer, etat.L())
    meilleur = next(x for x in res if x["meilleur"])
    recommandee = etat.enveloppe()

    cartes = ""
    for x in res:
        bord = "#1F3A5F" if x["meilleur"] else "#E3E8EE"
        tag = (f"<span class='ra-badge' style='background:#E6F4EA;color:#12873F'>{tr('Meilleur net', 'Best net')}</span>" if x["meilleur"] else "")
        tag += (f" <span class='ra-badge' style='background:#EAF2FB;color:#1F3A5F'>{tr('Recommandée', 'Recommended')}</span>"
                if x["enveloppe"] == recommandee else "")
        cartes += (f"<div class='ra-carte' style='border:2px solid {bord}'><div style='display:flex;justify-content:space-between;gap:6px;flex-wrap:wrap'>"
                   f"<b>{x['nom']}</b><span>{tag}</span></div>"
                   f"<div style='font-size:26px;font-weight:700;color:#1B2A41;margin-top:6px'>{eur(x['capital_net'])}</div>"
                   f"<div class='ra-note'>{tr('capital net après impôts', 'net capital after tax')}</div>"
                   f"<table style='width:100%;font-size:13px;margin-top:8px'>"
                   f"<tr><td>{tr('Capital brut', 'Gross capital')}</td><td style='text-align:right'>{eur(x['capital_brut'])}</td></tr>"
                   f"<tr><td>{tr('Impôt sur le revenu', 'Income tax')}</td><td style='text-align:right'>{eur(-x['impot_revenu'])}</td></tr>"
                   f"<tr><td>{tr('Prélèvements sociaux', 'Social charges')}</td><td style='text-align:right'>{eur(-x['prelevements_sociaux'])}</td></tr>"
                   f"<tr><td>{tr('Taux effectif sur les gains', 'Effective rate on gains')}</td><td style='text-align:right'><b>{pct(x['taux_effectif'])}</b></td></tr>"
                   "</table></div>")
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px'>{cartes}</div>",
                unsafe_allow_html=True)

    fig = go.Figure()
    noms = [x["nom"].split(" (")[0] for x in res]
    fig.add_trace(go.Bar(x=noms, y=[x["verse"] for x in res], name=tr("Versé", "Contributed"), marker_color="#C9D6E3"))
    fig.add_trace(go.Bar(x=noms, y=[x["gain_net"] for x in res], name=tr("Gain net", "Net gain"), marker_color="#1F3A5F"))
    fig.add_trace(go.Bar(x=noms, y=[x["impots"] for x in res], name=tr("Impôts", "Taxes"), marker_color="#D85A30"))
    fig.update_layout(barmode="stack", height=320, margin=dict(l=0, r=0, t=10, b=0), yaxis=dict(tickformat=",.0f", ticksuffix=" €",
                      gridcolor="#EEF1F5"), legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, width="stretch", key="fig_fiscal")

    ecart = meilleur["capital_net"] - min(x["capital_net"] for x in res)
    if recommandee and recommandee != meilleur["enveloppe"]:
        st.info(tr(f"Sur le seul critère fiscal, {meilleur['nom']} rapporte le plus ({eur(ecart)} d'écart maximal). Nous recommandons "
                   f"pourtant {etat.nom_enveloppe()} pour d'autres raisons : votre objectif, l'accès au fonds en euros, la transmission "
                   "(assurance-vie) ou la liberté d'investissement (compte-titres).",
                   f"On tax alone, {meilleur['nom']} leaves the most. We still recommend {etat.nom_enveloppe()} for other reasons "
                   "(goal, euro fund, estate planning, investment freedom)."))
    else:
        st.success(tr(f"L'enveloppe recommandée est aussi la plus efficace fiscalement sur {ans} ans ({eur(ecart)} d'écart maximal).",
                      f"The recommended wrapper is also the most tax-efficient over {ans} years."))
    with st.expander(tr("Règles appliquées et simplifications", "Rules and simplifications")):
        st.markdown(tr(
            "- **Compte-titres** : flat tax de 31,4 % (12,8 % d'impôt + 18,6 % de prélèvements sociaux depuis le 1er janvier 2026).\n"
            "- **PEA** : après 5 ans, seuls les prélèvements sociaux de 18,6 % ; avant 5 ans, 31,4 %. Versements plafonnés à 150 000 €, "
            "l'excédent est placé en compte-titres. Seules les actions européennes y sont éligibles.\n"
            "- **Assurance-vie** : prélèvements sociaux maintenus à 17,2 %. Après 8 ans, abattement de 4 600 € (9 200 € pour un couple) puis "
            "7,5 % d'impôt (12,8 % sur la part des versements au-delà de 150 000 €) ; avant 8 ans, 12,8 %. Frais de gestion de l'enveloppe : 0,60 %/an.\n"
            "- Simplifications : retrait total à l'horizon, pas d'imposition annuelle des dividendes en compte-titres, option pour le barème "
            "progressif non étudiée. Avantages successoraux de l'assurance-vie non chiffrés ici.",
            "- **Securities account**: 31.4% flat tax (12.8% income tax + 18.6% social charges since 1 January 2026).\n"
            "- **PEA**: after 5 years, only 18.6% social charges; before, 31.4%. Contributions capped at €150,000.\n"
            "- **Life insurance**: social charges kept at 17.2%. After 8 years, €4,600 allowance (€9,200 for a couple) then 7.5% "
            "(12.8% above €150,000 of premiums); before 8 years, 12.8%. Wrapper fee 0.60% p.a.\n"
            "- Simplifications: full withdrawal at horizon, no annual dividend tax, progressive scale option not modelled."))
