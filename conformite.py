"""
conformite.py — Contrôles d'adéquation (esprit MiFID II / règles de l'AMF), vus par le conseiller

Chaque contrôle renvoie un statut :
- "ok"        : règle respectée ;
- "attention" : à expliquer au client et à documenter dans le dossier ;
- "bloquant"  : la recommandation ne peut pas être émise en l'état.

    controler(reponses, profil, portefeuille, enveloppe, indicateurs=None) -> liste de contrôles
    synthese(controles) -> "ok" | "attention" | "bloquant"
"""

from __future__ import annotations

import regles

ORDRE = {"ok": 0, "attention": 1, "bloquant": 2}


def _c(code, titre, statut, detail, regle):
    return {"code": code, "titre": titre, "statut": statut, "detail": detail, "regle": regle}


def controler(reponses: dict, profil: dict, portefeuille: dict, enveloppe: str,
              indicateurs: dict | None = None) -> list[dict]:
    r = reponses
    u = regles.charger_univers()
    num = profil["profil"]
    calcule = profil.get("profil_calcule", num)
    montant = r.get("montant") or 0
    patrimoine = r.get("patrimoine") or 0
    classes = regles.poids_par_classe(portefeuille)
    res = []

    # 1. Adéquation du niveau de risque
    if num > calcule:
        res.append(_c("RISQUE", "Profil choisi plus risqué que le profil calculé", "attention",
                      f"Profil calculé {calcule}/5, profil retenu à la demande du client {num}/5. "
                      "Le client doit confirmer par écrit qu'il accepte ce niveau de risque.",
                      "MiFID II art. 25(2) — évaluation de l'adéquation"))
    else:
        res.append(_c("RISQUE", "Niveau de risque adapté", "ok",
                      f"Profil retenu {num}/5 ≤ profil calculé {calcule}/5.", "MiFID II art. 25(2)"))

    # 2. Capacité financière
    if patrimoine and montant > patrimoine:
        res.append(_c("CAPACITE", "Montant supérieur au patrimoine déclaré", "bloquant",
                      f"{montant:,.0f} € investis pour {patrimoine:,.0f} € de patrimoine.".replace(",", " "),
                      "Connaissance client (KYC) — cohérence des informations"))
    elif patrimoine and montant > 0.5 * patrimoine:
        res.append(_c("CAPACITE", "Concentration du patrimoine", "attention",
                      f"{montant / patrimoine:.0%} du patrimoine placé sur cette seule recommandation.",
                      "Capacité à subir des pertes"))
    else:
        res.append(_c("CAPACITE", "Capacité financière", "ok", "Montant cohérent avec le patrimoine déclaré.",
                      "Capacité à subir des pertes"))
    if r.get("epargne_precaution") is False:
        res.append(_c("PRECAUTION", "Pas d'épargne de précaution", "attention",
                      "Conseiller de garder 3 à 6 mois de dépenses disponibles avant d'investir.",
                      "Bonnes pratiques de conseil"))

    # 3. Cohérence des réponses
    if r.get("credits") is False and r.get("taux_effort") not in (None, "0"):
        res.append(_c("COHERENCE_CREDIT", "Réponses incohérentes sur les crédits", "attention",
                      "Le client déclare ne pas avoir de crédit mais indique un taux d'effort.",
                      "KYC — fiabilité des informations"))
    if r.get("rendement_attendu") in ("6-8", ">8") and r.get("perte_max") in ("0", "5"):
        res.append(_c("COHERENCE_RISQUE", "Rendement espéré incompatible avec la perte acceptée", "attention",
                      "Expliquer au client le lien entre rendement attendu et risque de perte.",
                      "Information du client — couple rendement / risque"))

    # 4. Horizon et liquidité
    if classes.get("scpi", 0) > 0 and r.get("horizon") != ">8":
        res.append(_c("LIQUIDITE", "SCPI avec un horizon court", "bloquant",
                      "La SCPI demande un horizon d'au moins 8 ans (revente lente, frais d'entrée).",
                      "Règle interne de construction"))
    if r.get("besoin_liquidite") and classes.get("monetaire", 0) < 0.05:
        res.append(_c("LIQUIDITE", "Besoin de liquidité et faible poche disponible", "attention",
                      "Le client peut avoir besoin de retirer de l'argent : garder une réserve monétaire.",
                      "Adéquation à l'horizon"))

    # 5. Connaissance des produits complexes / risqués
    hy = sum(w for i, w in portefeuille.items() if u.loc[i, "sous_classe"] == "haut_rendement")
    titres = sum(w for i, w in portefeuille.items() if u.loc[i, "type"] == "action")
    if (hy > 0 or titres > 0.5) and profil.get("notes", {}).get("connaissances", 5) <= 3:
        res.append(_c("CONNAISSANCES", "Produits risqués et connaissances limitées", "attention",
                      f"Actions en direct {titres:.0%}, haut rendement {hy:.0%} pour un client aux connaissances "
                      "limitées : renforcer l'information remise.", "MiFID II — connaissances et expérience"))
    else:
        res.append(_c("CONNAISSANCES", "Connaissances et expérience", "ok",
                      "Produits proposés compatibles avec le niveau déclaré.", "MiFID II — connaissances et expérience"))

    # 6. Contraintes de construction
    if max(portefeuille.values(), default=0) > regles.MAX_PAR_LIGNE + 1e-9:
        res.append(_c("DIVERSIFICATION", "Ligne supérieure à 30 %", "bloquant", "Une ligne dépasse 30 % du portefeuille.",
                      "Règle de diversification interne"))
    elif hy > regles.MAX_HAUT_RENDEMENT + 1e-9:
        res.append(_c("DIVERSIFICATION", "Haut rendement au-delà de 10 %", "bloquant", f"Haut rendement : {hy:.0%}.",
                      "Règle de diversification interne"))
    else:
        res.append(_c("DIVERSIFICATION", "Diversification", "ok",
                      f"{len(portefeuille)} lignes, aucune au-dessus de 30 %.", "Règle de diversification interne"))
    if indicateurs and indicateurs.get("volatilite") is not None:
        vmax = regles.PROFILS[num]["vol_max"]
        statut = "ok" if indicateurs["volatilite"] <= vmax else "attention"
        res.append(_c("VOLATILITE", "Volatilité historique / maximum du profil", statut,
                      f"{indicateurs['volatilite']:.1%} pour un maximum de {vmax:.0%}.", "Grille des profils"))

    # 7. Enveloppe
    if enveloppe == "PEA" and montant > regles.PLAFOND_PEA:
        res.append(_c("ENVELOPPE", "Plafond du PEA", "attention",
                      "Versements limités à 150 000 € : le reste est logé dans un compte-titres.", "Code monétaire et financier, art. L221-30"))
    voulue = r.get("enveloppe_souhaitee")
    if voulue and voulue not in ("auto", enveloppe):
        res.append(_c("ENVELOPPE", "Enveloppe différente du souhait du client", "attention",
                      f"Souhait : {voulue} ; retenue : {enveloppe}.", "Prise en compte des préférences"))

    # 8. Préférences de durabilité
    excl, esg = regles.preferences_durables(r)
    touches = [i for i in portefeuille if set(excl) & set(str(u.loc[i, "tags"]).split(";"))]
    if touches:
        res.append(_c("DURABILITE", "Exclusions sectorielles non respectées", "bloquant",
                      f"{len(touches)} ligne(s) appartiennent à un secteur exclu par le client.",
                      "MiFID II — préférences de durabilité (règlement délégué 2021/1253)"))
    elif excl or esg:
        res.append(_c("DURABILITE", "Préférences de durabilité respectées", "ok",
                      "Exclusions et filtre ESG appliqués à la construction.",
                      "MiFID II — préférences de durabilité (règlement délégué 2021/1253)"))
    return res


def synthese(controles: list[dict]) -> str:
    return max((c["statut"] for c in controles), key=ORDRE.get, default="ok")
