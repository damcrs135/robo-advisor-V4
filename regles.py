"""
regles.py — Règles de conseil (Amina)

Contient :
- la table des 5 profils (section 5.2 du cahier des charges) ;
- les contraintes de construction (30 % max par ligne, haut rendement ≤ 10 %, etc.) ;
- le choix de l'enveloppe ;
- la construction du portefeuille {identifiant: poids} ;
- les phrases de justification.

Contrat (section 4.3) :
    choisir_enveloppe(reponses, profil) -> "assurance-vie" | "PEA" | "CTO"
    construire_portefeuille(profil, durable, enveloppe) -> {isin: poids} (somme = 1)
    justifier(portefeuille, reponses) -> liste de phrases
"""

from __future__ import annotations

import math
import random
from functools import lru_cache
from pathlib import Path

import pandas as pd

DOSSIER = Path(__file__).resolve().parent
CHEMIN_UNIVERS = DOSSIER / "data" / "univers.csv"
CHEMIN_TITRES = DOSSIER / "data" / "univers_titres.csv"   # actions et obligations « titres vifs »

# ---------------------------------------------------------------------------
# 1. Table des profils (section 5.2) — poids en décimal
# ---------------------------------------------------------------------------
PROFILS = {
    1: {"nom": "Prudent", "nom_en": "Conservative", "sri_max": 2,
        "allocation": {"actions": 0.10, "obligations": 0.35, "monetaire": 0.50,
                       "diversifiants": 0.05, "scpi": 0.00, "actif": 0.00},
        "vol_min": 0.03, "vol_max": 0.05},
    2: {"nom": "Modéré", "nom_en": "Moderate", "sri_max": 3,
        "allocation": {"actions": 0.25, "obligations": 0.35, "monetaire": 0.25,
                       "diversifiants": 0.05, "scpi": 0.05, "actif": 0.05},
        "vol_min": 0.05, "vol_max": 0.08},
    3: {"nom": "Équilibré", "nom_en": "Balanced", "sri_max": 4,
        "allocation": {"actions": 0.45, "obligations": 0.30, "monetaire": 0.10,
                       "diversifiants": 0.05, "scpi": 0.05, "actif": 0.05},
        "vol_min": 0.08, "vol_max": 0.11},
    4: {"nom": "Dynamique", "nom_en": "Growth", "sri_max": 5,
        "allocation": {"actions": 0.65, "obligations": 0.15, "monetaire": 0.05,
                       "diversifiants": 0.05, "scpi": 0.05, "actif": 0.05},
        "vol_min": 0.11, "vol_max": 0.15},
    5: {"nom": "Offensif", "nom_en": "Aggressive", "sri_max": 6,
        "allocation": {"actions": 0.85, "obligations": 0.05, "monetaire": 0.00,
                       "diversifiants": 0.05, "scpi": 0.00, "actif": 0.05},
        "vol_min": 0.15, "vol_max": 0.18},
}

CLASSES = ["actions", "obligations", "monetaire", "diversifiants", "scpi", "actif"]

# ---------------------------------------------------------------------------
# 2. Contraintes (section 5.2)
# ---------------------------------------------------------------------------
MAX_PAR_LIGNE = 0.30          # 30 % maximum par ETF (appliqué à toutes les lignes)
MAX_HAUT_RENDEMENT = 0.10
MAX_EMERGENTS = 0.15
MAX_THEMATIQUE = 0.10
MAX_TITRE = 0.07              # 7 % maximum par action
MAX_TITRE_THEME = 0.05
MAX_OBLIG = 0.07              # 7 % maximum par obligation
MAX_OBLIG_HY = 0.03           # 3 % maximum par obligation à haut rendement
AJUSTEMENT_MAX = 0.10         # le client peut bouger une classe de ±10 points
PLAFOND_PEA = 150_000         # plafond légal des versements sur un PEA (en euros)

# Découpage de chaque poche entre sous-classes (en part de la poche).
# Ce sont des choix de construction, ajustables par l'équipe.
REPARTITION_ACTIONS = {
    "Monde": {"action_usa": 0.50, "action_europe": 0.25, "action_france": 0.25},
    "Europe": {"action_europe": 0.45, "action_france": 0.40, "action_usa": 0.15},
    "France": {"action_france": 0.60, "action_europe": 0.30, "action_usa": 0.10},
}
PART_THEMATIQUE_DURABLE = 0.10   # part de la poche actions prise par les thématiques vertes
REPARTITION_OBLIGATIONS = {"etat": 0.35, "etat_court": 0.20, "ig": 0.35, "haut_rendement": 0.10}
REPARTITION_DIVERSIFIANTS = {"or": 0.60, "immobilier": 0.40}

