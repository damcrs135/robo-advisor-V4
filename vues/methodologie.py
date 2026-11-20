"""Page Méthodologie et données : hypothèses, sources, qualité des données, architecture, limites."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analytics
import optimisation
import regles
import simulation
from etat import pct, tr


def afficher():
    i = 1 if st.session_state.get("langue") == "en" else 0
    st.markdown(f"<div class='ra-titre'>{tr('Méthodologie et données', 'Methodology & data')}</div>"
                f"<div class='ra-sous-titre'>{tr('Tout ce qui est calculé, d’où viennent les chiffres, et ce que l’outil ne fait pas.', 'What is computed, where figures come from, and the limits.')}</div>",
                unsafe_allow_html=True)
    o1, o2, o3, o4 = st.tabs([tr("Chaîne de décision", "Decision chain"), tr("Hypothèses de marché", "Market assumptions"),
                              tr("Qualité des données", "Data quality"), tr("Architecture et limites", "Architecture & limits")])
    with o1:
        etapes = [
            (tr("1. Connaissance client", "1. Know your client"), tr("35 questions en 5 blocs (situation, objectifs, connaissances, rapport au risque, préférences), questions adaptatives.", "35 questions in 5 sections, adaptive.")),
            (tr("2. Profil", "2. Profile"), tr("4 notes sur 5 (tolérance, horizon, capacité à subir des pertes, connaissances) ; le profil est la plus petite (règle prudente).", "4 scores out of 5; the profile is the lowest (prudent rule).")),
            (tr("3. Allocation", "3. Allocation"), tr("Grille de 5 profils (part actions de 10 % à 85 %), ajustable de ±10 points sous contrôle de volatilité.", "5-profile grid, ±10-point adjustment under volatility control.")),
            (tr("4. Sélection", "4. Selection"), tr("Actions et obligations en direct (poids égal, 7 % max par titre, 3 % max par obligation à haut rendement), ETF pour l'or et l'immobilier, fonds en euros, SCPI si horizon > 8 ans. Exclusions et filtre ESG du client appliqués.", "Direct stocks and bonds, ETFs for gold and real estate, euro fund, SCPI if horizon > 8 years. Client exclusions and ESG filter applied.")),
            (tr("5. Contrôles", "5. Checks"), tr("12 contrôles d'adéquation (esprit MiFID II) : risque, capacité, cohérence, liquidité, connaissances, diversification, enveloppe, durabilité.", "12 suitability checks (MiFID II spirit).")),
            (tr("6. Analyses", "6. Analyses"), tr("Indicateurs historiques, frontière de Markowitz, 5 stress tests, Monte Carlo 10 000 trajectoires, comparaison fiscale, ESG.", "Historical indicators, Markowitz, 5 stress tests, Monte Carlo, tax comparison, ESG.")),
            (tr("7. Restitution", "7. Output"), tr("Explication par IA vérifiée (aucun chiffre inventé accepté), déclaration d'adéquation PDF, fichier Excel, dossier conseiller avec journal d'audit.", "Verified AI explanation, PDF suitability statement, Excel file, advisor file with audit log.")),
        ]
        st.markdown("".join(f"<div class='ra-carte'><b>{a}</b><div style='font-size:13.5px;color:#4A5560;margin-top:3px'>{b}</div></div>"
                            for a, b in etapes), unsafe_allow_html=True)
    with o2:
        df = pd.DataFrame([{tr("Classe d'actifs", "Asset class"): optimisation.NOMS[c][i], tr("Rendement attendu", "Expected return"): pct(mu, 1),
                            tr("Volatilité", "Volatility"): pct(sig, 1)} for c, (mu, sig) in simulation.HYPOTHESES.items()])
        st.dataframe(df, hide_index=True, width="stretch")
        st.caption(tr("Source : ", "Source: ") + simulation.SOURCE_HYPOTHESES + tr(". Rendements nominaux en devise locale, bruts de frais.", ". Nominal, gross of fees."))
        noms = [optimisation.NOMS[c][i] for c in optimisation.CLASSES]
        fig = go.Figure(go.Heatmap(z=optimisation.CORRELATIONS, x=noms, y=noms, zmin=-1, zmax=1, colorscale="RdBu_r",
                                   text=[[f"{v:.2f}" for v in ligne] for ligne in optimisation.CORRELATIONS], texttemplate="%{text}",
                                   hovertemplate="%{y} / %{x} : %{z:.2f}<extra></extra>"))
        fig.update_layout(height=470, margin=dict(l=0, r=0, t=30, b=0), title=dict(text=tr("Corrélations retenues pour Markowitz", "Correlations used for Markowitz"), font=dict(size=13)))
        st.plotly_chart(fig, width="stretch", key="fig_corr")
        st.caption(tr("Ordres de grandeur de long terme (hypothèse pédagogique) ; la simulation Monte Carlo utilise, elle, les corrélations historiques quand les cours sont disponibles.",
                      "Long-run orders of magnitude; Monte Carlo uses historical correlations when prices are available."))
    with o3:
        u = regles.charger_univers()
        par_type = u.assign(t=u["type"].replace("", "fonds / ETF")).groupby("t").size()
        todo = {c: int((u[c] == "TODO").sum()) for c in ("sri", "sfdr", "ter", "pea", "ticker_yahoo") if c in u}
        snap = analytics.lire_snapshot()
        etat_snap = (tr(f"{snap.shape[1]} séries jusqu'au {snap.index.max().date()}", f"{snap.shape[1]} series up to {snap.index.max().date()}")
                     if snap is not None and not snap.empty else tr("absente", "missing"))
        st.markdown("".join(f"<div class='ra-carte'><b>{a}</b> · {b}</div>" for a, b in [
            (tr("Univers", "Universe"), " · ".join(f"{k} : {v}" for k, v in par_type.items())),
            (tr("Champs à compléter (TODO)", "Fields to complete (TODO)"), " · ".join(f"{k} : {v}" for k, v in todo.items())),
            (tr("Copie de secours des cours", "Price backup"), etat_snap),
            (tr("Cours en direct", "Live prices"), "Yahoo Finance (yfinance), " + tr("avec repli automatique sur la copie de secours", "falling back to the backup")),
        ]), unsafe_allow_html=True)
        st.caption(tr("Les coupons, échéances et rendements des obligations, ainsi que les identifiants internes « OBL-… », sont illustratifs : à vérifier avant tout usage réel.",
                      "Bond coupons, maturities and yields are illustrative."))
    with o4:
        st.markdown(tr(
            "**Architecture.** Les moteurs métier (`scoring`, `regles`, `analytics`, `simulation`, `optimisation`, `stress`, `fiscalite`, "
            "`esg`, `conformite`, `dossiers`, livrables) sont indépendants de l'interface et testés automatiquement (pytest, exécuté à chaque "
            "envoi sur GitHub). L'interface (`app.py`, `etat.py`, `vues/`) ne fait qu'afficher.\n\n"
            "**Données personnelles.** Aucun nom ni coordonnée n'est demandé ; les dossiers portent un identifiant pseudonyme. "
            "La clé de l'IA reste dans les secrets du serveur ; l'IA ne reçoit que des chiffres déjà calculés.\n\n"
            "**Limites.** Hypothèses de marché à 10 ans, corrélations simplifiées pour Markowitz, chocs de stress en ordres de grandeur, "
            "fiscalité simplifiée (retrait unique), intensité carbone estimée par secteur, dossiers effacés au redémarrage du serveur de démo. "
            "Ce site est un projet pédagogique : il ne constitue pas un conseil en investissement.",
            "**Architecture.** Business engines are independent of the UI and automatically tested (pytest on every GitHub push). "
            "The UI only displays.\n\n**Personal data.** No name or contact details; pseudonymous file IDs. The AI key stays server-side; "
            "the AI only receives computed figures.\n\n**Limits.** 10-year assumptions, simplified correlations, order-of-magnitude stress "
            "shocks, simplified tax, sector-estimated carbon, files wiped when the demo server restarts. Student project, not advice."))
