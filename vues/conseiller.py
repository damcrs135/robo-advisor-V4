"""
Espace conseiller : tableau de bord des dossiers, contrôles de conformité, journal d'audit, export.

Accès protégé par un code (secret Streamlit CODE_CONSEILLER ; « conseiller » par défaut pour la démo).
"""

from __future__ import annotations

import hmac
from datetime import datetime

import pandas as pd
import streamlit as st

import conformite
import dossiers
import etat
import questionnaire as qn
import regles
from etat import eur, tr
from textes import NOMS_ENVELOPPES


def _code_attendu() -> str:
    try:
        return str(st.secrets.get("CODE_CONSEILLER", "conseiller"))
    except Exception:
        return "conseiller"


def _connexion():
    s = st.session_state
    if hmac.compare_digest(str(s.get("code_conseiller", "")), _code_attendu()):
        s.conseiller_ok = True
        s["_erreur_code"] = False
    else:
        s["_erreur_code"] = True


def _changer_statut(identifiant: str):
    s = st.session_state
    dossiers.evenement(identifiant, s.get(f"note_{identifiant}", "").strip(), auteur="conseiller",
                       statut=s.get(f"statut_{identifiant}"))
    s[f"note_{identifiant}"] = ""


def _tableau(liste: list[dict]) -> pd.DataFrame:
    lignes = []
    for d in liste:
        p = d.get("profil", {})
        lignes.append({
            tr("Référence", "Reference"): d["id"],
            tr("Date", "Date"): d.get("cree_le", "")[:16].replace("T", " "),
            tr("Montant", "Amount"): d.get("montant") or d.get("reponses", {}).get("montant"),
            tr("Profil", "Profile"): f"{p.get('profil', '?')}/5" + (" ⚠" if p.get("profil", 0) > p.get("profil_calcule", 9) else ""),
            tr("Enveloppe", "Wrapper"): NOMS_ENVELOPPES[etat.L()].get(d.get("enveloppe"), d.get("enveloppe")),
            tr("Conformité", "Compliance"): {"ok": "✅", "attention": "🟠", "bloquant": "⛔"}.get(d.get("synthese"), "—"),
            tr("Statut", "Status"): d.get("statut", ""),
        })
    return pd.DataFrame(lignes)


def _detail(d: dict):
    L = etat.L()
    p = d.get("profil", {})
    st.markdown(f"#### {d['id']} {etat.badge(d.get('synthese', 'ok'))}", unsafe_allow_html=True)
    etat.rangee_kpi([
        etat.kpi(tr("Montant", "Amount"), eur(d.get("montant"))),
        etat.kpi(tr("Profil retenu / calculé", "Chosen / computed profile"), f"{p.get('profil')} / {p.get('profil_calcule')}"),
        etat.kpi(tr("Enveloppe", "Wrapper"), NOMS_ENVELOPPES[L].get(d.get("enveloppe"), "—")),
        etat.kpi(tr("Lignes", "Holdings"), str(len(d.get("portefeuille", {})))),
        etat.kpi(tr("Statut", "Status"), d.get("statut", "")),
    ])
    o1, o2, o3, o4 = st.tabs([tr("Contrôles", "Checks"), tr("Réponses", "Answers"), tr("Portefeuille", "Portfolio"), tr("Journal", "Log")])
    with o1:
        for c in d.get("controles", []):
            st.markdown(f"{etat.badge(c['statut'])} **{c['titre']}** — {c['detail']}  \n<span class='ra-note'>{c['regle']}</span>",
                        unsafe_allow_html=True)
    with o2:
        r = d.get("reponses", {})
        st.dataframe(pd.DataFrame([{"Question": q[L], tr("Réponse", "Answer"): qn.libelle(q["id"], r[q["id"]], L)}
                                   for q in qn.QUESTIONS if q["id"] in r and r[q["id"]] is not None]),
                     hide_index=True, width="stretch")
    with o3:
        u = regles.charger_univers()
        pf = d.get("portefeuille", {})
        st.dataframe(pd.DataFrame([{tr("Ligne", "Holding"): u.loc[i, "nom"] if i in u.index else i,
                                    tr("Classe", "Class"): u.loc[i, "classe"] if i in u.index else "",
                                    tr("Poids", "Weight"): round(w * 100, 2)} for i, w in sorted(pf.items(), key=lambda x: -x[1])]),
                     hide_index=True, width="stretch",
                     column_config={tr("Poids", "Weight"): st.column_config.ProgressColumn(format="%.1f %%", min_value=0, max_value=30)})
    with o4:
        for e in reversed(d.get("journal", [])):
            st.markdown(f"<span class='ra-note'>{e['date'].replace('T', ' ')} · {e['auteur']}</span> — {e['evenement']}",
                        unsafe_allow_html=True)
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 2, 1])
        c1.selectbox(tr("Nouveau statut", "New status"), dossiers.STATUTS, index=dossiers.STATUTS.index(d.get("statut", "à valider")),
                     key=f"statut_{d['id']}")
        c2.text_input(tr("Commentaire (appel client, justification…)", "Comment"), key=f"note_{d['id']}")
        c3.button(tr("Enregistrer", "Save"), type="primary", width="stretch", on_click=_changer_statut, args=(d["id"],),
                  key=f"btn_statut_{d['id']}")