NIVEAUX_DURABILITE = ["aucune", "exclusions", "article 8", "article 9"]


# ---------------------------------------------------------------------------
# 3. Lecture de l'univers
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def charger_univers(chemin: str | None = None) -> pd.DataFrame:
    """Lit data/univers.csv et renvoie un DataFrame indexé par ISIN (ou identifiant interne)."""
    df = pd.read_csv(chemin or CHEMIN_UNIVERS, dtype=str, keep_default_na=False)
    if chemin is None and CHEMIN_TITRES.exists():
        # Actions et obligations en titres vifs : elles remplacent les ETF actions/obligations,
        # qui restent dans le fichier mais ne sont plus utilisés (sous-classe préfixée « etf_ »).
        titres = pd.read_csv(CHEMIN_TITRES, dtype=str, keep_default_na=False)
        # « groupe » sert à construire le portefeuille ; « sous_classe » garde les valeurs
        # attendues par simulation.py (usa, europe, etat, ig…).
        df["groupe"] = df["sous_classe"]
        masque = df["classe"].isin(["actions", "obligations"])
        df.loc[masque, "groupe"] = "etf_" + df.loc[masque, "sous_classe"]
        titres["groupe"] = titres["sous_classe"]
        titres["sous_classe"] = titres["sous_classe"].replace(
            {"action_usa": "usa", "action_europe": "europe", "action_france": "europe"})
        df = pd.concat([df, titres], ignore_index=True).fillna("")
    if "groupe" not in df.columns:
        df["groupe"] = df["sous_classe"]
    for c in ("type", "emetteur", "maturite", "coupon", "notation", "secteur", "pays", "tags", "esg"):
        if c not in df.columns:
            df[c] = ""
    df = df.set_index("isin", drop=False)
    for col in ("ter", "taux_annuel"):
        df[col + "_num"] = pd.to_numeric(df[col], errors="coerce")
    return df


def info_ligne(isin: str) -> dict:
    """Renvoie la fiche d'une ligne de l'univers sous forme de dictionnaire."""
    return charger_univers().loc[isin].to_dict()


def classe_de(isin: str) -> str:
    return charger_univers().loc[isin, "classe"]


def poids_par_classe(portefeuille: dict) -> dict:
    """Somme des poids par grande classe (actions, obligations…)."""
    u = charger_univers()
    res = {c: 0.0 for c in CLASSES}
    for isin, w in portefeuille.items():
        res[u.loc[isin, "classe"]] += w
    return res


def _numero_profil(profil) -> int:
    """Accepte un entier (1 à 5) ou le dictionnaire renvoyé par calculer_profil."""
    if isinstance(profil, dict):
        profil = profil["profil"]
    profil = int(profil)
    if profil not in PROFILS:
        raise ValueError(f"Profil inconnu : {profil}")
    return profil


def _est_durable(durable) -> bool:
    """« aucune » (ou False / vide) = version standard ; les 3 autres niveaux = version durable."""
    if isinstance(durable, bool):
        return durable
    return str(durable or "aucune").strip().lower() not in ("aucune", "non", "standard", "")


# ---------------------------------------------------------------------------
# 4. Choix de l'enveloppe (section 5.2)
# ---------------------------------------------------------------------------
def choisir_enveloppe(reponses: dict, profil) -> str:
    """
    Règle :
    1. objectif retraite ou transmission -> assurance-vie ;
    2. horizon > 5 ans et profil Dynamique ou Offensif (beaucoup d'actions) -> PEA,
       les lignes non éligibles étant logées dans un compte-titres en complément ;
    3. sinon -> assurance-vie (elle seule donne accès au fonds en euros).
    Si le client a une préférence (réponse « enveloppe_souhaitee » = assurance-vie, PEA ou CTO),
    elle est respectée.
    """
    p = _numero_profil(profil)
    voulue = reponses.get("enveloppe_souhaitee")
    if voulue in ("CTO", "PEA", "assurance-vie"):
        return voulue
    if reponses.get("objectif") in ("retraite", "transmission"):
        return "assurance-vie"
    if reponses.get("horizon") in ("5-8", ">8") and p >= 4:
        return "PEA"
    return "assurance-vie"


