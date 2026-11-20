"""
fiscalite.py — Comparaison des enveloppes après impôts (règles françaises en vigueur en 2026)

Pour un même portefeuille, on compare le capital NET de frais d'enveloppe et d'impôts au moment du retrait total :
- Compte-titres (CTO) : prélèvement forfaitaire unique (PFU) de 31,4 % sur les gains
  (12,8 % d'impôt sur le revenu + 18,6 % de prélèvements sociaux depuis le 1er janvier 2026) ;
- PEA : après 5 ans, gains exonérés d'impôt sur le revenu, seuls les prélèvements sociaux de 18,6 % s'appliquent ;
  avant 5 ans, PFU de 31,4 %. Versements plafonnés à 150 000 € : l'excédent est placé en compte-titres ;
- Assurance-vie : prélèvements sociaux maintenus à 17,2 %. Après 8 ans, abattement annuel de 4 600 €
  (9 200 € pour un couple) puis 7,5 % d'impôt sur la part des gains liée aux 150 000 € premiers euros versés
  et 12,8 % au-delà ; avant 8 ans, 12,8 % d'impôt sur le revenu.

Simplifications (affichées sur le site) : retrait total en une fois à l'horizon ; pas d'imposition annuelle des
dividendes du CTO ni des prélèvements sociaux annuels du fonds en euros ; option pour le barème progressif non
étudiée ; frais d'enveloppe indicatifs (paramètres FRAIS_ENVELOPPE).
Sources : service-public.fr, La finance pour tous (hausse de la CSG au 1er janvier 2026).
"""

from __future__ import annotations

PS_CTO_PEA = 0.186
PS_AV = 0.172
IR_PFU = 0.128
IR_AV_8ANS = 0.075
ABATTEMENT_AV = {"seul": 4_600, "couple": 9_200}
SEUIL_AV = 150_000
PLAFOND_PEA = 150_000
FRAIS_ENVELOPPE = {"assurance-vie": 0.0060, "PEA": 0.0, "CTO": 0.0}   # frais annuels de l'enveloppe (indicatifs)
NOMS = {"assurance-vie": ("Assurance-vie", "Life insurance"), "PEA": ("PEA (+ CTO au-delà de 150 000 €)", "PEA (+ CTO above €150,000)"),
        "CTO": ("Compte-titres", "Securities account")}


def capital_brut(montant: float, versement: float, ans: int, rendement: float, frais: float) -> float:
    r = (1 + rendement - frais) ** (1 / 12) - 1
    v = montant
    for _ in range(int(ans) * 12):
        v = v * (1 + r) + versement
    return v


def _impot_cto(gain: float) -> tuple[float, float]:
    g = max(gain, 0.0)
    return g * IR_PFU, g * PS_CTO_PEA


def _impot_pea(gain: float, ans: int) -> tuple[float, float]:
    g = max(gain, 0.0)
    return (0.0 if ans >= 5 else g * IR_PFU), g * PS_CTO_PEA


def _impot_av(gain: float, verse: float, ans: int, foyer: str) -> tuple[float, float]:
    g = max(gain, 0.0)
    ps = g * PS_AV
    if ans < 8:
        return g * IR_PFU, ps
    imposable = max(g - ABATTEMENT_AV.get(foyer, 4_600), 0.0)
    part_basse = min(1.0, SEUIL_AV / verse) if verse > 0 else 1.0
    return imposable * (part_basse * IR_AV_8ANS + (1 - part_basse) * IR_PFU), ps


def comparer(montant: float, versement: float, ans: int, rendement: float, foyer: str = "seul",
             langue: str = "fr") -> list[dict]:
    """
    Une ligne par enveloppe : capital brut, impôts, capital net, gain net, taux d'imposition effectif.
    `rendement` = rendement annuel attendu du portefeuille, net des frais des fonds.
    """
    i = 1 if langue == "en" else 0
    ans = max(1, int(ans))
    verse = montant + versement * 12 * ans
    res = []
    for env in ("assurance-vie", "PEA", "CTO"):
        if env == "PEA" and verse > PLAFOND_PEA:
            # le PEA reçoit les 150 000 premiers euros, le reste va en CTO (mêmes proportions de versement)
            part = PLAFOND_PEA / verse
            cap = capital_brut(montant * part, versement * part, ans, rendement, 0.0)
            cap_cto = capital_brut(montant * (1 - part), versement * (1 - part), ans, rendement, 0.0)
            ir1, ps1 = _impot_pea(cap - PLAFOND_PEA, ans)
            ir2, ps2 = _impot_cto(cap_cto - (verse - PLAFOND_PEA))
            brut, ir, ps = cap + cap_cto, ir1 + ir2, ps1 + ps2
        else:
            brut = capital_brut(montant, versement, ans, rendement, FRAIS_ENVELOPPE[env])
            gain = brut - verse
            ir, ps = (_impot_av(gain, verse, ans, foyer) if env == "assurance-vie" else
                      _impot_pea(gain, ans) if env == "PEA" else _impot_cto(gain))
        gain_brut = brut - verse
        net = brut - ir - ps
        res.append({"enveloppe": env, "nom": NOMS[env][i], "verse": verse, "capital_brut": brut,
                    "impot_revenu": ir, "prelevements_sociaux": ps, "impots": ir + ps, "capital_net": net,
                    "gain_net": net - verse, "taux_effectif": (ir + ps) / gain_brut if gain_brut > 0 else 0.0})
    meilleur = max(res, key=lambda x: x["capital_net"])["enveloppe"]
    for r in res:
        r["meilleur"] = r["enveloppe"] == meilleur
    return res


def foyer_depuis_reponses(reponses: dict) -> str:
    return "couple" if reponses.get("situation_familiale") in ("couple", "couple_enfants") else "seul"
