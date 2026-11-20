"""
Parcours client en étapes : montant, 5 blocs de questions, récapitulatif.

- Une étape par bloc, avec une barre d'étapes et des boutons Précédent / Suivant.
- Questions adaptatives : le taux d'effort n'est demandé qu'en cas de crédit, les exclusions sectorielles
  seulement si le client exprime une préférence de durabilité.
- Chaque réponse est mémorisée au clic (S.brouillon) : changer de langue ou de page ne fait rien perdre.
- Récapitulatif final, avec un bouton « Modifier » par bloc, avant le calcul du profil.
"""

from __future__ import annotations

import streamlit as st

import etat
import questionnaire as qn
import regles
import scoring
from etat import eur, tr
from textes import t

BLOCS = list(qn.BLOCS)                          # A..E
ETAPES = ["montant"] + BLOCS + ["recap"]


def _b() -> dict:
    return st.session_state.brouillon


def visible(q: dict) -> bool:
    b = _b()
    if q["id"] == "taux_effort":
        return b.get("credits") is True
    if q["id"] == "exclusions":
        return b.get("durabilite") not in (None, "aucune")
    return True


def valeur_finale(q: dict):
    """Réponse retenue (les questions masquées prennent une valeur neutre)."""
    if not visible(q):
        return "0" if q["id"] == "taux_effort" else []
    v = _b().get(q["id"])
    if v is None and q["type"] == "nombre":
        return q["defaut"]
    if v is None and q["type"] == "multi":
        return []
    return v


def _memoriser(k, cle):
    _b()[k] = st.session_state[cle]


def _manquantes(bloc: str) -> list[dict]:
    return [q for q in qn.QUESTIONS if q["bloc"] == bloc and visible(q)
            and q["type"] in ("choix", "oui_non") and _b().get(q["id"]) is None]


def _erreur_etape(i: int) -> str | None:
    etape = ETAPES[i]
    if etape == "montant":
        statut = scoring.verifier_montant(_b().get("montant") or 0)
        return None if statut == "ok" else (t("montant_bas", etat.L()) if statut == "trop_bas" else t("montant_haut", etat.L()))
    if etape in BLOCS:
        manq = _manquantes(etape)
        if manq:
            return tr("Il manque encore des réponses : ", "Some answers are missing: ") + " ; ".join(q[etat.L()] for q in manq[:5])
        if etape == "A":
            m, p = _b().get("montant") or 0, _b().get("patrimoine") or 0
            if m > p:
                return tr(f"Le montant que vous souhaitez investir ({eur(m)}) dépasse votre patrimoine total ({eur(p)}). "
                          "Vérifiez l'un des deux chiffres.",
                          f"The amount you want to invest ({eur(m)}) exceeds your total wealth ({eur(p)}). "
                          "Please check one of the two figures.")
    return None


def _suivant():
    s = st.session_state
    err = _erreur_etape(s.etape_parcours)
    s["_erreur_parcours"] = err
    if not err:
        s.etape_parcours = min(s.etape_parcours + 1, len(ETAPES) - 1)


def _precedent():
    st.session_state.etape_parcours = max(st.session_state.etape_parcours - 1, 0)
    st.session_state["_erreur_parcours"] = None


def _aller_etape(i: int):
    st.session_state.etape_parcours = i
    st.session_state["_erreur_parcours"] = None


def _valider():
    """Calcule le profil à partir du brouillon et ouvre la page Profil."""
    s = st.session_state
    for i in range(len(ETAPES) - 1):
        err = _erreur_etape(i)
        if err:
            s["_erreur_parcours"], s.etape_parcours = err, i
            return
    rep = {q["id"]: valeur_finale(q) for q in qn.QUESTIONS}
    rep["montant"] = _b()["montant"]
    s.reponses = rep
    s.profil_calcule = scoring.calculer_profil(rep)
    s.profil_choisi = None
    s.pop("profil_radio", None)
    s.enveloppe = regles.choisir_enveloppe(rep, s.profil_calcule)
    s.enveloppe_choisie = None
    s.delta_actions = s.delta_oblig = 0
    s.horizon_ans = etat.HORIZONS[rep["horizon"]][2]
    s.explication = None
    s.dossier_id = None
    s["_cible"] = "profil"


def _barre_etapes(i: int):
    noms = [tr("Montant", "Amount")] + [qn.BLOCS[b][etat.L()] for b in BLOCS] + [tr("Récapitulatif", "Summary")]
    html = "".join(f"<div class='ra-etape {'actif' if k == i else 'fait' if k < i else ''}'>{k + 1}. {n}</div>"
                   for k, n in enumerate(noms))
    st.markdown(f"<div class='ra-etapes'>{html}</div>", unsafe_allow_html=True)