# ---------------------------------------------------------------------------
# 5. Construction du portefeuille
# ---------------------------------------------------------------------------
def _filtrer(df: pd.DataFrame, exclusions, esg: bool) -> pd.DataFrame:
    """Retire les titres qui portent un tag exclu (fossiles, armement, tabac, alcool, aerien…) ou, en mode ESG, les titres « esg = non »."""
    if df.empty or "tags" not in df.columns:
        return df
    excl = set(exclusions or [])
    if excl:
        df = df[~df["tags"].map(lambda s: bool(excl & set(str(s).split(";"))))]
    if esg:
        df = df[df["esg"] != "non"]
    return df


def _candidats(sous_classe: str, durable: bool, enveloppe: str, exclusions=(), esg: bool = False) -> list[str]:
    """
    Liste ordonnée des lignes possibles pour une sous-classe.
    Ordre de préférence : version demandée, puis éligibilité PEA si besoin, puis frais.
    """
    u = charger_univers()
    df = _filtrer(u[u["groupe"] == sous_classe].copy(), exclusions, esg)
    version_voulue = "durable" if durable else "standard"
    df["rang_version"] = df["version"].map(lambda v: 0 if v in (version_voulue, "commun") else 1)
    if enveloppe == "PEA" and sous_classe in ("monde", "usa", "europe", "emergents"):
        # En PEA, les actions doivent être éligibles. Si aucune version ISR n'est
        # éligible, on prend la version standard éligible (justifié dans le texte).
        df = df[df["pea"] == "oui"]
    elif (df["rang_version"] == 0).any():
        # Hors PEA : uniquement la version demandée.
        df = df[df["rang_version"] == 0]
    return list(df.sort_values(["rang_version", "ter_num"], kind="stable").index)


def _repartir(montant: float, candidats: list[str], plafonds: dict[str, float],
              portefeuille: dict) -> float:
    """
    Place `montant` sur la première ligne, puis déborde sur les suivantes
    quand le plafond de la ligne (30 %) est atteint. Renvoie le reste non placé.
    """
    reste = montant
    for isin in candidats:
        if reste <= 1e-12:
            break
        place = min(reste, plafonds.get(isin, MAX_PAR_LIGNE) - portefeuille.get(isin, 0.0))
        if place > 1e-12:
            portefeuille[isin] = portefeuille.get(isin, 0.0) + place
            reste -= place
    return reste


def _repartir_egal(montant: float, candidats: list[str], cap: float, portefeuille: dict,
                   mini: int = 3) -> float:
    """Répartit `montant` à parts égales sur au moins `mini` titres (cap par titre). Renvoie le reste."""
    if montant <= 1e-12 or not candidats:
        return max(montant, 0.0)
    n = min(len(candidats), max(mini, math.ceil(montant / cap - 1e-9)))
    part = montant / n
    reste = 0.0
    for isin in candidats[:n]:
        place = max(0.0, min(part, cap - portefeuille.get(isin, 0.0)))
        if place > 1e-12:
            portefeuille[isin] = portefeuille.get(isin, 0.0) + place
        reste += part - place
    return reste


def _cands_titres(sous_classe: str, enveloppe: str, exclusions=(), esg: bool = False) -> list[str]:
    """Actions d'une zone ; en PEA, les titres éligibles passent en premier."""
    u = charger_univers()
    df = _filtrer(u[u["groupe"] == sous_classe], exclusions, esg)
    if enveloppe == "PEA":
        df = df.assign(_r=(df["pea"] != "oui")).sort_values("_r", kind="stable")
    return list(df.index)