def afficher():
    s = st.session_state
    etat.entete(tr("Espace conseiller", "Advisor area"),
                tr("Suivi des recommandations, contrôles d'adéquation et piste d'audit.", "Recommendations, suitability checks and audit trail."))
    if not s.conseiller_ok:
        with st.container(border=True):
            st.text_input(tr("Code d'accès conseiller", "Advisor access code"), type="password", key="code_conseiller")
            st.button(tr("Se connecter", "Sign in"), type="primary", on_click=_connexion, key="btn_conseiller")
            if s.get("_erreur_code"):
                st.error(tr("Code incorrect.", "Wrong code."))
            st.caption(tr("Démo : le code par défaut est « conseiller » (modifiable dans les secrets Streamlit, clé CODE_CONSEILLER).",
                          "Demo: default code is 'conseiller' (CODE_CONSEILLER secret)."))
        return

    liste = dossiers.lister()
    if etat.a_un_profil():
        ctrl = etat.controles()
        with st.expander(tr("Dossier en cours dans cette session (non enregistré)", "Current session file (unsaved)")
                         if not s.get("dossier_id") else tr(f"Dossier en cours : {s.dossier_id}", f"Current file: {s.dossier_id}"),
                         expanded=not liste):
            st.markdown(f"{tr('Synthèse', 'Summary')} : {etat.badge(conformite.synthese(ctrl))}", unsafe_allow_html=True)
            for c in ctrl:
                st.markdown(f"{etat.badge(c['statut'])} **{c['titre']}** — {c['detail']}", unsafe_allow_html=True)
    if not liste:
        st.info(tr("Aucun dossier enregistré pour l'instant : un dossier est créé quand un client valide sa recommandation "
                   "(page Portefeuille).", "No saved file yet: one is created when a client validates a recommendation."))
        return
    n_att = sum(d.get("statut") == "à valider" for d in liste)
    n_alerte = sum(d.get("synthese") in ("attention", "bloquant") for d in liste)
    total = sum((d.get("montant") or 0) for d in liste)
    etat.rangee_kpi([etat.kpi(tr("Dossiers", "Files"), str(len(liste))),
                     etat.kpi(tr("À valider", "To validate"), str(n_att)),
                     etat.kpi(tr("Avec alerte", "With alert"), str(n_alerte), couleur="#8A5A00" if n_alerte else etat.TEXTE),
                     etat.kpi(tr("Encours conseillé", "Assets advised"), eur(total))])
    c1, c2 = st.columns([1, 1])
    filtre = c1.multiselect(tr("Statut", "Status"), dossiers.STATUTS, key="filtre_statut", placeholder=tr("Tous", "All"))
    seulement_alertes = c2.toggle(tr("Seulement les dossiers avec alerte", "Only files with alerts"), key="filtre_alerte")
    vue = [d for d in liste if (not filtre or d.get("statut") in filtre)
           and (not seulement_alertes or d.get("synthese") in ("attention", "bloquant"))]
    df = _tableau(vue)
    st.dataframe(df, hide_index=True, width="stretch",
                 column_config={tr("Montant", "Amount"): st.column_config.NumberColumn(format="%.0f €")})
    st.download_button(tr("Exporter la liste (CSV)", "Export list (CSV)"), df.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name=f"dossiers_{datetime.now():%Y%m%d}.csv", mime="text/csv", key="dl_dossiers")
    if vue:
        ids = [d["id"] for d in vue]
        choix = st.selectbox(tr("Ouvrir un dossier", "Open a file"), ids, key="choix_dossier")
        d = next(x for x in vue if x["id"] == choix)
        _detail(d)
