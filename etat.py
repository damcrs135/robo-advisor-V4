"""
etat.py — État de session et fonctions partagées par toutes les pages

Toutes les pages lisent la session par ce module : une seule source de vérité pour la langue,
les réponses, le profil, l'enveloppe et le portefeuille courant.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date

import streamlit as st

import analytics
import conformite
import optimisation
import regles
import simulation
from textes import NOMS_ENVELOPPES, t

ETAT_DEFAUT = {"langue": "fr", "brouillon": None, "reponses": {}, "profil_calcule": None, "profil_choisi": None,
               "enveloppe": None, "enveloppe_choisie": None, "delta_actions": 0, "delta_oblig": 0,
               "horizon_ans": None, "explication": None, "source_explication": None, "ter_trad": 1.5,
               "note_construction": None, "etape_parcours": 0, "dossier_id": None, "conseiller_ok": False}
HORIZONS = {"<2": (1, 2, 2), "2-5": (2, 5, 5), "5-8": (5, 8, 8), ">8": (8, 30, 15)}   # (min, max, défaut)
PAGES: dict = {}            # rempli par app.py : clé -> st.Page
BLEU, BLEU_CLAIR, TEXTE, DISCRET, VERT, ROUGE = "#1F3A5F", "#EAF2FB", "#1B2A41", "#6B7785", "#12873F", "#C0392B"


def S():
    return st.session_state


def initialiser():
    for cle, val in ETAT_DEFAUT.items():
        st.session_state.setdefault(cle, val)
    if st.session_state.brouillon is None:
        st.session_state.brouillon = {}


def L() -> str:
    return st.session_state.get("langue", "fr")


def tr(fr: str, en: str) -> str:
    return en if L() == "en" else fr


def pct(x, d=1, signe=False):
    if x is None or x != x:
        return t("nd", L())
    return f"{x * 100:+.{d}f} %" if signe else f"{x * 100:.{d}f} %"


def eur(x, signe=False):
    if x is None or x != x:
        return t("nd", L())
    return (f"{x:+,.0f} €" if signe else f"{x:,.0f} €").replace(",", " ")


# ---------------------------------------------------------------------------
# Navigation : les boutons posent une cible, app.py change de page au début de l'exécution suivante
# ---------------------------------------------------------------------------
def aller(cible: str):
    """Callback de bouton : « parcours », « profil », … ou « refaire » (efface les réponses)."""
    if cible == "refaire":
        recommencer(garder_montant=True)
        cible = "parcours"
    st.session_state["_cible"] = cible


def recommencer(garder_montant: bool = False):
    langue = L()
    montant = (st.session_state.get("brouillon") or {}).get("montant")
    for cle in list(st.session_state.keys()):
        del st.session_state[cle]
    initialiser()
    st.session_state.langue = langue
    if garder_montant and montant:
        st.session_state.brouillon = {"montant": montant}


def a_un_profil() -> bool:
    return bool(st.session_state.get("profil_calcule"))


def exiger_profil() -> bool:
    """Affiche une invitation à faire le questionnaire si besoin. Renvoie True si la page peut s'afficher."""
    if a_un_profil():
        return True
    with st.container(border=True):
        st.markdown(f"#### {tr('Commencez par votre questionnaire', 'Start with your questionnaire')}")
        st.write(tr("Cette page s'affiche une fois votre profil établi (environ 10 minutes).",
                    "This page appears once your profile is set (about 10 minutes)."))
        st.button(tr("Commencer", "Start"), type="primary", on_click=aller, args=("parcours",), key="btn_exiger")
    return False


# ---------------------------------------------------------------------------
# Calculs mis en cache
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def analyser(pf_items):
    return analytics.analyser(dict(pf_items))


@st.cache_data(show_spinner=False)
def perf_lignes(pf_items):
    return analytics.perf_lignes(dict(pf_items))


@st.cache_data(show_spinner=False)
def simuler(pf_items, montant, versement, horizon, cible):
    return simulation.simuler(dict(pf_items), montant, versement, horizon, cible)


@st.cache_data(show_spinner=False)
def markowitz(pf_items, env):
    return optimisation.analyse(dict(pf_items), env)


# ---------------------------------------------------------------------------
# Profil, enveloppe, portefeuille
# ---------------------------------------------------------------------------
def profil_num() -> int | None:
    s = st.session_state
    return s.get("profil_choisi") or (s.get("profil_calcule") or {}).get("profil")


def enveloppe() -> str | None:
    s = st.session_state
    return s.get("enveloppe_choisie") or s.get("enveloppe")


def nom_profil(num: int | None = None) -> str:
    num = num or profil_num()
    return regles.PROFILS[num]["nom_en" if L() == "en" else "nom"]