def _question(q: dict, numero: int):
    L = etat.L()
    k, cle = q["id"], f"q_{q['id']}_{L}"
    prec = _b().get(k)
    obligatoire = q["type"] in ("choix", "oui_non")
    st.markdown(f"**{numero}. {q[L]}**" + (" <span style='color:#C0392B'>*</span>" if obligatoire else ""),
                unsafe_allow_html=True)
    fmt = lambda v, q=q: qn.libelle(q["id"], v, L)
    cb = dict(key=cle, on_change=_memoriser, args=(k, cle), label_visibility="collapsed")
    if q["type"] == "nombre":
        st.number_input(k, min_value=q["min"], max_value=q["max"], step=q.get("pas", 1),
                        value=int(prec if prec is not None else q["defaut"]), **cb)
        if prec is None:                       # la valeur par défaut compte comme une réponse
            _b()[k] = q["defaut"]
    elif q["type"] == "choix":
        valeurs = [o[0] for o in q["options"]]
        st.radio(k, valeurs, index=valeurs.index(prec) if prec in valeurs else None, format_func=fmt, **cb)
    elif q["type"] == "multi":
        valeurs = [o[0] for o in q["options"]]
        st.multiselect(k, valeurs, default=[v for v in (prec or []) if v in valeurs], format_func=fmt,
                       placeholder=tr("Aucun", "None"), **cb)
    else:
        st.radio(k, [True, False], index={True: 0, False: 1}.get(prec), horizontal=True, format_func=fmt, **cb)


def _recapitulatif():
    L = etat.L()
    st.markdown("#### " + tr("Vérifiez vos réponses", "Check your answers"))
    st.caption(tr("Votre profil sera calculé à partir de ces réponses. Vous pouvez encore modifier chaque bloc.",
                  "Your profile will be computed from these answers. You can still edit each section."))
    m = _b().get("montant") or 0
    with st.container(border=True):
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"**{tr('Montant à investir', 'Amount to invest')}** : {eur(m)}")
        c2.button(tr("Modifier", "Edit"), key="mod_montant", on_click=_aller_etape, args=(0,), width="stretch")
    for i, bloc in enumerate(BLOCS, start=1):
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"**{bloc}. {qn.BLOCS[bloc][L]}**")
            c2.button(tr("Modifier", "Edit"), key=f"mod_{bloc}", on_click=_aller_etape, args=(i,), width="stretch")
            lignes = []
            for q in qn.QUESTIONS:
                if q["bloc"] != bloc or not visible(q):
                    continue
                v = valeur_finale(q)
                if q["type"] == "nombre":
                    txt = eur(v) if q["id"] in ("patrimoine", "versement_mensuel", "cible") else str(v)
                elif q["type"] == "vrai_faux" and v is None:
                    txt = tr("sans réponse", "no answer")
                else:
                    txt = qn.libelle(q["id"], v, L)
                lignes.append(f"<tr><td style='padding:3px 10px 3px 0;color:#4A5560'>{q[L]}</td>"
                              f"<td style='padding:3px 0;font-weight:600;text-align:right'>{txt}</td></tr>")
            st.markdown(f"<table style='width:100%;font-size:13.5px;border-collapse:collapse'>{''.join(lignes)}</table>",
                        unsafe_allow_html=True)


def afficher():
    s = st.session_state
    i = s.etape_parcours
    etat.entete(tr("Mon questionnaire", "My questionnaire"),
                tr(f"{len(qn.QUESTIONS)} questions en {len(BLOCS)} étapes, environ 10 minutes. Les questions marquées * sont obligatoires.",
                   f"{len(qn.QUESTIONS)} questions in {len(BLOCS)} steps, about 10 minutes. Questions marked * are required."))
    _barre_etapes(i)
    etape = ETAPES[i]

    if etape == "montant":
        with st.container(border=True):
            st.markdown(f"**{t('montant_q', etat.L())}**")
            cle = f"montant_{etat.L()}"
            st.number_input("montant", min_value=0, max_value=100_000_000, step=10_000,
                            value=int(_b().get("montant") or 0), key=cle, on_change=_memoriser, args=("montant", cle),
                            label_visibility="collapsed")
            st.caption(tr("Service conçu pour un capital de 100 000 € à 1 000 000 €.",
                          "Designed for capital between €100,000 and €1,000,000."))
    elif etape in BLOCS:
        premier = sum(1 for q in qn.QUESTIONS if BLOCS.index(q["bloc"]) < BLOCS.index(etape) and visible(q))
        with st.container(border=True):
            st.markdown(f"#### {etape}. {qn.BLOCS[etape][etat.L()]}")
            n = premier
            for q in [q for q in qn.QUESTIONS if q["bloc"] == etape]:
                if visible(q):
                    n += 1
                    _question(q, n)
    else:
        _recapitulatif()

    if s.get("_erreur_parcours"):
        st.error(s["_erreur_parcours"])
    c1, _, c2 = st.columns([1, 3, 1.3])
    if i > 0:
        c1.button("← " + tr("Précédent", "Back"), on_click=_precedent, width="stretch", key="btn_prec")
    if etape == "recap":
        c2.button(tr("Valider et voir mon profil", "Submit and see my profile"), type="primary",
                  on_click=_valider, width="stretch", key="btn_valider")
    else:
        c2.button(tr("Suivant", "Next") + " →", type="primary", on_click=_suivant, width="stretch", key="btn_suiv")