def construire_portefeuille(profil, durable, enveloppe, horizon: str | None = None,
                            zone: str = "Monde", allocation: dict | None = None,
                            exclusions=(), esg: bool = False, graine=None) -> dict:
    """
    Construit le portefeuille {isin: poids} d'un client.

    Paramètres du contrat : profil (1-5 ou dict de calculer_profil), durable (texte :
    "aucune", "exclusions", "article 8", "article 9"), enveloppe.
    Paramètres optionnels (ajoutés sans casser le contrat) :
    - horizon : nécessaire pour la règle SCPI (> 8 ans). Si absent, la SCPI n'est
      retenue qu'en assurance-vie pour le profil 3 ou 4 (prudence).
    - zone : "Monde", "Europe" ou "France" (préférence du bloc E).
    - allocation : allocation par classe déjà ajustée par le client (voir ajuster_allocation).
    - graine : entier ; fait varier le choix des titres d'un questionnaire à l'autre.
    - exclusions : tags à écarter, ex. ["fossiles", "armement", "tabac", "alcool", "aerien", "nucleaire"] ;
      esg : True pour ne garder que les actions et obligations « esg = oui ».
    """
    p = _numero_profil(profil)
    est_durable = _est_durable(durable)
    alloc = dict(allocation or PROFILS[p]["allocation"])
    u = charger_univers()
    pf: dict[str, float] = {}

    def _melanger(liste, cle):
        if graine is None:
            return liste
        l = list(liste)
        random.Random(f"{graine}-{cle}").shuffle(l)
        return l

    def cand(sc, d, e):
        res = _candidats(sc, d, e, exclusions, esg)
        return _melanger(res, sc) if sc in ("etat", "etat_court", "ig", "haut_rendement", "thematique") else res

    def cands_t(sc, e):
        res = _melanger(_cands_titres(sc, e, exclusions, esg), sc)
        if e == "PEA":
            res = sorted(res, key=lambda i: u.loc[i, "pea"] != "oui")
        return res

    # --- SCPI : seulement en assurance-vie et horizon > 8 ans, sinon vers les obligations
    scpi_ok = enveloppe == "assurance-vie" and (horizon == ">8" if horizon else p in (3, 4))
    if alloc.get("scpi", 0) > 0 and not scpi_ok:
        alloc["obligations"] = alloc.get("obligations", 0) + alloc["scpi"]
        alloc["scpi"] = 0.0
    if alloc.get("scpi", 0) > 0:
        pf["SCPI-IMMORENTE"] = alloc["scpi"]

    # --- Fonds actif : patrimonial pour les profils 2-3, actions pour 4-5
    if alloc.get("actif", 0) > 0:
        fonds = "FR0010135103" if p <= 3 else "FR0000284689"
        pf[fonds] = alloc["actif"]

    # --- Actions : titres vifs (jamais d'ETF), à parts égales dans chaque zone
    poche = alloc.get("actions", 0.0)
    if poche > 0:
        rep = dict(REPARTITION_ACTIONS.get(zone, REPARTITION_ACTIONS["Monde"]))
        if est_durable:
            theme = min(PART_THEMATIQUE_DURABLE * poche, MAX_THEMATIQUE)
            reste_theme = _repartir_egal(theme, cand("thematique", True, enveloppe), MAX_TITRE_THEME, pf, mini=2)
            poche_hors_theme = poche - theme + reste_theme
        else:
            poche_hors_theme = poche
        a_placer = 0.0
        for sc, part in rep.items():
            a_placer += _repartir_egal(part * poche_hors_theme, cands_t(sc, enveloppe), MAX_TITRE, pf)
        if a_placer > 1e-9:      # une zone est saturée : on déborde sur les autres
            for sc in rep:
                c2 = cands_t(sc, enveloppe)
                a_placer = _repartir(a_placer, c2, {i: MAX_TITRE for i in c2}, pf)
            if a_placer > 1e-9:
                raise ValueError("Impossible de placer la poche actions sous les contraintes.")

    # --- Obligations : titres vifs (États et entreprises)
    poche = alloc.get("obligations", 0.0)
    if poche > 0:
        reste_total = 0.0
        for sc, part in REPARTITION_OBLIGATIONS.items():
            cands = cand(sc, est_durable, enveloppe)
            cap = MAX_OBLIG_HY if sc == "haut_rendement" else MAX_OBLIG
            reste_total += _repartir_egal(part * poche, cands, cap, pf, mini=2)
        if reste_total > 1e-9:
            for sc in ["etat", "ig", "etat_court"]:
                cands = cand(sc, est_durable, enveloppe)
                reste_total = _repartir(reste_total, cands, {i: MAX_OBLIG for i in cands}, pf)
            if reste_total > 1e-9:
                raise ValueError("Impossible de placer la poche obligataire sous les contraintes.")

    # --- Monétaire : fonds en euros d'abord en assurance-vie, puis ETF monétaires
    poche = alloc.get("monetaire", 0.0)
    if poche > 0:
        cands = (["FONDS-EUROS"] if enveloppe == "assurance-vie" else []) + cand("monetaire", est_durable, enveloppe)
        if est_durable:   # une seule ligne monétaire durable : la version standard sert de dépannage
            cands += [i for i in cand("monetaire", False, enveloppe) if i not in cands]
        reste = _repartir(poche, cands, {i: MAX_PAR_LIGNE for i in cands}, pf)
        if reste > 1e-9:
            reste = _repartir(reste, cand("etat_court", est_durable, enveloppe),
                              {i: MAX_PAR_LIGNE for i in cand("etat_court", est_durable, enveloppe)}, pf)
            if reste > 1e-9:
                raise ValueError("Impossible de placer la poche monétaire sous les contraintes.")

    # --- Diversifiants
    poche = alloc.get("diversifiants", 0.0)
    if poche > 0:
        for sc, part in REPARTITION_DIVERSIFIANTS.items():
            cands = cand(sc, est_durable, enveloppe)
            _repartir(part * poche, cands, {i: MAX_PAR_LIGNE for i in cands}, pf)

    # Nettoyage : arrondi à 4 décimales et somme exactement égale à 1
    pf = {i: round(w, 4) for i, w in pf.items() if w > 1e-6}
    ecart = round(1.0 - sum(pf.values()), 4)
    if pf and abs(ecart) > 0:
        # l'écart d'arrondi va à la plus grosse ligne qui reste sous 30 %
        for isin in sorted(pf, key=pf.get, reverse=True):
            if pf[isin] + ecart <= MAX_PAR_LIGNE + 1e-9:
                pf[isin] = round(pf[isin] + ecart, 4)
                break
    return pf


