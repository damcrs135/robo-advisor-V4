"""Page Portefeuille : synthèse, historique réel, lignes par classe, personnalisation, contrôles et validation."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analytics
import conformite
import dossiers
import etat
import regles
from etat import eur, pct, tr
from textes import t

COULEURS = {"monetaire": "#3E7CB1", "obligations": "#12873F", "actions": "#1F3A5F", "diversifiants": "#D85A30",
            "scpi": "#9AA5B1", "actif": "#9CC3E6"}
ORDRE = ["monetaire", "obligations", "actions", "diversifiants", "scpi", "actif"]


def _sri(v) -> str:
    try:
        v = int(v)
    except (TypeError, ValueError):
        return "<span class='ra-note'>n/d</span>"
    bg, fg = ("#E6F4EA", "#12873F") if v <= 2 else ("#FFF4DB", "#8A5A00") if v <= 4 else ("#FDE8E8", "#C0392B")
    return f"<span style='font-size:11px;padding:2px 8px;border-radius:4px;background:{bg};color:{fg}'>{v}</span>"


def _ajustement():
    s = st.session_state
    p = etat.profil_num()
    with st.expander(t("ajuster", etat.L())):
        c1, c2 = st.columns(2)
        da = c1.slider(t("delta_actions", etat.L()), -10, 10, s.delta_actions, key="sl_actions")
        do = c2.slider(t("delta_oblig", etat.L()), -10, 10, s.delta_oblig, key="sl_oblig")
        st.caption(t("ajust_monetaire", etat.L()))
        try:
            regles.ajuster_allocation(p, da / 100, do / 100)
        except ValueError as e:
            st.error(t("ajust_refuse", etat.L(), raison=e))
            return
        if (da, do) != (s.delta_actions, s.delta_oblig):
            ancien = (s.delta_actions, s.delta_oblig)
            s.delta_actions, s.delta_oblig = da, do
            ind = etat.analyser(etat.items_pf())
            vmax = regles.PROFILS[p]["vol_max"]
            if ind["volatilite"] is not None and ind["volatilite"] > vmax and da > 0:
                st.error(t("vol_depassee", etat.L(), vol=pct(ind["volatilite"]), max=pct(vmax)))
                s.delta_actions, s.delta_oblig = ancien
            s.explication = None


def _historique(pf: dict, ind: dict):
    serie, _ = analytics.serie_portefeuille(pf)
    if serie.empty or len(serie) < 60:
        st.caption(tr("Historique des cours indisponible pour l'instant : les indicateurs passés s'afficheront dès que "
                      "les cours seront chargés.", "Price history not available yet."))
        return
    choix = st.segmented_control("periode", ["1 an", "3 ans", "5 ans"] if etat.L() == "fr" else ["1y", "3y", "5y"],
                                 default="3 ans" if etat.L() == "fr" else "3y", key="per_hist", label_visibility="collapsed")
    n = {"1": 252, "3": 756, "5": 1260}[(choix or "3")[0]]
    s = (1 + serie.iloc[-n:]).cumprod() * 100
    fig = go.Figure(go.Scatter(x=s.index, y=s.values, mode="lines", line=dict(color="#1F3A5F", width=2), fill="tozeroy",
                               fillcolor="rgba(31,58,95,0.06)", hovertemplate="%{x|%d/%m/%Y} · %{y:.1f}<extra></extra>"))
    fig.update_layout(height=220, margin=dict(l=0, r=0, t=6, b=0), yaxis=dict(range=[s.min() * 0.98, s.max() * 1.02],
                      gridcolor="#EEF1F5"), xaxis=dict(showgrid=False))
    st.plotly_chart(fig, width="stretch", key="fig_hist")
    st.caption(tr("Évolution passée du portefeuille (base 100, rééquilibré chaque jour). ", "Past performance (base 100). ")
               + t("source_prix", etat.L(), src=ind["source_prix"]))


def _lignes(pf: dict, ind: dict):
    u = regles.charger_univers()
    perf = etat.perf_lignes(etat.items_pf())
    mt = etat.montant()
    fr = etat.L() == "fr"
    cls = t("classes", etat.L())
    env_lignes = regles.repartition_enveloppes(pf, etat.enveloppe(), mt)
    classes = [c for c in ORDRE if any(u.loc[i, "classe"] == c for i in pf)]
    poids = {c: sum(w for i, w in pf.items() if u.loc[i, "classe"] == c) for c in classes}
    seg = "".join(f"<div style='width:{poids[c] * 100:.1f}%;background:{COULEURS[c]}'></div>" for c in classes)
    leg = "".join(f"<span style='margin-right:14px'><span style='color:{COULEURS[c]}'>●</span> {cls[c]} {poids[c] * 100:.0f} %</span>"
                  for c in classes)
    st.markdown(f"<div style='display:flex;height:12px;border-radius:6px;overflow:hidden;margin:6px 0 6px'>{seg}</div>"
                f"<div class='ra-note' style='margin-bottom:12px'>{leg}</div>", unsafe_allow_html=True)
    tete = ("<div style='display:flex;gap:10px;font-size:11px;color:#6B7785;padding:6px 0;border-bottom:1px solid #EEF1F5'>"
            f"<div style='flex:1'>{tr('Ligne', 'Holding')}</div><div style='width:62px'>{tr('Poids', 'Weight')}</div>"
            f"<div style='width:84px;text-align:right'>{tr('Montant', 'Amount')}</div>"
            f"<div style='width:62px;text-align:right'>{tr('1 an', '1y')}</div><div style='width:40px;text-align:center'>SRI</div></div>")
    blocs = ""
    for c in classes:
        ids = sorted([i for i in pf if u.loc[i, "classe"] == c], key=lambda i: -pf[i])
        lignes = ""
        for isin in ids:
            l, w = u.loc[isin], pf[isin]
            p1, p3 = perf.loc[isin, "perf_1a"], perf.loc[isin, "perf_3a"]
            cp = float(l["coupon"] or 0) if str(l["coupon"]).replace(".", "", 1).isdigit() else 0.0
            if l["type"] == "obligation":
                sous = f"{l['emetteur']} · {l['notation']} · {tr('échéance', 'maturity')} {l['maturite']}"
                extra = (f"<div><div class='ra-note'>{tr('Émetteur', 'Issuer')}</div>{l['emetteur']}"
                         f"<div class='ra-note' style='margin-top:4px'>{tr('Notation', 'Rating')}</div>{l['notation']}</div>"
                         f"<div><div class='ra-note'>Coupon</div>{tr('Zéro coupon', 'Zero coupon') if cp == 0 else f'{cp * 100:.2f} %'}"
                         f"<div class='ra-note' style='margin-top:4px'>{tr('Rendement estimé', 'Estimated yield')}</div>{pct(l['taux_annuel_num'], 2)}</div>")
            elif l["type"] == "action":
                sous = f"{l['ticker_yahoo']} · {l['secteur']} · {l['pays']}"
                extra = (f"<div><div class='ra-note'>{tr('Secteur', 'Sector')}</div>{l['secteur']}"
                         f"<div class='ra-note' style='margin-top:4px'>{tr('Pays', 'Country')}</div>{l['pays']}</div>")
            else:
                ter = l["ter_num"]
                sous = isin + ("" if pd.isna(ter) or not ter else f" · {tr('Frais', 'Fees')} {ter * 100:.2f} %")
                extra = ""
            lien = f"<a href='{l['source']}' target='_blank'>{tr('Fiche', 'Factsheet')}</a>" if str(l["source"]).startswith("http") else "—"
            lignes += (
                "<details style='border-bottom:1px solid #EEF1F5'><summary style='display:flex;align-items:center;gap:10px;"
                "padding:9px 0;cursor:pointer;list-style:none'>"
                f"<div style='flex:1;min-width:0'><div style='font-weight:600;color:#1B2A41'>{l['nom']}</div>"
                f"<div style='font-size:11px;color:#6B7785'>{sous}</div></div>"
                f"<div style='width:62px'><div style='height:5px;background:#EEF1F5;border-radius:3px'><div style='width:{min(w / poids[c] * 100, 100):.0f}%;"
                f"height:5px;background:{COULEURS[c]};border-radius:3px'></div></div><div style='font-size:11px;color:#6B7785;margin-top:2px'>{w * 100:.1f} %</div></div>"
                f"<div style='width:84px;text-align:right'>{eur(w * mt)}</div>"
                f"<div style='width:62px;text-align:right;color:{etat.couleur_signe(p1)}'>{pct(p1, signe=True)}</div>"
                f"<div style='width:40px;text-align:center'>{_sri(l['sri'])}</div></summary>"
                "<div style='background:#F4F6F9;border-radius:8px;padding:10px 12px;margin:0 0 8px;display:flex;gap:20px;flex-wrap:wrap;font-size:12px'>"
                f"<div style='flex:2;min-width:220px;color:#4A5560'>{l['description']}</div>"
                f"<div><div class='ra-note'>{tr('Perf. 3 ans', '3y perf.')}</div>{pct(p3, signe=True)}"
                f"<div class='ra-note' style='margin-top:4px'>{tr('Enveloppe', 'Wrapper')}</div>{env_lignes[isin]}</div>{extra}"
                f"<div><div class='ra-note'>SFDR</div>{l['sfdr'] or '—'}<div class='ra-note' style='margin-top:4px'>Documents</div>{lien}</div>"
                "</div></details>")
        p1_c = perf.loc[ids, "perf_1a"]
        p1_c = None if p1_c.isna().all() else float((p1_c.fillna(0) * pd.Series({i: pf[i] for i in ids})).sum() / poids[c])
        blocs += (
            "<details style='background:#fff;border:1px solid #E3E8EE;border-radius:12px;overflow:hidden'>"
            "<summary style='display:flex;justify-content:space-between;padding:12px 14px;cursor:pointer;background:#F7F9FB;list-style:none'>"
            f"<span style='font-weight:600;color:#1B2A41'><span style='color:{COULEURS[c]}'>●</span> {cls[c]} · {poids[c] * 100:.0f} %"
            f" <span class='ra-note'>({len(ids)} {tr('lignes', 'holdings') if len(ids) > 1 else tr('ligne', 'holding')})</span></span>"
            f"<span>{eur(poids[c] * mt)} · <span style='color:{etat.couleur_signe(p1_c)}'>{pct(p1_c, signe=True)}</span> ▾</span></summary>"
            f"<div style='padding:0 14px 6px'>{tete}{lignes}</div></details>")
    st.markdown("<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(460px,1fr));gap:10px;align-items:start'>"
                f"{blocs}</div>", unsafe_allow_html=True)
    st.caption(tr("Cliquez sur une classe, puis sur une ligne, pour voir sa fiche.", "Click a class, then a holding, to see its details."))


def _valider(ctrl):
    s = st.session_state
    d = etat.dossier_complet()
    donnees = {"langue": d["langue"], "reponses": d["reponses"], "profil": d["profil"], "enveloppe": d["enveloppe"],
               "portefeuille": d["portefeuille"], "horizon_ans": d["horizon_ans"], "controles": ctrl,
               "synthese": conformite.synthese(ctrl), "montant": d["reponses"].get("montant")}
    s.dossier_id = dossiers.enregistrer(donnees, s.get("dossier_id"))


def _validation():
    s = st.session_state
    ctrl = etat.controles()
    synth = conformite.synthese(ctrl)
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"#### {tr('Contrôle d’adéquation', 'Suitability check')} {etat.badge(synth)}", unsafe_allow_html=True)
        a_voir = [c for c in ctrl if c["statut"] != "ok"]
        if not a_voir:
            st.write(tr(f"Les {len(ctrl)} contrôles sont conformes.", f"All {len(ctrl)} checks pass."))
        for c in a_voir:
            st.markdown(f"{etat.badge(c['statut'])} **{c['titre']}** — {c['detail']}", unsafe_allow_html=True)
        st.caption(tr(f"{sum(c['statut'] == 'ok' for c in ctrl)} contrôles sur {len(ctrl)} conformes. Détail complet dans "
                      "l'espace conseiller.", f"{sum(c['statut'] == 'ok' for c in ctrl)} of {len(ctrl)} checks pass."))
        if s.get("dossier_id"):
            st.success(tr(f"Recommandation enregistrée sous la référence {s.dossier_id}.",
                          f"Recommendation saved as {s.dossier_id}."))
        else:
            lu = st.checkbox(tr("J'ai pris connaissance des risques de perte en capital et de ce portefeuille.",
                                "I have read the capital loss risks and this portfolio."), key="chk_risques")
            c2.button(tr("Valider ma recommandation", "Validate my recommendation"), type="primary", width="stretch",
                      disabled=synth == "bloquant" or not lu, on_click=_valider, args=(ctrl,), key="btn_valider_reco")
            if synth == "bloquant":
                st.caption(tr("Un contrôle bloquant empêche la validation : corrigez vos réponses.",
                              "A blocking check prevents validation: correct your answers."))


def afficher():
    if not etat.exiger_profil():
        return
    s = st.session_state
    pf = etat.portefeuille_courant()
    ind = etat.analyser(etat.items_pf())
    mt = etat.montant()
    etat.entete(tr("Mon portefeuille", "My portfolio"),
                f"{etat.nom_profil()} {etat.profil_num()}/5 · {etat.nom_enveloppe()} · {len(pf)} {tr('lignes', 'holdings')}")
    if s.note_construction:
        st.info({"ajustement": tr("Votre ajustement n'a pas pu être appliqué avec vos préférences : allocation de référence conservée.",
                                  "Your adjustment could not be applied with your preferences."),
                 "exclusions": tr("Vos exclusions sectorielles rendent le portefeuille impossible à construire : elles n'ont pas été appliquées.",
                                  "Your sector exclusions could not be applied."),
                 "esg": tr("Le filtre ESG n'a pas pu être appliqué.", "The ESG filter could not be applied.")}[s.note_construction])
    etat.rangee_kpi([
        etat.kpi(tr("Montant investi", "Amount invested"), eur(mt)),
        etat.kpi(tr("Perf. 1 an", "1y return"), pct(ind["perf_1a"], signe=True), couleur=etat.couleur_signe(ind["perf_1a"])),
        etat.kpi(tr("Perf. 3 ans", "3y return"), pct(ind["perf_3a"], signe=True), couleur=etat.couleur_signe(ind["perf_3a"])),
        etat.kpi(tr("Volatilité", "Volatility"), pct(ind["volatilite"])),
        etat.kpi(tr("Perte maximale", "Max drawdown"), pct(ind["drawdown_max"]), couleur=etat.ROUGE),
        etat.kpi(tr("Frais annuels", "Annual fees"), pct(ind["ter_moyen"], 2)),
    ])
    _historique(pf, ind)
    _lignes(pf, ind)
    _ajustement()
    if ind["avertissements"]:
        with st.expander(t("avertissements", etat.L())):
            for a in ind["avertissements"]:
                st.write("• " + a)
    _validation()
    c1, c2, _ = st.columns([1, 1, 2])
    c1.button(tr("Analyser les risques", "Analyse risks") + " →", on_click=etat.aller, args=("risques",), width="stretch", key="pf_risques")
    c2.button(tr("Voir la projection", "See projection") + " →", on_click=etat.aller, args=("projection",), width="stretch", key="pf_proj")
