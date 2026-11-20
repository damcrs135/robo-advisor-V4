"""
esg.py — Indicateurs extra-financiers du portefeuille

- part des lignes retenues par le filtre ESG (colonne « esg » de l'univers) ou en version ISR (fonds) ;
- exposition aux secteurs sensibles (tags : fossiles, armement, tabac, alcool, aérien, nucléaire) ;
- intensité carbone estimée (tonnes de CO2e par million d'euros de chiffre d'affaires, scopes 1 et 2).

L'intensité carbone est une ESTIMATION SECTORIELLE indicative (moyennes de secteur, ordres de grandeur),
pas la donnée publiée de chaque entreprise : à remplacer par une base fournisseur (MSCI, Sustainalytics, CDP)
dans un usage réel. Les obligations d'État et l'or ne sont pas couverts (méthodes de calcul différentes).
"""

from __future__ import annotations

import regles

INTENSITE_SECTEUR = {
    "Services publics": 500, "Énergie": 450, "Transport aérien": 800, "Matériaux": 600, "Énergie propre": 100,
    "Industrie": 120, "Aéronautique": 60, "Défense": 40, "Consommation de base": 60, "Consommation": 40,
    "Luxe": 15, "Santé": 15, "Technologie": 15, "Communication": 20, "Finance": 5,
}
INTENSITE_FONDS = {"monde": 100, "usa": 80, "europe": 90, "emergents": 300, "thematique": 140, "immobilier": 50,
                   "actions_actif": 90, "patrimonial": 70, "scpi": 30}
REFERENCE_MONDE = 100          # intensité indicative d'un indice actions monde, pour comparaison
TAGS = {"fossiles": ("Énergies fossiles", "Fossil fuels"), "armement": ("Armement", "Weapons"),
        "tabac": ("Tabac", "Tobacco"), "alcool": ("Alcool", "Alcohol"), "aerien": ("Transport aérien", "Aviation"),
        "nucleaire": ("Nucléaire", "Nuclear")}


def _secteur_emetteur(emetteur: str) -> str | None:
    """Secteur d'un émetteur d'obligation d'entreprise, retrouvé parmi les actions de l'univers."""
    u = regles.charger_univers()
    actions = u[u["type"] == "action"]
    mot = str(emetteur).split()[0].lower() if emetteur else ""
    for _, l in actions.iterrows():
        if mot and mot in str(l["nom"]).lower():
            return l["secteur"]
    return None


def intensite_ligne(isin: str) -> float | None:
    u = regles.charger_univers()
    l = u.loc[isin]
    if l["type"] == "action":
        return INTENSITE_SECTEUR.get(l["secteur"], 100)
    if l["type"] == "obligation":
        if l["sous_classe"] in ("etat", "etat_court"):
            return None
        return INTENSITE_SECTEUR.get(l["secteur"] or _secteur_emetteur(l["emetteur"]) or "", 100)
    return INTENSITE_FONDS.get(l["sous_classe"])


def analyser(portefeuille: dict) -> dict:
    u = regles.charger_univers()
    total = sum(portefeuille.values()) or 1.0
    esg_oui = sum(w for i, w in portefeuille.items()
                  if u.loc[i, "esg"] == "oui" or u.loc[i, "version"] == "durable") / total
    expo = {}
    for i, w in portefeuille.items():
        for tag in filter(None, str(u.loc[i, "tags"]).split(";")):
            expo[tag] = expo.get(tag, 0.0) + w
    couverts = {i: intensite_ligne(i) for i in portefeuille}
    poids_c = sum(w for i, w in portefeuille.items() if couverts[i] is not None)
    intensite = (sum(w * couverts[i] for i, w in portefeuille.items() if couverts[i] is not None) / poids_c
                 if poids_c else None)
    contributions = sorted(((u.loc[i, "nom"], w * couverts[i] / poids_c) for i, w in portefeuille.items()
                            if couverts[i] is not None and poids_c), key=lambda x: -x[1])[:5]
    sfdr = {}
    for i, w in portefeuille.items():
        s = str(u.loc[i, "sfdr"]).strip()
        cle = s if s in ("6", "8", "9") else "n.d."
        sfdr[cle] = sfdr.get(cle, 0.0) + w
    return {"part_esg": esg_oui, "exposition_tags": dict(sorted(expo.items(), key=lambda x: -x[1])),
            "intensite_carbone": intensite, "couverture_carbone": poids_c / total,
            "reference_monde": REFERENCE_MONDE, "principales_sources": contributions, "sfdr": sfdr}