def nom_enveloppe(env: str | None = None) -> str:
    env = env or enveloppe()
    return NOMS_ENVELOPPES[L()].get(env, env or "")


def _graine():
    r = json.dumps(st.session_state.get("reponses", {}), sort_keys=True, default=str)
    return int(hashlib.md5(r.encode()).hexdigest()[:8], 16)


def portefeuille_courant() -> dict:
    """
    Portefeuille avec l'ajustement du client et ses préférences durables. Si les contraintes sont impossibles
    à tenir, on retire d'abord l'ajustement, puis les exclusions, puis le filtre ESG (note pour le client).
    """
    s = st.session_state
    p, r = profil_num(), s.reponses
    excl, esg = regles.preferences_durables(r)
    try:
        alloc = regles.ajuster_allocation(p, s.delta_actions / 100, s.delta_oblig / 100)
    except ValueError:
        alloc = None
    base = dict(horizon=r.get("horizon"), zone=r.get("zone", "Monde"), graine=_graine())
    essais = [(alloc, excl, esg, None), (None, excl, esg, "ajustement"), (None, [], esg, "exclusions"),
              (None, [], False, "esg")]
    for al, ex, e, perdu in essais:
        try:
            pf = regles.construire_portefeuille(p, r.get("durabilite", "aucune"), enveloppe(), allocation=al,
                                                exclusions=ex, esg=e, **base)
            s.note_construction = perdu
            return pf
        except ValueError:
            continue
    raise RuntimeError("Construction du portefeuille impossible")


def portefeuille_sans_preferences() -> dict:
    """Même profil, même enveloppe, même tirage des titres, mais sans exclusion ni filtre ESG (pour comparer)."""
    s = st.session_state
    r = s.reponses
    try:
        return regles.construire_portefeuille(profil_num(), "aucune", enveloppe(), horizon=r.get("horizon"),
                                              zone=r.get("zone", "Monde"), graine=_graine())
    except ValueError:
        return {}


def items_pf():
    return tuple(sorted(portefeuille_courant().items()))


def montant() -> float:
    return st.session_state.reponses.get("montant", 0) or 0


def profil_complet() -> dict:
    s = st.session_state
    p = dict(s.profil_calcule)
    p["profil_calcule"] = p["profil"]
    p["profil"] = profil_num()
    return p


def controles(avec_indicateurs: bool = True) -> list[dict]:
    items = items_pf()
    ind = analyser(items) if avec_indicateurs else None
    return conformite.controler(st.session_state.reponses, profil_complet(), dict(items), enveloppe(), ind)


def dossier_complet() -> dict:
    """Tout ce qu'il faut pour l'explication, les livrables et le dossier conseiller."""
    s = st.session_state
    items = items_pf()
    pf = dict(items)
    r = dict(s.reponses)
    sim = simuler(items, r["montant"], r.get("versement_mensuel", 0), s.horizon_ans, r.get("cible", 0))
    r_just = dict(r, _profil=profil_num(), _enveloppe=enveloppe())
    return {"date": date.today().isoformat(), "langue": L(), "reponses": r, "profil": profil_complet(),
            "enveloppe": enveloppe(), "portefeuille": pf, "indicateurs": analyser(items), "simulation": sim,
            "horizon_ans": s.horizon_ans, "justifications": regles.justifier(pf, r_just, L()),
            "explication": s.explication or ""}


# ---------------------------------------------------------------------------
# Petits composants visuels
# ---------------------------------------------------------------------------
def entete(titre: str, sous_titre: str = ""):
    st.markdown(f"<div class='ra-titre'>{titre}</div>"
                + (f"<div class='ra-sous-titre'>{sous_titre}</div>" if sous_titre else ""), unsafe_allow_html=True)


def kpi(label: str, valeur: str, aide: str = "", couleur: str = TEXTE) -> str:
    return (f"<div class='ra-kpi'><div class='ra-kpi-l'>{label}</div>"
            f"<div class='ra-kpi-v' style='color:{couleur}'>{valeur}</div>"
            + (f"<div class='ra-kpi-a'>{aide}</div>" if aide else "") + "</div>")


def rangee_kpi(elements: list[str]):
    st.markdown("<div class='ra-kpis'>" + "".join(elements) + "</div>", unsafe_allow_html=True)


def badge(statut: str) -> str:
    c = {"ok": ("#E6F4EA", VERT, tr("Conforme", "Compliant")), "attention": ("#FFF4DB", "#8A5A00", tr("À documenter", "To document")),
         "bloquant": ("#FDE8E8", ROUGE, tr("Bloquant", "Blocking"))}[statut]
    return f"<span class='ra-badge' style='background:{c[0]};color:{c[1]}'>{c[2]}</span>"


def couleur_signe(x) -> str:
    return DISCRET if x is None or x != x else (VERT if x >= 0 else ROUGE)