def ajuster_allocation(profil, delta_actions: float = 0.0, delta_obligations: float = 0.0) -> dict:
    """
    Personnalisation du client (±10 points sur les actions et les obligations).
    La poche monétaire absorbe la différence. Lève ValueError si la demande sort des limites.
    Le contrôle de volatilité (≤ volatilité maximale du profil) est fait ensuite avec analytics.
    """
    p = _numero_profil(profil)
    if abs(delta_actions) > AJUSTEMENT_MAX + 1e-9 or abs(delta_obligations) > AJUSTEMENT_MAX + 1e-9:
        raise ValueError("Ajustement limité à ±10 points par classe.")
    alloc = dict(PROFILS[p]["allocation"])
    alloc["actions"] += delta_actions
    alloc["obligations"] += delta_obligations
    alloc["monetaire"] -= delta_actions + delta_obligations
    for c in ("actions", "obligations", "monetaire"):
        if alloc[c] < -1e-9:
            raise ValueError(f"La classe {c} deviendrait négative.")
        alloc[c] = max(0.0, round(alloc[c], 4))
    if abs(alloc["monetaire"] - PROFILS[p]["allocation"]["monetaire"]) > AJUSTEMENT_MAX + 1e-9:
        raise ValueError("La poche monétaire bougerait de plus de 10 points.")
    return alloc


def repartition_enveloppes(portefeuille: dict, enveloppe: str, montant: float | None = None) -> dict:
    """
    Indique dans quelle enveloppe loger chaque ligne.
    - PEA : lignes éligibles en PEA dans la limite de 150 000 € de versements ; le reste en CTO.
    - assurance-vie et CTO : tout dans l'enveloppe choisie.
    """
    if enveloppe != "PEA":
        return {i: enveloppe for i in portefeuille}
    u = charger_univers()
    res, verse_pea = {}, 0.0
    for isin, w in sorted(portefeuille.items(), key=lambda x: -x[1]):
        eligible = u.loc[isin, "pea"] == "oui"
        montant_ligne = w * montant if montant else 0.0
        if eligible and (montant is None or verse_pea + montant_ligne <= PLAFOND_PEA):
            res[isin] = "PEA"
            verse_pea += montant_ligne
        else:
            res[isin] = "CTO"
    return res


def estimer_sri(volatilite: float | None) -> int | None:
    """
    Classe de risque de marché estimée à partir de la volatilité annuelle,
    selon les seuils de volatilité (VEV) du règlement PRIIPs : <0,5 % -> 1 ;
    0,5-5 % -> 2 ; 5-12 % -> 3 ; 12-20 % -> 4 ; 20-30 % -> 5 ; 30-80 % -> 6 ; > 80 % -> 7.
    C'est une estimation : le vrai SRI combine aussi le risque de crédit.
    """
    if volatilite is None:
        return None
    for seuil, classe in [(0.005, 1), (0.05, 2), (0.12, 3), (0.20, 4), (0.30, 5), (0.80, 6)]:
        if volatilite < seuil:
            return classe
    return 7


# ---------------------------------------------------------------------------
# 6. Justifications (une phrase par règle appliquée)
# ---------------------------------------------------------------------------
def justifier(portefeuille: dict, reponses: dict, langue: str = "fr") -> list[str]:
    """Renvoie la liste des phrases qui expliquent chaque choix (plan B de llm.py)."""
    u = charger_univers()
    en = langue == "en"
    phrases = []
    classes = poids_par_classe(portefeuille)
    profil = reponses.get("_profil")
    if profil:
        nom = PROFILS[profil]["nom_en" if en else "nom"]
        phrases.append(
            f"Your profile is {nom}: the allocation follows its reference grid "
            f"({classes['actions']:.0%} equities, {classes['obligations']:.0%} bonds)."
            if en else
            f"Votre profil est {nom} : l'allocation suit sa grille de référence "
            f"({classes['actions']:.0%} d'actions, {classes['obligations']:.0%} d'obligations).")
    for isin, w in sorted(portefeuille.items(), key=lambda x: -x[1]):
        l = u.loc[isin]
        sc = l["sous_classe"]
        if sc == "fonds_euros":
            phrases.append(
                f"Euro fund ({w:.0%}): capital guaranteed by the insurer, available only in life insurance."
                if en else
                f"Fonds en euros ({w:.0%}) : capital garanti par l'assureur, accessible uniquement en assurance-vie.")
        elif sc == "scpi":
            phrases.append(
                f"SCPI {l['nom']} ({w:.0%}): unlisted real estate, kept because your horizon exceeds 8 years."
                if en else
                f"SCPI {l['nom']} ({w:.0%}) : immobilier non coté, retenu car votre horizon dépasse 8 ans (revente lente, frais d'entrée élevés).")
        elif l["classe"] == "actif":
            phrases.append(
                f"{l['nom']} ({w:.0%}): actively managed fund, fees {float(l['ter']):.2%} vs about 0.2% for an ETF, accepted for the manager's flexibility."
                if en else
                f"{l['nom']} ({w:.0%}) : fonds géré activement ; frais de {float(l['ter']):.2%} contre environ 0,2 % pour un ETF, acceptés pour la souplesse du gérant.")
        elif l["type"] == "action":
            phrases.append(
                f"{l['nom']} ({w:.1%}): {l['secteur']}, {l['pays']}; individual stock, equally weighted with the others in its region."
                if en else
                f"{l['nom']} ({w:.1%}) : action {l['secteur'].lower()} ({l['pays']}), titre vif à poids égal avec les autres de sa zone.")
        elif l["type"] == "obligation":
            cp = float(l["coupon"] or 0)
            cps = ("zero coupon" if cp == 0 else f"{cp:.2%} coupon") if en else ("zéro coupon" if cp == 0 else f"coupon {cp:.2%}")
            phrases.append(
                f"{l['nom']} ({w:.1%}): issuer {l['emetteur']}, rated {l['notation']}, {cps}, maturity {l['maturite']}."
                if en else
                f"{l['nom']} ({w:.1%}) : émetteur {l['emetteur']}, notation {l['notation']}, {cps}, échéance {l['maturite']}.")
        else:
            ter = l["ter_num"]
            raison = ("lowest fees in its category within our universe" if en
                      else "frais les plus bas de sa catégorie dans notre univers")
            if l["version"] == "durable" and _est_durable(reponses.get("durabilite")):
                raison = ("SRI version chosen to match your sustainability preference" if en
                          else "version ISR retenue pour respecter votre préférence de durabilité")
            if reponses.get("_enveloppe") == "PEA" and l["pea"] == "oui":
                raison = "PEA-eligible" if en else "éligible au PEA"
            phrases.append(f"{l['nom']} ({w:.0%}) : {raison} ({ter:.2%}/an)."
                           if not en else f"{l['nom']} ({w:.0%}): {raison} ({ter:.2%} p.a.).")
    if classes["obligations"] > 0 and any(u.loc[i, "sous_classe"] == "haut_rendement" for i in portefeuille):
        phrases.append("High-yield bonds are capped at 10% of the portfolio." if en
                       else "Les obligations à haut rendement sont plafonnées à 10 % du portefeuille.")
    return phrases


def preferences_durables(reponses: dict) -> tuple[list[str], bool]:
    """
    Traduit les réponses du bloc E en paramètres de construction :
    (secteurs à exclure, filtre ESG). Les fonds article 8 ou 9 imposent le filtre ESG.
    """
    exclusions = [e for e in (reponses.get("exclusions") or []) if e in ("armement", "tabac", "fossiles", "alcool", "aerien", "nucleaire")]
    esg = str(reponses.get("durabilite") or "aucune") in ("article 8", "article 9")
    return exclusions, esg
